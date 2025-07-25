import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../srv')))

import WIPCommonPy.packet.dynamic_format as df


def test_load_base_fields():
    data = df.load_base_fields()
    assert 'version' in data
    assert data['version']['length'] == 4


def test_reload_base_fields_equals_load():
    assert df.load_base_fields() == df.reload_base_fields()


def test_load_extended_fields():
    data = df.load_extended_fields()
    assert data['alert']['id'] == 1
    assert data['longitude']['type'] == 'float'


def test_load_response_fields():
    data = df.load_response_fields()
    assert 'weather_code' in data
    assert data['weather_code']['length'] == 16
