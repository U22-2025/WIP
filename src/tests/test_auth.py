import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../srv')))

from WIPCommonPy.utils.auth import WIPAuth


def test_auth_hash_roundtrip():
    packet_id = 123
    ts = 456
    phrase = 'secret'
    h = WIPAuth.calculate_auth_hash(packet_id, ts, phrase)
    assert WIPAuth.verify_auth_hash(packet_id, ts, phrase, h)
