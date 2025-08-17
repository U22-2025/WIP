# ClientAsync API リファレンス

## wiplib::client::ClientAsync

Python互換の非同期天気情報クライアント。Python版WIPClientPy.ClientAsyncと完全に同等の機能を提供します。

### コンストラクタ

```cpp
ClientAsync(double latitude, double longitude, uint32_t area_code,
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

### 非同期メソッド

#### get_weather_async()

現在設定されている座標またはエリアコードで天気データを非同期取得します。

```cpp
std::future<std::optional<WeatherData>> get_weather_async();
```

**戻り値:**
- `std::future<std::optional<WeatherData>>`: 天気データのfuture

**使用例:**
```cpp
auto future = client.get_weather_async();
auto weather = future.get();
if (weather.has_value()) {
    std::cout << "Temperature: " << weather->temperature << "°C" << std::endl;
}
```

#### get_weather_by_coordinates_async()

指定した座標で天気データを非同期取得します。

```cpp
std::future<std::optional<WeatherData>> get_weather_by_coordinates_async(double latitude, double longitude);
```

**パラメータ:**
- `latitude`: 緯度
- `longitude`: 経度

**戻り値:**
- `std::future<std::optional<WeatherData>>`: 天気データのfuture

#### get_weather_by_area_code_async()

指定したエリアコードで天気データを非同期取得します。

```cpp
std::future<std::optional<WeatherData>> get_weather_by_area_code_async(uint32_t area_code);
```

**パラメータ:**
- `area_code`: 気象庁エリアコード

**戻り値:**
- `std::future<std::optional<WeatherData>>`: 天気データのfuture

#### set_coordinates_async()

クライアントの座標を非同期で設定します。

```cpp
std::future<void> set_coordinates_async(double latitude, double longitude);
```

**パラメータ:**
- `latitude`: 新しい緯度
- `longitude`: 新しい経度

**戻り値:**
- `std::future<void>`: 設定完了のfuture

#### set_server_async()

サーバー設定を非同期で変更します。

```cpp
std::future<void> set_server_async(const std::string& weather_host, int weather_port,
                                   const std::string& location_host, int location_port,
                                   const std::string& query_host, int query_port);
```

**戻り値:**
- `std::future<void>`: 設定完了のfuture

### 同期メソッド（継承）

ClientAsyncは、通常のClientクラスを継承しているため、同期メソッドも利用できます：

- `get_weather()`
- `get_weather_by_coordinates()`
- `get_weather_by_area_code()`
- `set_coordinates()`
- `set_server()`
- `get_state()`
- `close()`

### 同期制御

ClientAsyncは、Python の `asyncio.Lock` 相当の同期制御機能を提供します：

#### 内部ミューテックス

```cpp
private:
    std::mutex async_mutex_;  // Python asyncio.Lock 相当の同期制御
```

複数の非同期操作が同時に実行される場合、内部的にミューテックスで同期が取られます。

### タイムアウト設定

#### set_timeout()

非同期操作のタイムアウト時間を設定します。

```cpp
void set_timeout(std::chrono::milliseconds timeout);
```

**パラメータ:**
- `timeout`: タイムアウト時間（ミリ秒）

## 使用例

### 基本的な非同期操作

```cpp
#include "wiplib/client/client_async.hpp"
#include <future>

int main() {
    // 非同期クライアントを作成
    wiplib::client::ClientAsync client(
        35.6762, 139.6503, 130010,
        "weather.example.com", 8080,
        "location.example.com", 8081,
        "query.example.com", 8082
    );
    
    // 非同期で天気データを取得
    auto future = client.get_weather_async();
    
    // 他の処理を実行...
    std::cout << "天気データを取得中..." << std::endl;
    
    // 結果を取得
    auto weather = future.get();
    if (weather.has_value()) {
        std::cout << "Temperature: " << weather->temperature << "°C" << std::endl;
    }
    
    return 0;
}
```

### 複数の同時非同期リクエスト

```cpp
#include "wiplib/client/client_async.hpp"
#include <vector>
#include <future>

int main() {
    wiplib::client::ClientAsync client(35.6762, 139.6503, 130010, 
                                       "localhost", 8080, "localhost", 8081, "localhost", 8082);
    
    // 複数のエリアコードで同時にリクエスト
    std::vector<uint32_t> area_codes = {130010, 140010, 270000, 230010};
    std::vector<std::future<std::optional<WeatherData>>> futures;
    
    // 非同期リクエストを開始
    for (uint32_t area_code : area_codes) {
        futures.push_back(client.get_weather_by_area_code_async(area_code));
    }
    
    // すべての結果を取得
    for (size_t i = 0; i < futures.size(); ++i) {
        auto weather = futures[i].get();
        if (weather.has_value()) {
            std::cout << "Area " << area_codes[i] 
                      << ": " << weather->temperature << "°C" << std::endl;
        }
    }
    
    return 0;
}
```

### タイムアウト付き非同期操作

```cpp
#include "wiplib/client/client_async.hpp"
#include <chrono>

