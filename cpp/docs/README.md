# WIPLib C++ API Documentation

Weather Information Protocol Library for C++ - Python互換性実現

## 概要

WIPLib C++は、Python版WIPCommonPy/WIPClientPyと完全に同等の機能をC++で実装した天気情報プロトコルライブラリです。

## 主な機能

### クライアント機能
- **Client**: Python互換の統合クライアント
- **ClientAsync**: Python互換の非同期クライアント  
- **WeatherClient**: 天気データ取得専用クライアント
- **AsyncWeatherClient**: 非同期天気データ取得クライアント
- **LocationClient**: 座標→エリアコード変換クライアント
- **QueryClient**: 直接データベースクエリクライアント

### パケット処理
- **Header**: WIPプロトコルヘッダー
- **Packet**: 汎用パケット構造
- **ExtendedField**: 拡張フィールド処理
- **Codec**: パケットエンコード/デコード

### ユーティリティ
- **Auth**: 認証機能
- **Cache**: インメモリキャッシュ
- **FileCache**: ファイルシステムキャッシュ
- **ConfigLoader**: 設定ファイル読み込み
- **LogConfig**: 統一ログフォーマット

## クイックスタート

### 基本的な使用方法

```cpp
#include "wiplib/client/client.hpp"

// Python互換クライアントの作成
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

// 天気データの取得
auto weather_data = client.get_weather();
if (weather_data.has_value()) {
    std::cout << "Temperature: " << weather_data->temperature << "°C" << std::endl;
    std::cout << "Humidity: " << weather_data->humidity << "%" << std::endl;
}
```

### 非同期クライアントの使用

```cpp
#include "wiplib/client/client_async.hpp"

wiplib::client::ClientAsync async_client(
    35.6762, 139.6503, 130010,
    "localhost", 8080,
    "localhost", 8081, 
    "localhost", 8082
);

// 非同期で天気データを取得
auto future = async_client.get_weather_async();
auto weather_data = future.get();
```

## API リファレンス

詳細なAPI リファレンスは、Doxygenで生成されたドキュメントを参照してください：

```bash
cd docs
doxygen Doxyfile
```

生成されたHTMLドキュメントは `docs/output/html/index.html` で閲覧できます。

## ビルド方法

### 要件
- C++20対応コンパイラ (GCC 10+, Clang 10+, MSVC 2019+)
- CMake 3.20以上
- Google Test (テスト実行時)

### ビルド手順

```bash
mkdir build
cd build
cmake ..
cmake --build .
```

### テストの実行

```bash
# 単体テスト・統合テストの実行
ctest

# Google Testベースのテスト実行
./wiplib_gtest
```

## Python互換性

WIPLib C++は、Python版との100%互換性を目標として設計されています：

### 互換性機能
- **同一のAPI**: Python版と同じメソッド名・引数順序
- **同一のエラー処理**: 日本語エラーメッセージ対応
- **同一の通信プロトコル**: パケットフォーマット完全互換
- **同一の設定形式**: JSON設定ファイル互換

### 移行ガイド

Python版からC++版への移行は非常に簡単です：

**Python版:**
```python
from WIPClientPy import Client

client = Client(35.6762, 139.6503, 130010, "localhost", 8080, "localhost", 8081, "localhost", 8082)
weather = client.get_weather()
```

**C++版:**
```cpp
#include "wiplib/client/client.hpp"

wiplib::client::Client client(35.6762, 139.6503, 130010, "localhost", 8080, "localhost", 8081, "localhost", 8082);
auto weather = client.get_weather();
```

## パフォーマンス

C++版は、Python版と比較して以下の優位性があります：

- **メモリ効率**: 最適化されたメモリ管理
- **処理速度**: ネイティブコードによる高速処理  
- **並行性**: std::futureによる効率的な非同期処理
- **リソース使用量**: 最小限のシステムリソース使用

## 例

### 詳細な使用例

より詳細な使用例については、以下を参照してください：

- [基本的な使用例](examples/basic_usage.cpp)
- [非同期処理の例](examples/async_usage.cpp)  
- [エラーハンドリングの例](examples/error_handling.cpp)
- [設定ファイルの例](examples/config_usage.cpp)

## トラブルシューティング

### よくある問題

1. **コンパイルエラー**
   - C++20サポートの確認
   - 適切なincludeパスの設定

2. **リンクエラー**
   - ライブラリの依存関係確認
   - プラットフォーム固有の設定

3. **実行時エラー**  
   - サーバー接続の確認
   - 設定ファイルの検証

### デバッグ

デバッグビルドでは詳細なログ出力が利用できます：

```cpp
#ifdef WIPLIB_DEBUG
    // デバッグ情報が自動的に出力されます
#endif
```

## ライセンス

このライブラリは、元のWIPClientPyと同じライセンス条件で提供されます。

## コントリビューション

バグレポートや機能要望は、プロジェクトのIssue Trackerで受け付けています。

## 更新履歴

### v1.0.0 (2024-08-17)
- 初回リリース
- Python版との完全互換性実現
- 包括的テストスイート追加
- 完全なドキュメント作成