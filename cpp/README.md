# WIP C++ Library (wiplib)

## 概要

Python版WIPCommonPy/WIPClientPyと完全互換性を持つC++実装です。同等のパケット仕様と高水準クライアントAPIを提供し、Windows・Linux・macOSでマルチプラットフォーム対応しています。

## 主な機能

- **完全Python互換API**: Python版WIPClientと同一のインターフェース
- **マルチプラットフォーム**: Windows/Linux/macOS対応
- **高性能**: C++ネイティブ実装によるPython版の5-50倍の高速化
- **包括的なクライアント**: Weather/Location/Query/Reportクライアントを統合
- **全パケットタイプ対応**: Location/Query/Report/Error response packets

## ビルド

**必要環境**
- CMake 3.20+
- C++20対応コンパイラ (GCC 10+, Clang 12+, MSVC 2019+)

**Linux/macOS**
```bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --config Release -j
```

**Windows**
```cmd
cmake -S . -B build -G "Visual Studio 17 2022"
cmake --build build --config Release
```

## Python版からの完全移行ガイド

### 1. WeatherClient (天気データ取得)

**Python版:**
```python
from WIPCommonPy.clients.weather_client import WeatherClient

client = WeatherClient(host="localhost", port=4110, debug=True)
client.set_coordinates(35.6895, 139.6917)
weather = client.get_weather()
print(f"Temperature: {weather['temperature']}°C")
```

**C++版:**
```cpp
#include "wiplib/client/weather_client.hpp"

// 環境変数から設定を取得または直接指定
auto client = wiplib::client::WeatherClient::from_env(); // 環境変数使用
// または
// wiplib::client::WeatherClient client("localhost", 4110, true);

wiplib::client::QueryOptions options;
options.weather = true;
options.temperature = true;
options.precipitation_prob = true;

auto result = client.get_weather_by_coordinates(35.6895, 139.6917, options);
if (result.has_value()) {
    std::cout << "Temperature: " << result->temperature.value_or(-999) << "°C" << std::endl;
}
```

### 2. LocationClient (座標→エリアコード変換)

**Python版:**
```python
from WIPCommonPy.clients.location_client import LocationClient

client = LocationClient(host="localhost", port=4109, debug=True)
area_code = client.get_area_code(35.6895, 139.6917)
print(f"Area code: {area_code}")
```

**C++版:**
```cpp
#include "wiplib/client/location_client.hpp"

wiplib::client::LocationClient client("localhost", 4109, true);
auto result = client.get_area_code(35.6895, 139.6917);
if (result.has_value()) {
    std::cout << "Area code: " << result.value() << std::endl;
}
```

### 3. QueryClient (気象データベース直接クエリ)

**Python版:**
```python
from WIPCommonPy.clients.query_client import QueryClient

client = QueryClient(host="localhost", port=4111, debug=True)
data = client.get_weather_data("130010", day=0)
print(f"Weather: {data['weather']}, Temp: {data['temperature']}")
```

**C++版:**
```cpp
#include "wiplib/client/query_client.hpp"

wiplib::client::QueryClient client("localhost", 4111, true);
wiplib::client::QueryOptions options;
options.weather = true;
options.temperature = true;
options.day = 0;

auto result = client.get_weather_data(130010, options);
if (result.has_value()) {
    if (result->weather_code.has_value()) {
        std::cout << "Weather: " << result->weather_code.value() << std::endl;
    }
    if (result->temperature.has_value()) {
        std::cout << "Temperature: " << result->temperature.value() << "°C" << std::endl;
    }
}
```

### 4. ReportClient (IoTセンサーデータ送信)

**Python版:**
```python
from WIPCommonPy.clients.report_client import ReportClient

client = ReportClient(host="localhost", port=4112, debug=True)
client.set_sensor_data(
    area_code="130010",
    weather_code=100,
    temperature=25.5,
    precipitation_prob=30,
    alert=["大雨警報"],
    disaster=["地震情報"]
)
response = client.send_report_data()
print(f"Success: {response['success']}")
```

