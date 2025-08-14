External Weather API (FastAPI)

概要
- JMA XML の取得・抽出は本APIサーバ側で実行します。
- 取得結果はDBやRedisではなくローカルJSONファイルに保存します。
- QueryServer はHTTP経由で本APIから気象情報を取得します。

起動方法
- `python python/application/weather_api/start_fastapi_server.py`
- ポート設定: `WEATHER_API_PORT` (既定: 8001)
- スケジューラ: `WEATHER_API_SCHEDULE_ENABLED=true` で有効。
  - 天気更新間隔: `WEATHER_API_WEATHER_INTERVAL_MIN` (既定: 180分)
  - 警報/災害更新間隔: `WEATHER_API_DISASTER_INTERVAL_MIN` (既定: 10分)

エンドポイント
- `GET /health` 健康チェック
- `GET /weather` クエリ例:
  - `?area_code=130010&day=0&weather_flag=1&temperature_flag=1&pop_flag=1&alert_flag=1&disaster_flag=1`
  - Redisに格納済みのデータから必要項目のみを返却
- `POST /update/weather` 気象データ更新を即時実行（JMAから取得→`weather_store.json`へ保存）
- `POST /update/disaster` 警報/災害データ更新を即時実行（JMAから取得→`hazard_store.json`へ保存）

QueryServer の設定
- QueryServer は外部APIを直接参照しません。Redisのみを参照して応答します。

レポート経路（推奨フロー）
- レポートクライアントが本APIから取得 → レポートサーバへType4で送信。
- レポートサーバはRedis（DB）を直接更新し、QueryServerはDBを参照して応答。
- 送信スクリプト: `python python/application/tools/push_api_to_report.py`
  - APIの`/areas`で全エリアコードを取得 → `/weather` で各エリアのデータ取得 → ReportServerへ送信。
  - 環境変数: `WEATHER_API_BASE_URL`, `REPORT_SERVER_HOST`, `REPORT_SERVER_PORT`。
  - ReportServer 側: `src/WIPServerPy/servers/report_server/config.ini` の `[database] enable_database=true` を有効化（Redis直書き実装済）。

保存先
- `python/application/weather_api/data/weather_store.json`
- `python/application/weather_api/data/hazard_store.json`

環境変数
- `WEATHER_API_TARGET_OFFICES`（例: `130000,140000`）: 取得対象の地方予報区コード（JMA forecastの親コード）。
- `WEATHER_API_WEATHER_INTERVAL_MIN`（既定180）: 天気データ更新間隔（分）
- `WEATHER_API_DISASTER_INTERVAL_MIN`（既定10）: 災害/警報データ更新間隔（分）
- `WEATHER_API_SCHEDULE_ENABLED`（既定true）: スケジューラ有効化

備考
- 本APIは既存のXML解析ロジック（AlertDataProcessor, UnifiedDataProcessor）を再利用し、保存のみJSONに変更しています。
