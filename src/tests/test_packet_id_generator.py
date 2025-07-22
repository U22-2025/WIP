import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../srv')))

from WIPCommonPy.clients.utils.packet_id_generator import PacketIDGenerator12Bit


def test_packet_id_wraparound():
    gen = PacketIDGenerator12Bit()
    gen._current = 4095
    first = gen.next_id()
    second = gen.next_id()
    assert first == 4095
    assert second == 0
