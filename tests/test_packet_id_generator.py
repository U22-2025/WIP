from unittest import mock
from WIPCommonPy.clients.utils.packet_id_generator import PacketIDGenerator12Bit


def test_packet_id_wraparound():
    with mock.patch('random.randint', return_value=4095):
        gen = PacketIDGenerator12Bit()
    assert gen.next_id() == 4095
    assert gen.next_id() == 0  # wrap around
    assert gen.next_id() == 1
