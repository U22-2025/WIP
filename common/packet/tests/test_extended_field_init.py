import unittest
import warnings
from common.packet.extended_field import ExtendedField

class TestExtendedFieldInitialization(unittest.TestCase):
    def test_init_with_validation_no_warning(self):
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter('always')
            ef = ExtendedField({'alert': ['津波警報', '高潮警報'], 'latitude': 35.5})
        self.assertEqual(len(w), 0)
        data = ef.to_dict()
        self.assertEqual(data['alert'], '津波警報,高潮警報')
        self.assertAlmostEqual(data['latitude'], 35.5)

    def test_update_emits_warning(self):
        ef = ExtendedField()
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter('always')
            ef.update({'alert': 'storm'})
        self.assertTrue(any(issubclass(item.category, DeprecationWarning) for item in w))
        self.assertEqual(ef.to_dict()['alert'], 'storm')

if __name__ == '__main__':
    unittest.main()
