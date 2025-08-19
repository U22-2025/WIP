"""
Minimal stub for python-dotenv to satisfy local interop without external deps.
Provides load_dotenv() no-op.
"""

from typing import Any

def load_dotenv(*args: Any, **kwargs: Any) -> bool:  # type: ignore[override]
    return False

