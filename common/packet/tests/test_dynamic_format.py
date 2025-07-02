import importlib
import unittest

from common.packet import dynamic_format
from common.packet.extended_field import ExtendedField

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

    def test_checksum_validation(self):
        fmt = dynamic_format.DynamicFormat.load('common/packet/request_format.yml')
        fmt.set(version=1, packet_id=99)
        data = fmt.to_bytes()
        # 正常なデータから復元できること
        restored = dynamic_format.DynamicFormat.from_bytes('common/packet/request_format.yml', data)
        self.assertEqual(restored.values['checksum'], fmt.values['checksum'])

        # データを改ざんするとエラーになること
        tampered = bytearray(data)
        tampered[0] ^= 0xFF
        with self.assertRaises(ValueError):
            dynamic_format.DynamicFormat.from_bytes('common/packet/request_format.yml', bytes(tampered))

    def test_to_dict_with_extended(self):
        fmt = dynamic_format.DynamicFormat.load('common/packet/request_format.yml')
        fmt.set(version=1, packet_id=5, ex_flag=1)
        fmt.set_extended(alert='台風')
        data = fmt.to_bytes()
        restored = dynamic_format.DynamicFormat.from_bytes('common/packet/request_format.yml', data)
        result = restored.to_dict()
        self.assertIn('ex_field', result)
        self.assertEqual(result['ex_field']['alert'], '台風')

    def test_ex_flag_without_extended_data(self):
        fmt = dynamic_format.DynamicFormat.load('common/packet/request_format.yml')
        fmt.set(version=1, packet_id=1, ex_flag=0)
        fmt.set_extended(alert='無視されるデータ')
        data = fmt.to_bytes()
        # 拡張フィールドが含まれないため、常に最小長16バイトになる
        self.assertEqual(len(data), 16)
        restored = dynamic_format.DynamicFormat.from_bytes('common/packet/request_format.yml', data)
        self.assertTrue(restored.ex_field.is_empty())

    def test_field_value_range(self):
        fmt = dynamic_format.DynamicFormat.load('common/packet/request_format.yml')
        fmt.set(version=16)  # version は4ビットのため16は範囲外
        with self.assertRaises(ValueError):
            fmt.to_bytes()

    def test_calc_checksum12(self):
        self.assertEqual(dynamic_format.DynamicFormat.calc_checksum12(bytes([0]*16)), 0xFFF)
        self.assertEqual(dynamic_format.DynamicFormat.calc_checksum12(bytes([1]*4)), 0xFFB)

    def test_custom_format_with_external_extended(self):
        original_int = ExtendedField.FIELD_MAPPING_INT.copy()
        original_str = ExtendedField.FIELD_MAPPING_STR.copy()
        try:
            fmt = dynamic_format.DynamicFormat.load(
                'common/packet/tests/custom_request_format.yml'
            )
            fmt.set(version=1, packet_id=7, ex_flag=1, extra_field=42)
            fmt.set_extended(extra_info=123)
            data = fmt.to_bytes()
            restored = dynamic_format.DynamicFormat.from_bytes(
                'common/packet/tests/custom_request_format.yml', data
            )
            self.assertEqual(restored.values['extra_field'], 42)
            self.assertEqual(restored.ex_field.to_dict().get('extra_info'), 123)
            self.assertIn('extra_info', ExtendedField.FIELD_MAPPING_STR)
        finally:
            ExtendedField.FIELD_MAPPING_INT = original_int
            ExtendedField.FIELD_MAPPING_STR = original_str

if __name__ == '__main__':
    unittest.main()
