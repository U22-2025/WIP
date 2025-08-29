# Weather API Reporter

APIから気象情報を取得してレポートサーバーに送信するツールセットです。

## 概要

このツールセットは以下の流れで動作します：

1. **外部API** → 気象データ取得
2. **データ変換** → WIP形式に変換  
3. **ReportClient** → レポートサーバーに送信
4. **レポートサーバー** → Redisに保存
5. **クエリサーバー** → Redisから読み取りレスポンス

## ファイル構成

```
python/application/tools/
├── weather_api_reporter.py      # メインのレポーター
├── scheduled_weather_reporter.py # 定期実行版
└── README.md                    # このファイル
```

## 特徴

- ✅ **report_client.pyを変更しない** - 既存実装を完全に独立させて使用
- ✅ **分離された設計** - APIレポーター機能は独立モジュール
- ✅ **設定可能** - 環境変数やコマンドライン引数で設定
- ✅ **エラーハンドリング** - 失敗時の適切な処理
- ✅ **定期実行対応** - スケジュール機能付き

## 使用方法

### 1. 基本的な使用方法

```bash
# 単発実行
cd python/application/tools
python weather_api_reporter.py

# 定期実行（スケジュールモード）
python scheduled_weather_reporter.py --mode schedule

# 一回限り実行
python scheduled_weather_reporter.py --mode once
```

### 2. 環境変数設定

```bash
# 必要に応じて設定
export WEATHER_API_KEY="your_api_key_here"
export REPORT_SERVER_HOST="localhost" 
export REPORT_SERVER_PORT="4112"
export DEBUG="false"
```

### 3. コマンドライン引数

```bash
python scheduled_weather_reporter.py \
  --mode schedule \
  --host localhost \
  --port 4112 \
  --debug \
  --api-key "your_api_key"
```

## API設定のカスタマイズ

### 実際のAPIに接続する場合

`weather_api_reporter.py`の`get_weather_from_api`メソッドを修正してください：

```python
def get_weather_from_api(self, city: str) -> Optional[Dict[str, Any]]:
    """実際のAPIエンドポイントに変更"""
    try:
        # 例: OpenWeatherMap API
        url = f"http://api.openweathermap.org/data/2.5/weather"
        params = {
            "q": city,
            "appid": self.api_key,
            "units": "metric"
        }
        response = requests.get(url, params=params)
        response.raise_for_status()
        
        data = response.json()
        
        # APIレスポンスをWIP形式に変換
        return {
            "weather": self._convert_weather_condition(data["weather"][0]["main"]),
            "temperature": data["main"]["temp"],
            "precipitation_prob": data.get("pop", 0) * 100,  # 降水確率
            "alerts": [],  # 警報情報（APIに依存）
            "disasters": []  # 災害情報（APIに依存）
        }
    except Exception as e:
        self.logger.error(f"API呼び出しエラー: {e}")
        return None
```

### エリアコードマッピングの変更

```python
# weather_api_reporter.py内で修正
self.area_mapping = {
    "Tokyo": "130000",
    "Osaka": "270000",
    # 必要に応じて追加
    "YourCity": "123456"
}
```

### 天気コードマッピングの変更

```python
# weather_api_reporter.py内で修正
self.weather_code_mapping = {
    "Clear": 100,      # 晴れ
    "Clouds": 200,     # 曇り
    "Rain": 300,       # 雨
    # APIの値に合わせて修正
}
```

## スケジュール設定

デフォルトのスケジュール：
- **全都市更新**: 06:00, 12:00, 18:00 (1日3回)
- **優先都市更新**: 2時間おき

### スケジュール変更例

```python
# scheduled_weather_reporter.py内で修正
def setup_schedule(self):
    # 毎時更新に変更
    schedule.every().hour.do(self.update_all_cities)
    
    # 30分おきに優先都市更新
    schedule.every(30).minutes.do(self.update_priority_cities)
```

## プログラム内での使用例

```python
from weather_api_reporter import WeatherAPIReporter

# インスタンス作成
reporter = WeatherAPIReporter(
    api_key="your_api_key",
    report_server_host="localhost",
    report_server_port=9999,
    debug=True
)

# 単一都市の処理
success = reporter.process_single_city("Tokyo")

# 複数都市の処理
cities = ["Tokyo", "Osaka", "Sapporo"]
results = reporter.process_multiple_cities(cities)

# 結果確認
for city, success in results.items():
    print(f"{city}: {'成功' if success else '失敗'}")
```

## ログ出力例

```
2024-01-01 12:00:00 - __main__ - INFO - 都市 Tokyo の天気データを処理中...
2024-01-01 12:00:01 - __main__ - INFO - APIからTokyoの天気データを取得しました
2024-01-01 12:00:02 - __main__ - INFO - ✓ レポート送信成功: エリア 130000
2024-01-01 12:00:03 - __main__ - INFO - 更新完了: 成功率 100.0% (1/1)
```

## トラブルシューティング

### レポートサーバーに接続できない
```bash
# デバッグモードで実行
python weather_api_reporter.py --debug

# レポートサーバーの起動確認
# サーバーが4112ポートで起動していることを確認
```

### APIキーエラー
```bash
# 環境変数設定確認
echo $WEATHER_API_KEY

# または直接指定
python scheduled_weather_reporter.py --api-key "your_key"
```

### パス問題
```bash
# PYTHONPATHの確認
export PYTHONPATH="/mnt/c/Users/ポッポ焼き/Desktop/WIP/src:$PYTHONPATH"
```

## 依存関係

- `requests` - API呼び出し用
- `schedule` - 定期実行用  
- `WIPCommonPy.clients.report_client` - レポート送信用（既存）

## 注意事項

1. **report_client.pyは変更しません** - 既存の実装をそのまま使用
2. **API制限に注意** - 外部APIの利用制限を確認してください
3. **エラーハンドリング** - 実運用時は適切なエラー処理を追加してください
4. **ログ管理** - 長期運用時はログローテーションを設定してください