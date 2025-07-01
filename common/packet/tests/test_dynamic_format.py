import importlib
import unittest

from common.packet import dynamic_format

class TestDynamicFormat(unittest.TestCase):
    def test_load_with_fallback_yaml(self):
        # PyYAML がなくても読み込めるか確認
        original_yaml = dynamic_format.yaml
        dynamic_format.yaml = None
        importlib.reload(dynamic_format)
        fmt = dynamic_format.DynamicFormat.load('common/packet/request_format.yml')
        self.assertEqual(len(fmt.field_defs), 14)
        dynamic_format.yaml = original_yaml
        importlib.reload(dynamic_format)

    def test_to_bytes_and_restore(self):
        fmt = dynamic_format.DynamicFormat.load('common/packet/request_format.yml')
        fmt.set(version=1, packet_id=10, ex_flag=1)
        fmt.set_extended(latitude=35.0, longitude=139.0)
        data = fmt.to_bytes()
        restored = dynamic_format.DynamicFormat.from_bytes('common/packet/request_format.yml', data)
        self.assertEqual(restored.values['packet_id'], 10)
        self.assertAlmostEqual(restored.ex_field.latitude, 35.0)

if __name__ == '__main__':
    unittest.main()
