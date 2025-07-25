# WIP Python Client Library

WIP (Weather Transfer Protocol) のクライアント機能を提供する Python ライブラリです。
`common` モジュールの低水準実装と `WIP_Client` の高水準ラッパーから構成されており、
簡単に気象データを取得できます。

## ディレクトリ構成

```
python/
├── common/      # パケット定義・低水準クライアント・ユーティリティ
└── WIP_Client/  # 同期 / 非同期の高水準クライアント
```

### common
- **packet/**: WIP パケットフォーマットの定義とユーティリティ
- **clients/**: WeatherClient・QueryClient などの低水準クライアント群
- **utils/**: キャッシュやネットワーク処理の補助関数

### WIP_Client
- **client.py**: 同期版クライアント `Client`
- **client_async.py**: 非同期版クライアント `ClientAsync`
- **config.ini**: 参考用設定ファイル

## インストール

```
# 依存パッケージをインストール
pip install -r requirements.txt
```

`WEATHER_SERVER_HOST` と `WEATHER_SERVER_PORT` の環境変数を設定するか、
`Client` / `ClientAsync` の引数でホスト名・ポートを指定してください。

## 使い方

### 同期クライアント

```python
from WIP_Client import Client

client = Client(host="localhost", port=4110)
client.set_coordinates(35.6895, 139.6917)
weather = client.get_weather()
print(weather)
client.close()
```

### 非同期クライアント

```python
import asyncio
from WIP_Client import ClientAsync

async def main():
    async with ClientAsync(debug=True) as c:
        c.set_coordinates(35.6895, 139.6917)
        weather = await c.get_weather()
        print(weather)

asyncio.run(main())
```

## 各種パケット送信

### 位置解決パケット (LocationRequest)

緯度・経度からエリアコードを取得するには `LocationClient` を利用します。

```python
from common.clients import LocationClient

client = LocationClient(host="localhost", port=4000)
# 座標を指定して LocationRequest を送信
resp = client.get_location_data(35.6895, 139.6917)
print(resp.get_area_code())
client.close()
```

### 気象データ取得パケット (QueryRequest)

既にエリアコードが分かっている場合は `QueryClient` で `QueryRequest` を送信します。

```python
from common.clients import QueryClient

client = QueryClient(host="localhost", port=4111)
resp = client.get_weather_data("011000", weather=True, temperature=True)
print(resp.get_response_summary())
client.close()
```

クエリが不正な場合は `ErrorResponse` が返ります。以下のようにして内容を確認できます。

```python
from common.packet import ErrorResponse

err = ErrorResponse.from_bytes(raw_data)
print(err.error_code, err.message)
```

### センサーデータのレポート送信

IoT機器からサーバへ観測データを送る場合は `ReportClient` を使用します。

```python
from common.clients import ReportClient

report = ReportClient(host="localhost", port=4110)
report.set_sensor_data(
    area_code="011000",
    weather_code=100,
    temperature=25.5,
    precipitation_prob=30,
)
resp = report.send_report_data()
print(resp)
report.close()
```

### Location サーバを経由しない直接通信

`Client` 系メソッドに `proxy=True` を指定すると、Location サーバを介さず
Weather Server へ直接リクエストを送信します。

```python
client = Client()
client.set_coordinates(35.6895, 139.6917)
weather = client.get_weather(proxy=True)
```
## ライセンス


本ライブラリは MIT ライセンスの下で公開されています。
