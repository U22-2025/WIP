"""
Minimal stub for redis.asyncio to satisfy local interop.
Provides Redis class with async publish().
"""
from __future__ import annotations

from typing import Any


class Redis:
    def __init__(self, host: str = "localhost", port: int = 6379, db: int = 0, decode_responses: bool = False, **kwargs: Any) -> None:
        self.host = host
        self.port = port
        self.db = db
        self.decode_responses = decode_responses

    async def publish(self, channel: str, message: str) -> int:  # pragma: no cover - stub
        # No-op stub that pretends to publish successfully
        return 1

