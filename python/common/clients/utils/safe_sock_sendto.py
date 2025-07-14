import asyncio
from typing import Any, Tuple

async def safe_sock_sendto(loop: asyncio.AbstractEventLoop, sock: Any, data: bytes, addr: Tuple[str, int]):
    """``loop.sock_sendto`` の ``NotImplementedError`` を回避するヘルパー。

    ``uvloop`` 使用時 ``sock_sendto`` が未実装の場合があるため、
    ``run_in_executor`` によるフォールバックを行う。
    """
    if hasattr(loop, "sock_sendto"):
        try:
            return await loop.sock_sendto(sock, data, addr)
        except NotImplementedError:
            pass

    blocking = None
    if hasattr(sock, "getblocking"):
        blocking = sock.getblocking()
        if not blocking:
            sock.setblocking(True)

    try:
        await loop.run_in_executor(None, sock.sendto, data, addr)
    finally:
        if blocking is not None and not blocking:
            sock.setblocking(False)

