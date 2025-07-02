import pytest
from .dataclass_packet import create_packet_dataclass
from .extended_field import ExtendedField


def test_dynamic_dataclass_roundtrip():
    Packet = create_packet_dataclass('common/packet/request_format.yml')
    pkt = Packet(version=1, packet_id=1, ex_flag=1)
    pkt.ex_field.latitude = 35.0
    pkt.ex_field.longitude = 139.0
    data = pkt.to_bytes()
    restored = Packet.from_bytes(data)
    assert restored.version == 1
    assert restored.packet_id == 1
    assert restored.ex_field.latitude == 35.0
    assert restored.ex_field.longitude == 139.0
