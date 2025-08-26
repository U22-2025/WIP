import asyncio
import logging
import os
from typing import Any

import redis.asyncio as aioredis


class RedisLogHandler(logging.Handler):
    """RedisへログをPublishするハンドラー"""

    def __init__(
        self,
        host: str | None = None,
        port: int | None = None,
        db: int | None = None,
        channel: str = "wip.log",
    ) -> None:
        super().__init__()
        self.host = host or os.getenv("LOG_REDIS_HOST", "localhost")
        self.port = int(port or os.getenv("LOG_REDIS_PORT", 6380))
        self.db = int(db or os.getenv("LOG_REDIS_DB", 0))
        self.channel = channel
        self.redis = aioredis.Redis(
            host=self.host, port=self.port, db=self.db, decode_responses=True
        )

    async def publish(self, message: str) -> None:
        await self.redis.publish(self.channel, message)

    def emit(self, record: logging.LogRecord) -> None:  # pragma: no cover - async
        msg = self.format(record)
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self.publish(msg))
        except RuntimeError:  # no running loop
            asyncio.run(self.publish(msg))
