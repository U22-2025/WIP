import unittest
from pathlib import Path
import importlib
import warnings
from unittest import mock

from common.packet.extended_field import ExtendedField
from common.packet.dynamic_format import _safe_load_yaml

class TestDefaultMapping(unittest.TestCase):
    def test_mapping_loaded_from_yaml(self):
        yaml_path = Path(__file__).resolve().parent.parent / "extended_fields.yml"
        data = _safe_load_yaml(yaml_path)
        entries = data.get("extended_fields", data)
        expected = {e["name"]: e["id"] for e in entries}
        self.assertEqual(ExtendedField.FIELD_MAPPING_STR, expected)
        reverse = {v: k for k, v in expected.items()}
        self.assertEqual(ExtendedField.FIELD_MAPPING_INT, reverse)


class TestMappingLoadWarnings(unittest.TestCase):
    def test_warning_on_invalid_yaml(self):
        import common.packet as packet
        with mock.patch(
            'common.packet.dynamic_format._safe_load_yaml',
            side_effect=ValueError('broken')
        ):
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter('always')
                importlib.reload(packet)
            self.assertTrue(any('broken' in str(wi.message) for wi in w))
        importlib.reload(packet)

if __name__ == "__main__":
    unittest.main()
