import asyncio
from typing import Any, Tuple

async def safe_sock_sendto(loop: asyncio.AbstractEventLoop, sock: Any, data: bytes, addr: Tuple[str, int]):
    """``loop.sock_sendto`` の ``NotImplementedError`` を回避するヘルパー。

    ``uvloop`` 使用時、 ``sock_sendto`` が未実装の場合があるため、
    ``create_datagram_endpoint`` を用いて送信を行う。
    """
    if hasattr(loop, "sock_sendto"):
        try:
            return await loop.sock_sendto(sock, data, addr)
        except NotImplementedError:
            pass
    transport, _ = await loop.create_datagram_endpoint(
        lambda: asyncio.DatagramProtocol(), remote_addr=addr
    )
    transport.sendto(data)
    transport.close()

