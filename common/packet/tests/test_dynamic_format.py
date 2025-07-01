import unittest
from common.packet import DynamicFormat

class TestDynamicFormat(unittest.TestCase):
    def test_basic_flow(self):
        data = {
            'version': 1,
            'packet_id': 10,
            'timestamp': 123456789,
            'area_code': 1000,
        }
        pkt = DynamicFormat.load(data)
        self.assertEqual(pkt.packet_id, 10)

        pkt.set('packet_id', 20)
        self.assertEqual(pkt.packet_id, 20)

        b = pkt.to_bytes()
        restored = DynamicFormat.from_bytes(b)
        d = restored.to_dict()
        self.assertEqual(d['packet_id'], 20)
        self.assertEqual(restored.packet_id, 20)
        self.assertEqual(restored.timestamp, 123456789)

    def test_extended_field_roundtrip(self):
        data = {
            'version': 1,
            'packet_id': 11,
            'ex_flag': 1,
            'timestamp': 111111111,
            'area_code': 2000,
            'ex_field': {
                'alert': ['storm'],
                'latitude': 35.0,
            }
        }
        pkt = DynamicFormat.load(data)
        pkt.set('ex_field', {'longitude': 139.0})

        b = pkt.to_bytes()
        restored = DynamicFormat.from_bytes(b)
        ex = restored.ex_field.to_dict()
        self.assertEqual(ex['alert'], 'storm')
        self.assertAlmostEqual(ex['latitude'], 35.0)
        self.assertAlmostEqual(ex['longitude'], 139.0)
        d = restored.to_dict()
        self.assertEqual(d['ex_field'], ex)

if __name__ == '__main__':
    unittest.main()
