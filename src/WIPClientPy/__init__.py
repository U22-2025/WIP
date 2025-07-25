"""
WIP (Weather Transport Protocol) クライアントパッケージ
"""

from WIPClientPy.client import Client
from WIPClientPy.client_async import ClientAsync
from wiplib import __version__


# パッケージ情報
__author__ = "WIP Team"


__all__ = [
    "Client",
    "ClientAsync",
]
