import json
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
                if v.startswith("'") and v.endswith("'") or v.startswith('"') and v.endswith('"'):
                    v = v[1:-1]
                item[k] = int(v) if v.isdigit() else v
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
                if value.startswith("'") and value.endswith("'") or value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]
                data[key] = int(value) if value.isdigit() else value
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
        self.values: Dict[str, int] = {f['name']: 0 for f in self.field_defs}

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

    def to_bits(self) -> int:
        bitstr = 0
        for name, (pos, length) in self._positions.items():
            val = self.values.get(name, 0)
            max_val = (1 << length) - 1
            if val < 0 or val > max_val:
                raise ValueError(f"Field {name} out of range")
            bitstr |= int(val) << pos
        return bitstr

    def to_bytes(self) -> bytes:
        bitstr = self.to_bits()
        required_bytes = (bitstr.bit_length() + 7) // 8 or 1
        return bitstr.to_bytes(required_bytes, byteorder='little')

    @classmethod
    def from_bytes(cls, path: str, data: bytes) -> "DynamicFormat":
        inst = cls.load(path)
        bitstr = int.from_bytes(data, byteorder='little')
        for name, (pos, length) in inst._positions.items():
            inst.values[name] = (bitstr >> pos) & ((1 << length) - 1)
        return inst

    def to_dict(self) -> Dict[str, int]:
        return dict(self.values)
