"""
WTP Packet - Weather Transport Protocol Packet Implementation

このパッケージは、Weather Transport Protocol (WTP) のパケットフォーマット処理を提供します。

基本パケットクラス:
- Request, Response: 汎用的なパケット処理
- Format: 基本的なパケットフォーマット実装

専用パケットクラス（推奨）:
- WeatherRequest, WeatherResponse: エンドユーザー向けAPI
- LocationRequest, LocationResponse: サーバー間通信（座標解決）
- QueryRequest, QueryResponse: サーバー間通信（気象データ取得）
"""

from .exceptions import BitFieldError
from .extended_field import ExtendedField, ExtendedFieldType
from .format import Format
from .request import Request
from .response import Response

# 専用パケットクラス
from .weather_packet import WeatherRequest, WeatherResponse
from .location_packet import LocationRequest, LocationResponse
from .query_packet import QueryRequest, QueryResponse

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
    "WeatherRequest",
    "WeatherResponse",
    "LocationRequest",
    "LocationResponse",
    "QueryRequest",
    "QueryResponse",
]
