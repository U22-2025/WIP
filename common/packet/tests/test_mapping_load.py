import unittest
from pathlib import Path

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

if __name__ == "__main__":
    unittest.main()
