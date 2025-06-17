"""
WIP Packet - Weather Information Protocol Packet Implementation

このパッケージは、Weather Information Protocol (WIP) のパケットフォーマット処理を提供します。
"""

from .exceptions import BitFieldError
from .extended_field import ExtendedField, ExtendedFieldType
from .format import Format
from .request import Request
from .response import Response

__version__ = "1.0.0"
__all__ = [
    "BitFieldError",
    "ExtendedField",
    "ExtendedFieldType",
    "Format",
    "Request",
    "Response",
]
