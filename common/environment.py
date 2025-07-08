from __future__ import annotations
import os
from dotenv import load_dotenv

load_dotenv()


def get(key: str, default=None, cast=None):
    value = os.getenv(key, default)
    if cast is int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return default
    if cast is bool:
        return str(value).lower() in ("1", "true", "yes")
    return value
