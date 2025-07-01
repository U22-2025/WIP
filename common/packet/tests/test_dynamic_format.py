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

if __name__ == '__main__':
    unittest.main()
