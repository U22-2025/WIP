import threading
import random


class PacketIDGenerator12Bit:
    def __init__(self):
        self._lock = threading.Lock()
        self._current = random.randint(0, 4095)  # 0 - 4095
        self._max_id = 4096  # 2^12

    def next_id(self) -> int:
        with self._lock:
            pid = self._current
            self._current = (self._current + 1) % self._max_id
            return pid

    def next_id_bytes(self) -> bytes:
        """2バイトに12ビット分を格納して返す（上位4ビットは0埋め）"""
        pid = self.next_id()
        return pid.to_bytes(2, byteorder="little")
