import asyncio
import socket
import pytest

from common.clients.utils import safe_sock_sendto

@pytest.mark.asyncio
async def test_safe_sock_sendto_fallback(monkeypatch):
    loop = asyncio.get_running_loop()

    async def raise_notimpl(sock, data, addr):
        raise NotImplementedError

    monkeypatch.setattr(loop, "sock_sendto", raise_notimpl, raising=False)

    sender = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    receiver = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    receiver.bind(("127.0.0.1", 0))
    addr = ("127.0.0.1", receiver.getsockname()[1])

    await safe_sock_sendto(loop, sender, b"hello", addr)
    if hasattr(loop, "sock_recvfrom"):
        data, _ = await loop.sock_recvfrom(receiver, 1024)
    else:
        data, _ = await loop.run_in_executor(None, receiver.recvfrom, 1024)

    assert data == b"hello"

    sender.close()
    receiver.close()

