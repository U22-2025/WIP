# WIPClientPy クライアント送信メソッド一覧

WIPClientPy フォルダ内に含まれる各クライアントクラスで利用できるパケット送信メソッドの概要をまとめます。主に `python/WIP_Client` と `python/common/clients` 以下の実装を対象としています。

## WeatherClient
`python/common/clients/weather_client.py`

### get_weather_data(area_code, weather=True, temperature=True, precipitation_prob=True, alert=False, disaster=False, day=0)
エリアコードを指定して天気データを取得する基本メソッド。取得する要素をフラグで指定できます。
- **area_code**: 文字列または数値のエリアコード
- **weather**: 天気情報を取得するか
- **temperature**: 気温を取得するか
- **precipitation_prob**: 降水確率を取得するか
- **alert**: 警報データを含めるか
- **disaster**: 災害情報を含めるか
- **day**: 予報日 (0=今日)

### _execute_query_request(request)
`QueryRequest` インスタンスを直接送信する内部処理。主に `get_weather_data` から呼び出されます。

### _execute_location_request(request)
座標解決用 `LocationRequest` を送信し、続けて天気レスポンスを待ち受けます。

### 非同期版
- `_execute_query_request_async(request)`
- `_execute_location_request_async(request)`

### get_weather_simple(area_code, include_all=False, day=0)
基本的な項目をまとめて取得する簡易メソッド。`include_all=True` で警報・災害情報も取得します。

## LocationClient
`python/common/clients/location_client.py`

### get_location_data(latitude, longitude, source=None, use_cache=True, enable_debug=None, weather=True, temperature=True, precipitation_prob=True, alert=False, disaster=False, day=0, validate_response=True, force_refresh=False)
座標から位置情報（エリアコード）を取得します。キャッシュ利用やレスポンス検証など多くのオプションを備えます。
- **latitude / longitude**: 座標値
- **source**: 送信元情報 `(ip, port)`
- **use_cache**: キャッシュを利用するか
- **enable_debug**: デバッグ出力を有効化
- **weather / temperature / precipitation_prob / alert / disaster / day**: 取得対象フラグ
- **validate_response**: レスポンスを厳密検証するか
- **force_refresh**: キャッシュを無視して取得するか

### get_location_data_async(...)
`get_location_data` の非同期版。引数は同様です。

### get_area_code_simple(latitude, longitude, source=None, use_cache=True, return_cache_info=False)
`get_location_data` を内部で呼び出し、エリアコードのみを返す簡易メソッド。`return_cache_info=True` でキャッシュヒット情報を得られます。

## QueryClient
`python/common/clients/query_client.py`

### get_weather_data(area_code, weather=False, temperature=False, precipitation_prob=False, alert=False, disaster=False, source=None, timeout=5.0, use_cache=True, day=0, force_refresh=False)
Query サーバーから直接気象データを取得します。
- **area_code**: エリアコード
- **weather / temperature / precipitation_prob / alert / disaster / day**: 取得対象フラグ
- **source**: 送信元情報 `(ip, port)`
- **timeout**: タイムアウト秒
- **use_cache**: キャッシュ利用の有無
- **force_refresh**: キャッシュを無視するか

### get_weather_data_async(...)
上記メソッドの非同期版。

### get_weather_simple(area_code, include_all=False, timeout=5.0, use_cache=True)
主要データをまとめて取得するラッパー。`include_all=True` で警報・災害情報を含めます。

## ReportClient
`python/common/clients/report_client.py`

### send_report_data()
設定済みのセンサーデータをレポートとして送信します。事前に `set_sensor_data` などでデータを設定しておきます。

### send_report_data_async()
レポート送信の非同期版。

### send_data_simple()
現在の設定データを一括送信する簡便メソッド。`send_report_data` を内部で呼び出します。

## 高水準クライアント
`python/WIP_Client/client.py` および `client_async.py` では、上記クライアントをまとめて利用できるラッパークラス `Client`／`ClientAsync` を提供しています。主な送信関連メソッドは以下の通りです。

- **get_weather(...)**: 座標またはエリアコードを基に天気データ取得。`proxy=True` を指定すると WeatherServer 経由で直接パケットを送信します。
- **get_weather_by_coordinates(latitude, longitude, proxy=False, \*\*kwargs)**: 座標指定での取得。
- **get_weather_by_area_code(area_code, proxy=False, \*\*kwargs)**: エリアコード指定での取得。

非同期版 (`ClientAsync`) では同名の非同期メソッドが用意されています。

