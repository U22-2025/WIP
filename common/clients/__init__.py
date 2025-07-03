"""
WIP クライアントパッケージ

遅延インポートにより環境変数未設定時の読み込みエラーを防ぐ。
"""

__all__ = [
    'LocationClient',
    'QueryClient',
    'WeatherClient',
    'ReportClient',
]

def __getattr__(name):
    if name == 'LocationClient':
        from .location_client import LocationClient
        return LocationClient
    if name == 'QueryClient':
        from .query_client import QueryClient
        return QueryClient
    if name == 'WeatherClient':
        from .weather_client import WeatherClient
        return WeatherClient
    if name == 'ReportClient':
        from .report_client import ReportClient
        return ReportClient
    raise AttributeError(f"module {__name__} has no attribute {name}")
