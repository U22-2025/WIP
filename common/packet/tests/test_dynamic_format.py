import os
import unittest
from common.packet.dynamic_format import DynamicFormat

class TestDynamicFormat(unittest.TestCase):
    def setUp(self):
        self.yml = os.path.join(os.path.dirname(__file__), 'dynamic_sample.yml')

    def test_load_with_defaults(self):
        fmt = DynamicFormat.load(self.yml)
        fmt.set()
        self.assertEqual(fmt.version, 1)
        self.assertFalse(fmt.flag)
        self.assertEqual(fmt.code, None)

    def test_to_bits_and_from_bytes(self):
        fmt = DynamicFormat.load(self.yml)
        fmt.set(code=5)
        bits = fmt.to_bits()
        data = fmt.to_bytes()
        parsed = DynamicFormat.from_bytes(data, self.yml)
        self.assertEqual(parsed.version, 1)
        self.assertFalse(parsed.flag)
        self.assertEqual(parsed.code, 5)

if __name__ == '__main__':
    unittest.main()