**C++版:**
```cpp
#include "wiplib/client/report_client.hpp"
#include "wiplib/packet/report_packet.hpp"

wiplib::client::ReportClient client("localhost", 4112, true);

// レポートデータ構造体を作成
wiplib::packet::ReportData data;
data.area_code = 130010;
data.weather_code = 100;
data.temperature = 25.5f;
data.precipitation_prob = 30;
data.alerts = {"大雨警報"};
data.disasters = {"地震情報"};

auto result = client.send_report(data);
if (result.has_value()) {
    std::cout << "Success: " << (result->success ? "true" : "false") << std::endl;
}
```

### 5. 統合Client (Python互換高レベルAPI)

**Python版:**
```python
from WIPClientPy.client import Client

client = Client(
    latitude=35.6895,
    longitude=139.6917,
    area_code="130010",
    weather_host="localhost",
    weather_port=4110,
    location_host="localhost", 
    location_port=4109,
    query_host="localhost",
    query_port=4111
)
weather = client.get_weather()
```

**C++版:**
```cpp
#include "wiplib/client/wip_client.hpp"

// 統合クライアント作成
wiplib::client::WipClient client(
    "localhost", 4110, // weather server
    "localhost", 4109, // location server
    "localhost", 4111, // query server
    "localhost", 4112, // report server (optional)
    true               // debug mode
);

// 座標設定
client.set_coordinates(35.6895, 139.6917);
client.set_area_code("130010");

wiplib::client::QueryOptions options;
options.weather = true;
options.temperature = true;
options.precipitation_prob = true;

auto weather = client.get_weather(options);
if (weather.has_value()) {
    std::cout << "Temperature: " << weather->temperature.value_or(-999) << "°C" << std::endl;
}
```

### 6. 非同期処理

**Python版:**
```python
import asyncio
from WIPCommonPy.clients.weather_client import WeatherClient

async def get_weather_async():
    client = WeatherClient()
    # Python版は基本的に同期のみ
    return client.get_weather()
```

**C++版:**
```cpp
#include "wiplib/client/async_weather_client.hpp"
#include <future>

wiplib::client::AsyncWeatherClient async_client("localhost", 4110, true);

// 非同期で天気データを取得
wiplib::client::QueryOptions options;
options.weather = true;
options.temperature = true;

// std::futureを使用した非同期実行
auto future = std::async(std::launch::async, [&]() {
    return async_client.get_weather_by_coordinates(35.6895, 139.6917, options);
});

auto weather = future.get();
if (weather.has_value()) {
    std::cout << "Temperature: " << weather->temperature.value_or(-999) << "°C" << std::endl;
}
```

## CLI完全使用ガイド

### unified_client_cli (統合CLIツール)

**天気データ取得**
```bash
# 座標指定で天気取得
./build/unified_client_cli weather --coords 35.6895 139.6917

# エリアコード指定で天気取得
./build/unified_client_cli weather --area 130010

# プロキシ経由で取得
./build/unified_client_cli weather --coords 35.6895 139.6917 --proxy

# 特定項目のみ取得
./build/unified_client_cli weather --area 130010 --no-precipitation --alerts --disaster

# 未来の天気取得（day=0-7）
./build/unified_client_cli weather --area 130010 --day 3

# カスタムサーバー指定
./build/unified_client_cli weather --host 192.168.1.100 --port 4110 --coords 35.6895 139.6917
```

**センサーデータレポート送信**
```bash
# 基本的なセンサーデータ送信
./build/unified_client_cli report --area 130010 --temp 25.5

# 天気コード付きレポート
./build/unified_client_cli report --area 130010 --weather-code 200 --temp 18.2 --precipitation 60

# 警報・災害情報付きレポート
./build/unified_client_cli report --area 130010 --temp 30.1 --alert "大雨警報" --alert "洪水注意報" --disaster "地震情報"

# レポートサーバー指定
./build/unified_client_cli report --host 192.168.1.200 --port 4112 --area 130010 --temp 22.0
```

