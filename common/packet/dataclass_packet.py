from dataclasses import field, make_dataclass
from typing import Any, Dict, Type

from .dynamic_format import DynamicFormat
from .extended_field import ExtendedField


def create_packet_dataclass(path: str, class_name: str = "DynamicPacket") -> Type:
    """YAML/JSON 定義から dataclass ベースのパケットクラスを生成"""
    base_fmt = DynamicFormat.load(path)

    dataclass_fields = [
        (name, int, field(default=0)) for name in base_fmt.values.keys()
    ]

    if base_fmt.has_ex_flag:
        dataclass_fields.append(
            ("ex_field", ExtendedField, field(default_factory=ExtendedField))
        )

    cls = make_dataclass(class_name, dataclass_fields)
    setattr(cls, "_fmt_path", path)

    def to_bytes(self) -> bytes:
        fmt = DynamicFormat.load(self._fmt_path)
        fmt.set(**{name: getattr(self, name) for name in base_fmt.values.keys()})
        if base_fmt.has_ex_flag:
            fmt.ex_field = getattr(self, "ex_field")
        return fmt.to_bytes()

    @classmethod
    def from_bytes(cls, data: bytes):
        inst = DynamicFormat.from_bytes(cls._fmt_path, data)
        kwargs = inst.values.copy()
        obj = cls(**kwargs)
        if base_fmt.has_ex_flag:
            obj.ex_field = inst.ex_field
        return obj

    def to_dict(self) -> Dict[str, Any]:
        res = {name: getattr(self, name) for name in base_fmt.values.keys()}
        if base_fmt.has_ex_flag and getattr(self, "ex_field"):
            res["ex_field"] = self.ex_field.to_dict()
        return res

    cls.to_bytes = to_bytes
    cls.from_bytes = from_bytes
    cls.to_dict = to_dict

    return cls
