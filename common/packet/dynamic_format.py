from typing import Any, Dict
from .format import Format
from .extended_field import ExtendedField
from .bit_utils import extract_rest_bits
from .exceptions import BitFieldError

class DynamicFormat(Format):
    """柔軟にフィールドを設定できるフォーマットクラス"""

    @classmethod
    def load(cls, data: Dict[str, Any]) -> "DynamicFormat":
        """辞書からインスタンスを生成"""
        return cls(**data)

    def set(self, key: str, value: Any) -> None:
        """フィールドを設定"""
        if key == "ex_field":
            if isinstance(value, dict):
                for k, v in value.items():
                    self.ex_field.set(k, v)
            elif isinstance(value, ExtendedField):
                self.ex_field = value
            else:
                raise ValueError("ex_field must be dict or ExtendedField")
            self.ex_flag = 0 if self.ex_field.is_empty() else 1
            return

        if not hasattr(self, key):
            raise AttributeError(f"Unknown field: {key}")
        setattr(self, key, value)

    def to_dict(self) -> Dict[str, Any]:
        """辞書形式で取得"""
        return self.as_dict()

    def from_bits(self, bitstr: int) -> None:
        """_total_bitsを考慮して拡張フィールドを解析"""
        super().from_bits(bitstr)
        if self.ex_flag == 1:
            ex_field_start = max(pos + size for field, (pos, size) in self._BIT_FIELDS.items())
            ex_field_bits = extract_rest_bits(bitstr, ex_field_start)
            total_bits = getattr(self, "_total_bits", bitstr.bit_length())
            if total_bits > ex_field_start:
                ex_field_total_bits = total_bits - ex_field_start
                self._ex_field = ExtendedField.from_bits(ex_field_bits, ex_field_total_bits)
            else:
                self._ex_field = ExtendedField.from_bits(ex_field_bits)
            self._ex_field.add_observer(self._on_ex_field_changed)

    @classmethod
    def from_bytes(cls, data: bytes) -> "DynamicFormat":
        instance = cls()
        min_packet_size = instance.get_min_packet_size()
        if len(data) < min_packet_size:
            raise BitFieldError(
                f"バイト列の長さが最小パケットサイズ {min_packet_size} バイトより短いです。受け取った長さ: {len(data)} バイト"
            )
        bitstr = int.from_bytes(data, byteorder="little")
        instance._total_bits = len(data) * 8
        instance.from_bits(bitstr)
        if not instance.verify_checksum12(data):
            raise BitFieldError("チェックサム検証に失敗しました。パケットが破損しているか、改ざんされています。")
        return instance
