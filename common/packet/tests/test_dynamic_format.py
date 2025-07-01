import unittest
from common.packet.dynamic_format import DynamicFormat

class TestDynamicFormat(unittest.TestCase):
    def test_duplicate_name_raises(self):
        fields = [
            {'name': 'a', 'length': 1},
            {'name': 'a', 'length': 2},
        ]
        with self.assertRaises(ValueError):
            DynamicFormat.load(fields)

    def test_length_must_be_positive(self):
        fields = [
            {'name': 'a', 'length': 0},
        ]
        with self.assertRaises(ValueError):
            DynamicFormat.load(fields)

    def test_load_success(self):
        fields = [
            {'name': 'a', 'length': 1},
            {'name': 'b', 'length': 2},
        ]
        fmt = DynamicFormat.load(fields)
        self.assertEqual(len(fmt.fields), 2)

if __name__ == '__main__':
    unittest.main()
