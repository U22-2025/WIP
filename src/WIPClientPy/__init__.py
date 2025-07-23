"""
WIP (Weather Transport Protocol) クライアントパッケージ
"""

from .client import Client
from .client_async import ClientAsync


# バージョン情報
__version__ = "1.0.0"

# パッケージ情報
__author__ = "WIP Team"



__all__ = [
    "Client",
    "ClientAsync",
]
