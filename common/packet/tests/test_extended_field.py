import unittest
from common.packet.extended_field import ExtendedField, ExtendedFieldType

class TestExtendedFieldHelpers(unittest.TestCase):
    def test_parse_header_and_decode(self):
        ef = ExtendedField({'alert': 'storm'})
        bits = ef.to_bits()
        total_bits = ef.EXTENDED_HEADER_TOTAL + len('storm'.encode('utf-8')) * 8
        parsed = ExtendedField._parse_header(bits, 0, total_bits)
        self.assertIsNotNone(parsed)
        key, bytes_len, bits_len = parsed
        self.assertEqual(key, ExtendedFieldType.ALERT)
        self.assertEqual(bytes_len, len('storm'.encode('utf-8')))
        value_bits = bits >> ef.EXTENDED_HEADER_TOTAL & ((1 << bits_len) - 1)
        value = ExtendedField._decode_value(key, value_bits, bytes_len)
        self.assertEqual(value, 'storm')

    def test_decode_coordinate_and_source(self):
        ef = ExtendedField({'latitude': 35.0, 'source': ('127.0.0.1', 8080)})
        bits = ef.to_bits()
        total_bits = (
            ef.EXTENDED_HEADER_TOTAL + 4 * 8 +
            ef.EXTENDED_HEADER_TOTAL + len("127.0.0.1:8080".encode()) * 8
        )
        parsed = ExtendedField.from_bits(bits, total_bits)
        self.assertAlmostEqual(parsed.latitude, 35.0)
        self.assertEqual(parsed.source, ('127.0.0.1', 8080))

if __name__ == '__main__':
    unittest.main()
