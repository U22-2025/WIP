import asyncio
import logging
import types

import pytest

from WIPCommonPy.utils import redis_log_handler
from WIPCommonPy.utils.redis_log_handler import RedisLogHandler


class DummyRedis:
    def __init__(self, *args, **kwargs):
        self.messages = []

    async def publish(self, channel: str, msg: str):
        self.messages.append((channel, msg))


def _patch_redis(monkeypatch, dummy):
    monkeypatch.setattr(
        redis_log_handler,
        "aioredis",
        types.SimpleNamespace(Redis=lambda **kw: dummy),
    )


@pytest.mark.asyncio
async def test_publish(monkeypatch):
    dummy = DummyRedis()
    _patch_redis(monkeypatch, dummy)
    handler = RedisLogHandler(channel="test.log")
    await handler.publish("hello")
    assert dummy.messages == [("test.log", "hello")]


@pytest.mark.asyncio
async def test_emit_with_running_loop(monkeypatch):
    dummy = DummyRedis()
    _patch_redis(monkeypatch, dummy)
    handler = RedisLogHandler(channel="test.log")
    logger = logging.getLogger("test_logger")
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
    logger.info("sample")
    await asyncio.sleep(0)
    assert dummy.messages == [("test.log", "sample")]


def test_emit_without_running_loop(monkeypatch):
    dummy = DummyRedis()
    _patch_redis(monkeypatch, dummy)
    handler = RedisLogHandler(channel="test.log")
    record = logging.LogRecord(
        name="test", level=logging.INFO, pathname=__file__, lineno=1, msg="msg", args=(), exc_info=None
    )
    monkeypatch.setattr(asyncio, "get_running_loop", lambda: (_ for _ in ()).throw(RuntimeError))
    loop = asyncio.new_event_loop()
    monkeypatch.setattr(asyncio, "run", lambda coro: loop.run_until_complete(coro))
    handler.emit(record)
    loop.close()
    assert dummy.messages == [("test.log", "msg")]
