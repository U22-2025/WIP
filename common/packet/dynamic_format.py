from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, OrderedDict, Optional
import yaml

@dataclass
class FieldSpec:
    start: int
    size: int
    type: str = "int"
    default: Any = None


class DynamicFormat:
    """YAML定義から動的にフォーマットを生成するクラス"""

    def __init__(self, specs: Dict[str, FieldSpec]):
        self._specs: OrderedDict[str, FieldSpec] = OrderedDict()
        self._values: Dict[str, Any] = {}
        for name, spec in specs.items():
            self._specs[name] = spec
            self._values[name] = spec.default

    @classmethod
    def load(cls, path: str) -> "DynamicFormat":
        """YAMLファイルを読み込みフォーマットを生成する"""
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        fields = data.get("fields", data)
        specs: OrderedDict[str, FieldSpec] = OrderedDict()
        start = 0
        for name, info in fields.items():
            size = int(info["size"])
            f_type = info.get("type", "int")
            default = info.get("default")
            specs[name] = FieldSpec(start=start, size=size, type=f_type, default=default)
            start += size
        return cls(specs)

    def set(self, **kwargs: Any) -> None:
        """フィールド値を設定。未指定フィールドはデフォルト値を使用"""
        for name, spec in self._specs.items():
            if name in kwargs:
                self._values[name] = kwargs[name]
            elif self._values[name] is None and spec.default is not None:
                self._values[name] = spec.default

    def to_bits(self) -> int:
        bitstr = 0
        for name, spec in self._specs.items():
            value = self._values.get(name)
            if value is None:
                continue
            if spec.type == "int":
                int_val = int(value)
            elif spec.type == "bool":
                int_val = 1 if value else 0
            elif spec.type == "str":
                int_val = int.from_bytes(str(value).encode("utf-8"), "little")
            else:
                raise ValueError(f"Unsupported type: {spec.type}")
            max_val = (1 << spec.size) - 1
            if int_val > max_val:
                raise ValueError(f"{name} exceeds {spec.size} bits")
            bitstr |= (int_val & max_val) << spec.start
        return bitstr

    def from_bits(self, bitstr: int) -> None:
        for name, spec in self._specs.items():
            mask = (1 << spec.size) - 1
            raw = (bitstr >> spec.start) & mask
            if spec.type == "int":
                value = raw
            elif spec.type == "bool":
                value = bool(raw)
            elif spec.type == "str":
                byte_len = (spec.size + 7) // 8
                value = raw.to_bytes(byte_len, "little").decode("utf-8").rstrip("\x00")
            else:
                value = raw
            self._values[name] = value

    def to_bytes(self) -> bytes:
        bitstr = self.to_bits()
        byte_len = (bitstr.bit_length() + 7) // 8
        return bitstr.to_bytes(byte_len or 1, "little")

    @classmethod
    def from_bytes(cls, data: bytes, path: str) -> "DynamicFormat":
        inst = cls.load(path)
        bitstr = int.from_bytes(data, "little")
        inst.from_bits(bitstr)
        return inst

    def __getattr__(self, item: str) -> Any:
        if item in self._values:
            return self._values[item]
        raise AttributeError(item)

    def __setattr__(self, key: str, value: Any) -> None:
        if key in {"_specs", "_values"}:
            super().__setattr__(key, value)
        elif key in self._specs:
            self._values[key] = value
        else:
            super().__setattr__(key, value)

    def as_dict(self) -> Dict[str, Any]:
        return dict(self._values)
