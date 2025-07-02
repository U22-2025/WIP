import json
import re
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional
from .extended_field import ExtendedField

try:
    import yaml  # type: ignore
except ImportError:  # pragma: no cover
    yaml = None


def _load_simple_yaml(text: str) -> Any:
    """pyyaml がない場合の簡易 YAML パーサ"""
    data: Dict[str, Any] = {}
    current_key: Optional[str] = None

    def _parse(v: str) -> Any:
        """文字列を整数・小数・文字列として解釈"""
        if v.startswith("'") and v.endswith("'") or v.startswith('"') and v.endswith('"'):
            return v[1:-1]
        if re.fullmatch(r"-?\d+\.\d+", v):
            return float(v)
        if re.fullmatch(r"-?\d+", v):
            return int(v)
        return v

    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("-"):
            if current_key is None:
                continue
            entry = line[1:].strip()
            if entry.startswith("{") and entry.endswith("}"):
                entry = entry[1:-1]
            item: Dict[str, Any] = {}
            for part in entry.split(','):
                k, v = part.split(':', 1)
                k = k.strip()
                v = v.strip()
                item[k] = _parse(v)
            data.setdefault(current_key, []).append(item)
        else:
            if ':' not in line:
                continue
            key, value = line.split(':', 1)
            key = key.strip()
            value = value.strip()
            if value == "":
                data[key] = []
                current_key = key
            else:
                data[key] = _parse(value)
                current_key = None
    return data


def _safe_load_yaml(path: Path) -> Any:
    text = path.read_text(encoding='utf-8')
    if yaml is not None:
        return yaml.safe_load(text)
    return _load_simple_yaml(text)


class DynamicFormat:
    """JSON/YAML定義から動的に生成されるパケットクラス"""

    def __init__(self, field_defs: List[Dict[str, Any]]):
        self.field_defs = field_defs
        self._positions: Dict[str, Tuple[int, int]] = {}
        pos = 0
        for f in self.field_defs:
            length = int(f['length'])
            self._positions[f['name']] = (pos, length)
            pos += length
        self._base_bits = pos
        self.values: Dict[str, int] = {f['name']: 0 for f in self.field_defs}
        self.ex_field = ExtendedField()
        self.has_checksum = 'checksum' in self.values
        self.has_ex_flag = 'ex_flag' in self.values

    def __getattr__(self, name: str) -> Any:
        """values 辞書に存在する項目を属性として参照できるようにする"""
        vals = self.__dict__.get("values")
        if vals is not None and name in vals:
            return vals[name]
        raise AttributeError(name)

    def __getattribute__(self, name: str) -> Any:  # pragma: no cover - 挙動確認用
        vals = object.__getattribute__(self, "__dict__").get("values")
        if vals is not None and name in vals:
            return vals[name]
        return object.__getattribute__(self, name)

    def __setattr__(self, name: str, value: Any) -> None:
        vals = self.__dict__.get('values')
        if vals and name in vals:
            vals[name] = int(value) if isinstance(value, (int, float)) else value
        else:
            super().__setattr__(name, value)

    @classmethod
    def load(cls, path: str) -> "DynamicFormat":
        """JSONまたはYAMLファイルからフォーマットを読み込む"""
        p = Path(path)
        if p.suffix in {'.yaml', '.yml'}:
            data = _safe_load_yaml(p)
        else:
            data = json.loads(p.read_text(encoding='utf-8'))
        fields = data.get('fields', [])
        # 拡張フィールド定義を外部ファイルから読み込むか、同ファイルの設定を使用
        ext = data.get('extended_fields')
        ext_file = data.get('extended_fields_file')
        if ext_file:
            ext_path = Path(ext_file)
            if not ext_path.is_absolute():
                ext_path = p.parent / ext_file
            ext_data = _safe_load_yaml(ext_path)
            ext_entries = ext_data.get('extended_fields', ext_data)
            ExtendedField.update_mapping(ext_entries)
        elif ext:
            ExtendedField.update_mapping(ext)
        return cls(fields)

    def set(self, **kwargs: int) -> None:
        for k, v in kwargs.items():
            if k in self.values:
                self.values[k] = int(v)

    def set_extended(self, **kwargs: Any) -> None:
        """拡張フィールドの値を設定"""
        self.ex_field.update(kwargs)

    def _build_bits(self) -> int:
        bitstr = 0
        for name, (pos, length) in self._positions.items():
            val = self.values.get(name, 0)
            max_val = (1 << length) - 1
            if val < 0 or val > max_val:
                raise ValueError(f"Field {name} out of range")
            bitstr |= int(val) << pos
        if self.has_ex_flag and self.values.get('ex_flag', 0) == 1 and not self.ex_field.is_empty():
            bitstr |= self.ex_field.to_bits() << self._base_bits
        return bitstr

    def to_bits(self) -> int:
        return self._build_bits()

    def to_bytes(self) -> bytes:
        original_checksum = self.values.get('checksum', 0)
        if self.has_checksum:
            self.values['checksum'] = 0

        bitstr = self._build_bits()
        required_bytes = max((bitstr.bit_length() + 7) // 8, 16)
        data = bitstr.to_bytes(required_bytes, byteorder='little')

        if self.has_checksum:
            checksum = self.calc_checksum12(data)
            self.values['checksum'] = checksum
            bitstr = self._build_bits()
            data = bitstr.to_bytes(required_bytes, byteorder='little')
        else:
            self.values['checksum'] = original_checksum

        return data

    @classmethod
    def from_bytes(cls, path: str, data: bytes) -> "DynamicFormat":
        inst = cls.load(path)
        bitstr = int.from_bytes(data, byteorder='little')
        for name, (pos, length) in inst._positions.items():
            inst.values[name] = (bitstr >> pos) & ((1 << length) - 1)

        if inst.has_ex_flag and inst.values.get('ex_flag', 0) == 1:
            total_bits = len(data) * 8
            if total_bits > inst._base_bits:
                ext_bits = bitstr >> inst._base_bits
                inst.ex_field = ExtendedField.from_bits(ext_bits, total_bits - inst._base_bits)

        if inst.has_checksum:
            stored = inst.values.get('checksum', 0)
            inst.values['checksum'] = 0
            check_data = inst._build_bits()
            check_bytes = check_data.to_bytes(len(data), byteorder='little')
            calc = inst.calc_checksum12(check_bytes)
            inst.values['checksum'] = stored
            if calc != stored:
                raise ValueError('checksum mismatch')

        return inst

    def to_dict(self) -> Dict[str, int]:
        result = dict(self.values)
        if not self.ex_field.is_empty():
            result['ex_field'] = self.ex_field.to_dict()
        return result

    @staticmethod
    def calc_checksum12(data: bytes) -> int:
        sum_val = 0
        for b in data:
            sum_val += b
        while sum_val >> 12:
            sum_val = (sum_val & 0xFFF) + (sum_val >> 12)
        return (~sum_val) & 0xFFF
