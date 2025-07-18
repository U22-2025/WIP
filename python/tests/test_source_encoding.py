import pytest
from common.packet.core.extended_field import ExtendedField


def test_source_field_encode_decode():
    ex = ExtendedField({'source': ('127.0.0.1', 5000)})
    bits = ex.to_bits()
    value_int = ExtendedField._source_to_int('127.0.0.1', 5000)
    bytes_len = (value_int.bit_length() + 7) // 8
    total_bits = ExtendedField.EXTENDED_HEADER_TOTAL + bytes_len * 8
    restored = ExtendedField.from_bits(bits, total_bits)
    assert restored.source == ('127.0.0.1', 5000)
