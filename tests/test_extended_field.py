import warnings
from WIPCommonPy.packet.core.extended_field import ExtendedField


def test_property_access_no_deprecation_warning():
    ex = ExtendedField()
    with warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)
        ex.alert = ["津波警報"]
        assert ex.alert == "津波警報"


def test_get_set_emit_deprecation_warning():
    ex = ExtendedField()
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always", DeprecationWarning)
        ex.set("alert", "津波警報")
        ex.get("alert")
        assert any(isinstance(rec.message, DeprecationWarning) for rec in w)
