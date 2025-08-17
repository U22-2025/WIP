# WIPLib C++ チュートリアル

## はじめに

WIPLib C++は、Python版WIPCommonPy/WIPClientPyと完全に互換性のある天気情報プロトコルライブラリです。このチュートリアルでは、基本的な使用方法から高度な機能まで段階的に学習します。

## 目次

1. [環境設定](#環境設定)
2. [基本的な使用方法](#基本的な使用方法)
3. [非同期処理](#非同期処理)
4. [エラーハンドリング](#エラーハンドリング)
5. [設定管理](#設定管理)
6. [高度な機能](#高度な機能)
7. [Python版からの移行](#python版からの移行)

## 環境設定

### 必要な環境

- C++20対応コンパイラ (GCC 10+, Clang 10+, MSVC 2019+)
- CMake 3.20以上
- 対応OS: Windows, Linux, macOS

### ビルドとインストール

```bash
# リポジトリをクローン
git clone <repository-url>
cd WIP/cpp

# ビルド
mkdir build
cd build
cmake ..
cmake --build .

# テスト実行（オプション）
ctest
```

### プロジェクトへの組み込み

#### CMakeを使用する場合

```cmake
# CMakeLists.txt
find_package(wiplib REQUIRED)

add_executable(my_app main.cpp)
target_link_libraries(my_app wiplib::wiplib)
```

#### 手動リンクの場合

```bash
g++ -std=c++20 -I/path/to/wiplib/include main.cpp -lwiplib -o my_app
```

## 基本的な使用方法

### 1. 最初のプログラム

```cpp
#include <iostream>
#include "wiplib/client/client.hpp"

int main() {
    // クライアントを作成（Python版と同じ引数順序）
    wiplib::client::Client client(
        35.6762,      // latitude (東京)
        139.6503,     // longitude
        130010,       // area_code
        "localhost",  // weather_host
        8080,         // weather_port
        "localhost",  // location_host
        8081,         // location_port
        "localhost",  // query_host
        8082          // query_port
    );
    
    // 天気データを取得
    auto weather = client.get_weather();
    if (weather.has_value()) {
        std::cout << "気温: " << weather->temperature << "°C" << std::endl;
        std::cout << "湿度: " << weather->humidity << "%" << std::endl;
    } else {
        std::cout << "天気データの取得に失敗しました" << std::endl;
    }
    
    return 0;
}
```

### 2. 座標による天気取得

```cpp
// 特定の座標で天気を取得
double osaka_lat = 34.6937;
double osaka_lon = 135.5023;

auto osaka_weather = client.get_weather_by_coordinates(osaka_lat, osaka_lon);
if (osaka_weather.has_value()) {
    std::cout << "大阪の気温: " << osaka_weather->temperature << "°C" << std::endl;
}
```

### 3. エリアコードによる天気取得

```cpp
// エリアコードで天気を取得
uint32_t yokohama_area = 140010;
auto yokohama_weather = client.get_weather_by_area_code(yokohama_area);
if (yokohama_weather.has_value()) {
    std::cout << "横浜の気温: " << yokohama_weather->temperature << "°C" << std::endl;
}
```

### 4. 座標の変更

```cpp
// クライアントの座標を変更
client.set_coordinates(43.0642, 141.3469); // 札幌

// 新しい座標で天気を取得
auto sapporo_weather = client.get_weather();
```

## 非同期処理

### 1. 基本的な非同期処理

```cpp
#include "wiplib/client/client_async.hpp"
#include <future>

int main() {
    wiplib::client::ClientAsync client(
        35.6762, 139.6503, 130010,
        "localhost", 8080, "localhost", 8081, "localhost", 8082
    );
    
    // 非同期で天気データを取得
    auto future = client.get_weather_async();
    
    // 他の処理を実行...
    std::cout << "天気データを取得中..." << std::endl;
    
    // 結果を取得
    auto weather = future.get();
    if (weather.has_value()) {
        std::cout << "気温: " << weather->temperature << "°C" << std::endl;
    }
    
    return 0;
}
```

### 2. 複数の同時リクエスト

```cpp
#include <vector>

// 複数都市の天気を同時取得
std::vector<uint32_t> area_codes = {130010, 140010, 270000};
std::vector<std::future<std::optional<WeatherData>>> futures;

// 非同期リクエストを開始
for (uint32_t area_code : area_codes) {
    futures.push_back(client.get_weather_by_area_code_async(area_code));
}

// 結果を取得
for (auto& future : futures) {
    auto weather = future.get();
    if (weather.has_value()) {
        std::cout << "気温: " << weather->temperature << "°C" << std::endl;
    }
}
```

### 3. タイムアウト付き処理

```cpp
#include <chrono>

// タイムアウトを設定
client.set_timeout(std::chrono::milliseconds(5000));

auto future = client.get_weather_async();

// タイムアウト付きで結果を待機
auto status = future.wait_for(std::chrono::seconds(10));

if (status == std::future_status::ready) {
    auto weather = future.get();
    // 処理成功
} else if (status == std::future_status::timeout) {
    std::cout << "タイムアウトしました" << std::endl;
}
```

## エラーハンドリング

### 1. 基本的なエラーハンドリング

```cpp
auto weather = client.get_weather();
if (!weather.has_value()) {
    // エラー情報を取得
    auto error = client.get_last_error();
    if (error.has_value()) {
        std::cout << "エラーコード: " << error->code << std::endl;
        std::cout << "エラーメッセージ: " << error->message << std::endl;
    }
}
```

### 2. 例外処理

```cpp
try {
    auto weather = client.get_weather();
    // 正常処理
} catch (const std::exception& e) {
    std::cerr << "例外が発生しました: " << e.what() << std::endl;
}
```

### 3. 非同期エラーハンドリング

```cpp
try {
    auto future = client.get_weather_async();
    auto weather = future.get();
    
    if (!weather.has_value()) {
        auto error = client.get_last_error();
        // エラー処理
    }
} catch (const std::exception& e) {
    // 例外処理
}
```

## 設定管理

### 1. 設定ファイルの使用

```cpp
#include "wiplib/utils/config_loader.hpp"

wiplib::utils::ConfigLoader loader;
auto config = loader.load_config("config.json");

if (config.has_value()) {
    std::string host = config->get_string("server.host");
    int port = config->get_int("server.port");
    
    // 設定値を使用してクライアントを作成
}
```

### 2. 環境変数の使用

```json
// config.json
{
    "server": {
        "host": "${WEATHER_SERVER_HOST}",
        "port": "${WEATHER_SERVER_PORT}"
    }
}
```

### 3. キャッシュの有効化

```cpp
#include "wiplib/utils/cache.hpp"

// キャッシュを有効にする
client.enable_cache(std::chrono::minutes(10)); // 10分間キャッシュ

// ファイルキャッシュも利用可能
client.enable_file_cache("cache_directory", std::chrono::hours(24));
```

## 高度な機能

### 1. 認証機能

```cpp
#include "wiplib/utils/auth.hpp"

wiplib::utils::WIPAuth auth("your_passphrase");
if (auth.is_authenticated()) {
    std::string token = auth.get_token();
    // 認証トークンを使用
}
```

### 2. ログ設定

```cpp
#include "wiplib/utils/log_config.hpp"

wiplib::utils::UnifiedLogFormatter formatter;
std::string log_message = formatter.format("INFO", "Test message", "module");
std::cout << log_message << std::endl;
```

### 3. デバッグ機能

```cpp
// デバッグモードを有効にする
#ifdef WIPLIB_DEBUG
    client.enable_debug_logging(true);
#endif
```

### 4. カスタムパケット処理

```cpp
#include "wiplib/packet/codec.hpp"

// カスタムパケットの作成
wiplib::proto::Packet packet;
packet.header.version = 1;
packet.header.packet_id = 0x123;
packet.header.type = wiplib::proto::PacketType::WeatherRequest;

// パケットのエンコード
auto encoded = wiplib::proto::encode_packet(packet);
if (encoded.has_value()) {
    // エンコードされたデータを使用
}
```

## Python版からの移行

### 移行の容易さ

WIPLib C++は、Python版との100%API互換性を目標としているため、移行は非常に簡単です。

### Python版コード

```python
from WIPClientPy import Client

client = Client(35.6762, 139.6503, 130010, "localhost", 8080, "localhost", 8081, "localhost", 8082)
weather = client.get_weather()
print(f"Temperature: {weather.temperature}°C")
```

### C++版コード

```cpp
#include "wiplib/client/client.hpp"

wiplib::client::Client client(35.6762, 139.6503, 130010, "localhost", 8080, "localhost", 8081, "localhost", 8082);
auto weather = client.get_weather();
if (weather.has_value()) {
    std::cout << "Temperature: " << weather->temperature << "°C" << std::endl;
}
```

### 主な相違点

1. **エラーハンドリング**: C++では`std::optional`を使用
2. **非同期処理**: Python の `asyncio` → C++ の `std::future`
3. **例外処理**: より厳密な型チェック

### 移行チェックリスト

- [ ] ヘッダーファイルのインクルード
- [ ] 名前空間の指定 (`wiplib::client::`)
- [ ] `std::optional` を使用したエラーハンドリング
- [ ] 非同期処理の `std::future` への変更
- [ ] CMake または Makefile の設定

## トラブルシューティング

### よくある問題

#### 1. コンパイルエラー

```bash
# C++20サポートの確認
g++ --version

# 適切なフラグの設定
g++ -std=c++20 -I/path/to/include main.cpp -lwiplib
```

#### 2. リンクエラー

```bash
# ライブラリパスの確認
export LD_LIBRARY_PATH=/path/to/wiplib/lib:$LD_LIBRARY_PATH

# 依存関係の確認
ldd my_app
```

#### 3. 実行時エラー

```cpp
// サーバー接続の確認
auto state = client.get_state();
std::cout << "Server: " << state.weather_host << ":" << state.weather_port << std::endl;

// エラー詳細の確認
auto error = client.get_last_error();
if (error.has_value()) {
    std::cout << "Error: " << error->message << std::endl;
}
```

## パフォーマンスの最適化

### 1. 非同期処理の活用

```cpp
// 複数リクエストを並行処理
std::vector<std::future<std::optional<WeatherData>>> futures;
for (int i = 0; i < 10; ++i) {
    futures.push_back(client.get_weather_async());
}
```

### 2. キャッシュの活用

```cpp
// 頻繁にアクセスするデータをキャッシュ
client.enable_cache(std::chrono::minutes(5));
```

### 3. コンパイル最適化

```bash
# リリースビルドでの最適化
g++ -std=c++20 -O3 -DNDEBUG main.cpp -lwiplib
```

## 次のステップ

1. **実際のプロジェクトへの統合**: 既存プロジェクトにWIPLib C++を組み込む
2. **カスタマイズ**: プロジェクト固有の要件に合わせて拡張
3. **監視とログ**: 本番環境での監視機能を追加
4. **テスト**: 包括的なテストスイートの作成

## 参考資料

- [API リファレンス](api_reference/)
- [使用例](examples/)
- [FAQ](faq.md)
- [GitHub Issues](https://github.com/project/issues)

このチュートリアルを通じて、WIPLib C++の基本的な使用方法から高度な機能まで学習できます。疑問や問題があれば、APIドキュメントやサンプルコードを参照してください。