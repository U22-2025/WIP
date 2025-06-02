"""
WTP (Weather Transport Protocol) サーバーパッケージ
天気情報転送プロトコルの実装
"""

# バージョン情報
__version__ = "1.0.0"

# パッケージ情報
__author__ = "WTP Team"

# 遅延インポートを使用してサーバークラスを公開
def __getattr__(name):
    """遅延インポートを実装"""
    if name == "WeatherServer":
        from .servers.weather_server import WeatherServer
        return WeatherServer
    elif name == "LocationServer":
        from .servers.location_server import LocationServer
        return LocationServer
    elif name == "QueryServer":
        from .servers.query_server import QueryServer
        return QueryServer
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    "servers", "data", "utils",
    "WeatherServer", "LocationServer", "QueryServer"
]
