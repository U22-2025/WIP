import socket
import time


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

