import importlib


def test_common_packet_models_importable():
    module = importlib.import_module('common.packet.models')
    assert hasattr(module, '__package__')
    sub = importlib.import_module('common.packet.models.request')
    assert hasattr(sub, 'Request')


def test_common_packet_types_importable():
    module = importlib.import_module('common.packet.types')
    assert hasattr(module, '__package__')
    sub = importlib.import_module('common.packet.types.location_packet')
    assert hasattr(sub, 'LocationRequest')
