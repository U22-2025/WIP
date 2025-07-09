import importlib


def test_common_utils_exports():
    module = importlib.import_module('common.utils')
    for name in module.__all__:
        assert hasattr(module, name)
    assert 'debug_print' not in module.__all__
    assert 'debug_hex' not in module.__all__
