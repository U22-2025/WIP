import threading
import random

class PacketIDGenerator12Bit:
    """12ビット幅のパケットIDを生成するスレッドセーフなジェネレーター"""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._current = random.randint(0, 4095)
        self._max_id = 4096  # 2^12

    def next_id(self) -> int:
        """次のIDを返す"""
        with self._lock:
            pid = self._current
            self._current = (self._current + 1) % self._max_id
            return pid

    def next_id_bytes(self) -> bytes:
        """2バイトに12ビット分を格納して返す"""
        pid = self.next_id()
        return pid.to_bytes(2, byteorder='little')