int main() {
    wiplib::client::ClientAsync client(35.6762, 139.6503, 130010,
                                       "localhost", 8080, "localhost", 8081, "localhost", 8082);
    
    // 5秒のタイムアウトを設定
    client.set_timeout(std::chrono::milliseconds(5000));
    
    auto future = client.get_weather_async();
    
    // タイムアウト付きで結果を待機
    auto status = future.wait_for(std::chrono::seconds(10));
    
    if (status == std::future_status::ready) {
        auto weather = future.get();
        if (weather.has_value()) {
            std::cout << "Temperature: " << weather->temperature << "°C" << std::endl;
        } else {
            std::cout << "天気データの取得に失敗しました" << std::endl;
        }
    } else {
        std::cout << "タイムアウトしました" << std::endl;
    }
    
    return 0;
}
```

### 非同期設定変更

```cpp
#include "wiplib/client/client_async.hpp"

int main() {
    wiplib::client::ClientAsync client(35.6762, 139.6503, 130010,
                                       "localhost", 8080, "localhost", 8081, "localhost", 8082);
    
    // 座標を非同期で変更
    auto coord_future = client.set_coordinates_async(40.7128, -74.0060); // ニューヨーク
    
    // サーバー設定を非同期で変更
    auto server_future = client.set_server_async("new-weather.example.com", 8080,
                                                  "new-location.example.com", 8081,
                                                  "new-query.example.com", 8082);
    
    // 設定変更の完了を待機
    coord_future.get();
    server_future.get();
    
    // 新しい設定で天気データを取得
    auto weather_future = client.get_weather_async();
    auto weather = weather_future.get();
    
    return 0;
}
```

### Python asyncio パターンの再現

```cpp
#include "wiplib/client/client_async.hpp"
#include <vector>
#include <future>

// Python の asyncio.gather() 相当の実装
template<typename... Futures>
auto gather(Futures&&... futures) {
    return std::make_tuple(futures.get()...);
}

int main() {
    wiplib::client::ClientAsync client(35.6762, 139.6503, 130010,
                                       "localhost", 8080, "localhost", 8081, "localhost", 8082);
    
    // 複数のタスクを作成（Python の asyncio.create_task 相当）
    auto task1 = client.get_weather_by_area_code_async(130010);
    auto task2 = client.get_weather_by_area_code_async(140010);
    auto task3 = client.get_weather_by_area_code_async(270000);
    
    // すべてのタスクの完了を待機（Python の asyncio.gather 相当）
    auto results = gather(std::move(task1), std::move(task2), std::move(task3));
    
    // 結果を処理
    auto& [weather1, weather2, weather3] = results;
    
    if (weather1.has_value()) {
        std::cout << "東京: " << weather1->temperature << "°C" << std::endl;
    }
    if (weather2.has_value()) {
        std::cout << "横浜: " << weather2->temperature << "°C" << std::endl;
    }
    if (weather3.has_value()) {
        std::cout << "大阪: " << weather3->temperature << "°C" << std::endl;
    }
    
    return 0;
}
```

### エラーハンドリング

```cpp
#include "wiplib/client/client_async.hpp"

int main() {
    wiplib::client::ClientAsync client(35.6762, 139.6503, 130010,
                                       "localhost", 8080, "localhost", 8081, "localhost", 8082);
    
    try {
        auto future = client.get_weather_by_area_code_async(999999); // 無効なエリアコード
        auto weather = future.get();
        
        if (!weather.has_value()) {
            auto error = client.get_last_error();
            if (error.has_value()) {
                std::cerr << "エラー: " << error->message << std::endl;
            }
        }
    } catch (const std::exception& e) {
        std::cerr << "例外が発生しました: " << e.what() << std::endl;
    }
    
    return 0;
}
```

## Python版との比較

### Python版（asyncio）
```python
import asyncio
from WIPClientPy import ClientAsync

async def main():
    client = ClientAsync(35.6762, 139.6503, 130010, "localhost", 8080, "localhost", 8081, "localhost", 8082)
    
    # 複数の非同期タスク
    tasks = [
        client.get_weather_by_area_code_async(130010),
        client.get_weather_by_area_code_async(140010),
        client.get_weather_by_area_code_async(270000)
    ]
    
    results = await asyncio.gather(*tasks)
    
    for weather in results:
        print(f"Temperature: {weather.temperature}°C")

asyncio.run(main())
```

### C++版（std::future）
```cpp
#include "wiplib/client/client_async.hpp"

int main() {
    wiplib::client::ClientAsync client(35.6762, 139.6503, 130010, "localhost", 8080, "localhost", 8081, "localhost", 8082);
    
    // 複数の非同期タスク
    std::vector<std::future<std::optional<WeatherData>>> tasks = {
        client.get_weather_by_area_code_async(130010),
        client.get_weather_by_area_code_async(140010), 
        client.get_weather_by_area_code_async(270000)
    };
    
    // 結果を取得
    for (auto& task : tasks) {
        auto weather = task.get();
        if (weather.has_value()) {
            std::cout << "Temperature: " << weather->temperature << "°C" << std::endl;
        }
    }
    
    return 0;
}
```

C++版では `std::future` を使用してPython版の `asyncio` と同等の非同期処理を実現します。