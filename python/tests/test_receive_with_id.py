import socket
import pytest
import asyncio

from common.clients.utils import receive_with_id, receive_with_id_async


def _make_packet(pid: int, version: int = 1) -> bytes:
    return ((pid << 4) | version).to_bytes(2, 'little') + b'data'


def test_receive_with_id_skip_until_match():
    server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server.bind(('127.0.0.1', 0))
    addr = ('127.0.0.1', server.getsockname()[1])
    client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    client.sendto(_make_packet(1), addr)
    client.sendto(_make_packet(2), addr)

    data, _ = receive_with_id(server, 2, 1.0)
    pid = (int.from_bytes(data[:2], 'little') >> 4) & 0x0FFF
    assert pid == 2

    client.close()
    server.close()


def test_receive_with_id_timeout():
    server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server.bind(('127.0.0.1', 0))
    with pytest.raises(socket.timeout):
        receive_with_id(server, 1, 0.3)
    server.close()


@pytest.mark.asyncio
async def test_receive_with_id_async():
    server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server.bind(("127.0.0.1", 0))
    addr = ("127.0.0.1", server.getsockname()[1])
    client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    client.setblocking(False)

    client.sendto(_make_packet(5), addr)

    data, _ = await receive_with_id_async(server, 5, 1.0)
    pid = (int.from_bytes(data[:2], "little") >> 4) & 0x0FFF
    assert pid == 5

    client.close()
    server.close()
