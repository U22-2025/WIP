import pytest
from common.packet.core.extended_field import ExtendedField, BitFieldError


def test_source_int_roundtrip():
    value = ExtendedField._source_to_int("10.0.0.1", 123)
    ip, port = ExtendedField._int_to_source(value)
    assert ip == "10.0.0.1" and port == 123


def test_source_to_int_invalid_ip():
    with pytest.raises(BitFieldError):
        ExtendedField._source_to_int("10.0.0", 80)


def test_int_to_source_too_short():
    with pytest.raises(BitFieldError):
        ExtendedField._int_to_source(123456)


def test_to_csv_line_strips_empty():
    result = ExtendedField.to_csv_line(['a', '  ', '', 'b'])
    assert result == 'a,b'
