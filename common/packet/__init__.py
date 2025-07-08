"""
WIP Packet - Weather Transport Protocol Packet Implementation

このパッケージは、Weather Transport Protocol (WIP) のパケットフォーマット処理を提供します。

基本パケットクラス:
- Request, Response: 汎用的なパケット処理
- Format: 基本的なパケットフォーマット実装

専用パケットクラス（推奨）:
- LocationRequest, LocationResponse: サーバー間通信（座標解決）
- QueryRequest, QueryResponse: サーバー間通信（気象データ取得）
"""

from .core.exceptions import BitFieldError
from .core.extended_field import ExtendedField, ExtendedFieldType
from .core.format import Format
from .models.request import Request
from .models.response import Response

# 専用パケットクラス
from .types.location_packet import LocationRequest, LocationResponse
from .types.query_packet import QueryRequest, QueryResponse
from .types.report_packet import ReportRequest, ReportResponse
from .types.error_response import ErrorResponse

__version__ = "1.1.0"
__all__ = [
    # 基本クラス
    "BitFieldError",
    "ExtendedField",
    "ExtendedFieldType",
    "Format",
    "Request",
    "Response",
    # 専用パケットクラス
    "LocationRequest",
    "LocationResponse",
    "QueryRequest",
    "QueryResponse",
    "ReportRequest",
    "ReportResponse",
    "ErrorResponse",
]
