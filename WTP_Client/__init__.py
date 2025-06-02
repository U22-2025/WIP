"""
WTP (Weather Transport Protocol) クライアントパッケージ
"""

# バージョン情報
__version__ = "1.0.0"

# パッケージ情報
__author__ = "WTP Team"

# クライアントクラスを直接インポート可能にする
def __getattr__(name):
    """遅延インポートを実装"""
    if name == "WeatherClient":
        from common.clients.weather_client import WeatherClient
        return WeatherClient
    elif name == "LocationClient":
        from common.clients.location_client import LocationClient
        return LocationClient
    elif name == "QueryClient":
        from common.clients.query_client import QueryClient
        return QueryClient
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    "WeatherClient", "LocationClient", "QueryClient"
]