**認証オプション**
```bash
# 認証有効化
./build/unified_client_cli weather --coords 35.6895 139.6917 --auth-enabled

# サーバー別認証設定
./build/unified_client_cli weather --area 130010 --auth-weather "weather_pass" --auth-location "location_pass"

# 環境変数から認証情報取得（推奨）
export WIP_AUTH_WEATHER="your_weather_password"
export WIP_AUTH_LOCATION="your_location_password"
./build/unified_client_cli weather --area 130010 --auth-enabled
```

### wip_client_cli (専用Weatherクライアント)

**プロキシモード**
```bash
# Weather Server経由（プロキシモード）
./build/wip_client_cli --proxy --host localhost --port 4110 --coords 35.6895 139.6917

# 出力項目制御
./build/wip_client_cli --proxy --area 130010 --no-weather --temperature --precipitation --alerts
```

**ダイレクトモード**
```bash
# Location/Query Server直接接続
./build/wip_client_cli --coords 35.6895 139.6917 --location-host localhost --location-port 4109 --query-host localhost --query-port 4111

# 特定の日の天気（day 0-7）
./build/wip_client_cli --area 130010 --day 3 --location-host localhost --location-port 4109
```

### 開発・デバッグツール

**パケット解析**
```bash
# パケットデコード
./build/wip_packet_decode --file packet.bin

# パケット生成・テスト
./build/wip_packet_gen --type location --area 130010 --coords 35.6895 139.6917
```

**パケット分析**
```bash
# パケットラウンドトリップテスト
./build/wip_packet_roundtrip --area 130010 --weather --temperature

# パケット生成とデバッグ
./build/packet_encoding_debug --coords 35.6895 139.6917
```

**モックサーバー**
```bash
# テスト用Report Server起動
./build/mock_report_server --port 4112 --debug
```

**非同期クライアント**
```bash
# 非同期天気クライアント
./build/async_weather_cli --host localhost --port 4110 --area 130010 --weather

# 認証変数テスト
./build/test_auth_vars
```

**レポートツール**
```bash
# レポートデバッグツール
./build/report_debug_tool --area 130010 --temperature 25.5
```

## 全パケットタイプ対応

**対応パケット一覧:**
- **LocationRequest/Response**: GPS座標→エリアコード変換
- **QueryRequest/Response**: 気象データベース直接クエリ
- **ReportRequest/Response**: IoTセンサーデータ送信
- **ErrorResponse**: エラーハンドリング
- **ExtendedField**: 拡張データフィールド（警報・災害情報）

**パケット拡張フィールド:**
- Alert情報（注意報・警報）
- Disaster情報（地震・津波等）
- 座標情報（緯度・経度）
- タイムスタンプ
- カスタムデータ

## 認証・セキュリティ

**環境変数による認証設定:**
```bash
export WIP_AUTH_ENABLED=true
export WIP_AUTH_WEATHER="your_weather_password"
export WIP_AUTH_LOCATION="your_location_password" 
export WIP_AUTH_QUERY="your_query_password"
export WIP_AUTH_REPORT="your_report_password"
export WIP_VERIFY_RESPONSE=true
```

**プログラム内認証設定:**
```cpp
#include "wiplib/client/auth_config.hpp"

wiplib::client::AuthConfig auth;
auth.enabled = true;
auth.weather_passphrase = "weather_pass";
auth.verify_response = true;

wiplib::client::WeatherClient client("localhost", 4110);
client.set_auth_config(auth);
```

## エラーハンドリング

**C++版エラーハンドリング:**
```cpp
#include "wiplib/client/weather_client.hpp"
#include "wiplib/expected.hpp"

wiplib::client::WeatherClient client("localhost", 4110, true);
wiplib::client::QueryOptions options;
options.weather = true;
options.temperature = true;

auto result = client.get_weather_by_coordinates(35.6895, 139.6917, options);
if (!result.has_value()) {
    std::cerr << "Weather request failed" << std::endl;
    return 1;
}

// よりC++らしい記述
if (result) {
    if (result->temperature) {
        std::cout << "Temperature: " << result->temperature.value() << "°C" << std::endl;
    } else {
        std::cout << "Temperature data not available" << std::endl;
    }
} else {
    std::cerr << "Failed to retrieve weather data" << std::endl;
}
```

## ライセンス

MIT License