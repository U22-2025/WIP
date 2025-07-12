"""
WIP クライアントパッケージ

遅延インポートにより環境変数未設定時の読み込みエラーを防ぐ。

## 統一された命名規則

### メインメソッド:
- LocationClient: get_location_data() - 座標から位置情報を取得
- QueryClient: get_weather_data() - エリアコードから気象データを取得
- ReportClient: send_report_data() - センサーデータレポートを送信
- WeatherClient: get_weather_data() - エリアコードから気象データを取得

### 簡便メソッド:
- LocationClient: get_area_code_simple() - 座標からエリアコードのみ取得
- QueryClient: get_weather_simple() - 基本気象データを一括取得
- ReportClient: send_data_simple() - 設定済みデータで送信
- WeatherClient: get_weather_simple() - 基本気象データを一括取得

### 後方互換性:
すべてのクライアントで旧メソッド名のエイリアスを提供。
新しいコードでは統一された命名規則を使用してください。
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
