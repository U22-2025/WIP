import random
import pytest
from common.clients.utils.packet_id_generator import PacketIDGenerator12Bit


def test_sequential_and_wraparound(monkeypatch):
    monkeypatch.setattr(random, "randint", lambda a, b: b)  # start near max
    gen = PacketIDGenerator12Bit()
    first = gen.next_id()
    second = gen.next_id()
    third = gen.next_id()
    assert second == (first + 1) % 4096
    assert third == (second + 1) % 4096
    # after wrap-around should be 0 when starting at 4095
    assert first == 4095
    assert second == 0
    assert third == 1
