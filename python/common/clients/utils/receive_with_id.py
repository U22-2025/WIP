import socket
import time
import asyncio


def receive_with_id(sock: socket.socket, expected_id: int, timeout: float):
    """指定したパケットIDのデータを受信する。

    Parameters
    ----------
    sock : socket.socket
        受信に使用するソケット
    expected_id : int
        受信を待つパケットのID
    timeout : float
        タイムアウト秒

    Returns
    -------
    tuple[bytes, tuple]
        受信したデータと送信元アドレス

    Raises
    ------
    socket.timeout
        タイムアウトに達した場合
    """
    start = time.time()
    sock.settimeout(timeout)
    while True:
        remaining = timeout - (time.time() - start)
        if remaining <= 0:
            raise socket.timeout("receive timeout")
        sock.settimeout(remaining)
        data, addr = sock.recvfrom(1024)
        if len(data) >= 2:
            value = int.from_bytes(data[:2], byteorder="little")
            packet_id = (value >> 4) & 0x0FFF
            if packet_id == expected_id:
                return data, addr


async def receive_with_id_async(
    sock: socket.socket, expected_id: int, timeout: float
) -> tuple[bytes, tuple]:
    """非同期版 ``receive_with_id``

    Parameters
    ----------
    sock : socket.socket
        受信に使用するソケット
    expected_id : int
        受信を待つパケットのID
    timeout : float
        タイムアウト秒

    Returns
    -------
    tuple[bytes, tuple]
        受信したデータと送信元アドレス

    Raises
    ------
    asyncio.TimeoutError
        タイムアウトに達した場合
    """
    loop = asyncio.get_running_loop()
    start = loop.time()
    sock.setblocking(False)
    while True:
        remaining = timeout - (loop.time() - start)
        if remaining <= 0:
            raise asyncio.TimeoutError("receive timeout")
        try:
            if hasattr(loop, "sock_recvfrom"):
                data, addr = await asyncio.wait_for(loop.sock_recvfrom(sock, 1024), remaining)
            else:
                data, addr = await asyncio.wait_for(
                    loop.run_in_executor(None, sock.recvfrom, 1024), remaining
                )
        except (asyncio.TimeoutError, BlockingIOError) as e:
            if isinstance(e, BlockingIOError):
                continue  # Retry on Windows BlockingIOError
            raise asyncio.TimeoutError("receive timeout")
        if len(data) >= 2:
            value = int.from_bytes(data[:2], byteorder="little")
            packet_id = (value >> 4) & 0x0FFF
            if packet_id == expected_id:
                return data, addr

