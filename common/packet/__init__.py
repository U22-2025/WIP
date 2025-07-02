"""
WIP Packet - Weather Transport Protocol Packet Implementation

このパッケージは、Weather Transport Protocol (WIP) のパケットフォーマット処理を提供します。

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
from .dynamic_format import DynamicFormat, _safe_load_yaml
from .request import Request
from .response import Response

# 専用パケットクラス
from .weather_packet import WeatherRequest, WeatherResponse
from .location_packet import LocationRequest, LocationResponse
from .query_packet import QueryRequest, QueryResponse
from .error_response import ErrorResponse  # エラーパケット追加

# デフォルトの拡張フィールド定義を読み込んでマッピングを更新
try:
    from pathlib import Path

    ext_path = Path(__file__).resolve().parent / "extended_fields.yml"
    if ext_path.exists():
        ext_data = _safe_load_yaml(ext_path)
        entries = ext_data.get("extended_fields", ext_data)
        if isinstance(entries, list):
            ExtendedField.update_mapping(entries)
except Exception:
    # 定義ファイルが存在しない場合や読み込みエラーは無視
    pass

__version__ = "1.1.0"
__all__ = [
    # 基本クラス
    "BitFieldError",
    "ExtendedField",
    "ExtendedFieldType",
    "Format",
    "DynamicFormat",
    "Request",
    "Response",
    # 専用パケットクラス
    "WeatherRequest",
    "WeatherResponse",
    "LocationRequest",
    "LocationResponse",
    "QueryRequest",
    "QueryResponse",
    "ErrorResponse",  # エラーパケット追加
]
