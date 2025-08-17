# Client API リファレンス

## wiplib::client::Client

Python互換の統合天気情報クライアント。Python版WIPClientPy.Clientと完全に同等の機能を提供します。

### コンストラクタ

```cpp
Client(double latitude, double longitude, uint32_t area_code,
       const std::string& weather_host, int weather_port,
       const std::string& location_host, int location_port,
       const std::string& query_host, int query_port);
```

**パラメータ:**
- `latitude`: 緯度 (-90.0 ～ 90.0)
- `longitude`: 経度 (-180.0 ～ 180.0)  
- `area_code`: 気象庁エリアコード
- `weather_host`: 天気サーバーのホスト名
- `weather_port`: 天気サーバーのポート番号
- `location_host`: 位置サーバーのホスト名
- `location_port`: 位置サーバーのポート番号
- `query_host`: クエリサーバーのホスト名
- `query_port`: クエリサーバーのポート番号

### 主要メソッド

#### get_weather()

現在設定されている座標またはエリアコードで天気データを取得します。

```cpp
std::optional<WeatherData> get_weather();
```

**戻り値:**
- `std::optional<WeatherData>`: 天気データ（失敗時はnullopt）

**使用例:**
```cpp
auto weather = client.get_weather();
if (weather.has_value()) {
    std::cout << "Temperature: " << weather->temperature << "°C" << std::endl;
}
```

#### get_weather_by_coordinates()

指定した座標で天気データを取得します。

```cpp
std::optional<WeatherData> get_weather_by_coordinates(double latitude, double longitude);
```

**パラメータ:**
- `latitude`: 緯度
- `longitude`: 経度

**戻り値:**
- `std::optional<WeatherData>`: 天気データ

#### get_weather_by_area_code()

指定したエリアコードで天気データを取得します。

```cpp
std::optional<WeatherData> get_weather_by_area_code(uint32_t area_code);
```

**パラメータ:**
- `area_code`: 気象庁エリアコード

**戻り値:**
- `std::optional<WeatherData>`: 天気データ

#### set_coordinates()

クライアントの座標を設定します。

```cpp
void set_coordinates(double latitude, double longitude);
```

**パラメータ:**
- `latitude`: 新しい緯度
- `longitude`: 新しい経度

#### set_server()

サーバー設定を変更します。

```cpp
void set_server(const std::string& weather_host, int weather_port,
                const std::string& location_host, int location_port,
                const std::string& query_host, int query_port);
```

#### get_state()

クライアントの現在の状態を取得します。

```cpp
ClientSnapshot get_state() const;
```

**戻り値:**
- `ClientSnapshot`: 現在の設定値（座標、エリアコード、サーバー情報など）

#### close()

クライアント接続を閉じます。

```cpp
void close();
```

### プロパティアクセス

#### latitude()

現在設定されている緯度を取得します。

```cpp
double latitude() const;
```

#### longitude()

現在設定されている経度を取得します。

```cpp
double longitude() const;
```

#### area_code()

現在設定されているエリアコードを取得します。

```cpp
uint32_t area_code() const;
```

### エラーハンドリング

#### get_last_error()

最後に発生したエラーの詳細を取得します。

```cpp
std::optional<ErrorInfo> get_last_error() const;
```

**戻り値:**
- `std::optional<ErrorInfo>`: エラー情報（エラーコード、日本語メッセージ）

## WeatherData 構造体

天気データを格納する構造体です。

```cpp
struct WeatherData {
    double temperature;              // 気温（℃）
    int humidity;                   // 湿度（%）
    double pressure;                // 気圧（hPa）
    double wind_speed;              // 風速（m/s）
    int wind_direction;             // 風向（度）
    double precipitation;           // 降水量（mm）
    std::time_t timestamp;          // タイムスタンプ
    std::optional<double> visibility;        // 視程（km）
    std::optional<int> uv_index;            // UV指数
    std::optional<int> cloud_coverage;      // 雲量（%）
};
```

## ClientSnapshot 構造体

クライアントの状態を表す構造体です。

```cpp
struct ClientSnapshot {
    double latitude;                // 緯度
    double longitude;               // 経度
    uint32_t area_code;            // エリアコード
    std::string weather_host;       // 天気サーバーホスト
    int weather_port;              // 天気サーバーポート
    std::string location_host;      // 位置サーバーホスト
    int location_port;             // 位置サーバーポート
    std::string query_host;        // クエリサーバーホスト
    int query_port;                // クエリサーバーポート
};
```

## ErrorInfo 構造体

エラー情報を格納する構造体です。

```cpp
struct ErrorInfo {
    int code;                      // エラーコード
    std::string message;           // エラーメッセージ（日本語）
    std::chrono::system_clock::time_point timestamp; // 発生時刻
};
```

## 使用例

### 基本的な使用法

```cpp
#include "wiplib/client/client.hpp"

int main() {
    // クライアントを作成
    wiplib::client::Client client(
        35.6762, 139.6503, 130010,  // 東京の座標とエリアコード
        "weather.example.com", 8080,  // 天気サーバー
        "location.example.com", 8081, // 位置サーバー
        "query.example.com", 8082     // クエリサーバー
    );
    
    // 天気データを取得
    auto weather = client.get_weather();
    if (weather.has_value()) {
        std::cout << "Temperature: " << weather->temperature << "°C" << std::endl;
        std::cout << "Humidity: " << weather->humidity << "%" << std::endl;
        std::cout << "Pressure: " << weather->pressure << " hPa" << std::endl;
    } else {
        // エラー処理
        auto error = client.get_last_error();
        if (error.has_value()) {
            std::cerr << "Error: " << error->message << std::endl;
        }
    }
    
    return 0;
}
```

### 座標による天気取得

```cpp
// 特定の座標で天気を取得
auto weather = client.get_weather_by_coordinates(34.0522, -118.2437); // ロサンゼルス
if (weather.has_value()) {
    std::cout << "LA Temperature: " << weather->temperature << "°C" << std::endl;
}
```

### 座標の変更

```cpp
// 座標を変更
client.set_coordinates(40.7128, -74.0060); // ニューヨーク

// 新しい座標で天気を取得
auto weather = client.get_weather();
```

### クライアント状態の確認

```cpp
auto state = client.get_state();
std::cout << "Current location: (" << state.latitude << ", " << state.longitude << ")" << std::endl;
std::cout << "Area code: " << state.area_code << std::endl;
std::cout << "Weather server: " << state.weather_host << ":" << state.weather_port << std::endl;
```

### エラーハンドリング

```cpp
auto weather = client.get_weather_by_area_code(999999); // 無効なエリアコード
if (!weather.has_value()) {
    auto error = client.get_last_error();
    if (error.has_value()) {
        std::cerr << "エラーコード: " << error->code << std::endl;
        std::cerr << "エラーメッセージ: " << error->message << std::endl;
    }
}
```

## Python版との比較

### Python版
```python
from WIPClientPy import Client

client = Client(35.6762, 139.6503, 130010, "localhost", 8080, "localhost", 8081, "localhost", 8082)
weather = client.get_weather()
print(f"Temperature: {weather.temperature}°C")
```

### C++版
```cpp
#include "wiplib/client/client.hpp"

wiplib::client::Client client(35.6762, 139.6503, 130010, "localhost", 8080, "localhost", 8081, "localhost", 8082);
auto weather = client.get_weather();
if (weather.has_value()) {
    std::cout << "Temperature: " << weather->temperature << "°C" << std::endl;
}
```

APIは完全に互換性があり、移行は非常に簡単です。