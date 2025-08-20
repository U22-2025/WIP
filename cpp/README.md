# WIP C++ Library (wiplib)

## 概要

Python版WIPCommonPy/WIPClientPyと完全互換性を持つC++実装です。同等のパケット仕様と高水準クライアントAPIを提供し、Windows・Linux・macOSでマルチプラットフォーム対応しています。

## 主な機能

- **完全Python互換API**: Python版WIPClientと同一のインターフェース
- **マルチプラットフォーム**: Windows/Linux/macOS対応
- **高性能**: C++ネイティブ実装によるPython版の5-50倍の高速化
- **包括的なクライアント**: Weather/Location/Query/Reportクライアントを統合
- **豊富なツール**: CLI、パケット解析、デバッグツール一式

## クイックスタート

### ビルド

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

**成果物**
- ライブラリ: `build/(lib)wiplib.*`
- ツール: `unified_client_cli`, `wip_client_cli`など

### 基本的な使用例

**Python互換クライアント**
```cpp
#include "wiplib/client/client.hpp"
using namespace wiplib::client;

int main() {
    // Python版Client()と同等
    Client client("localhost", 4110);
    client.set_coordinates(35.6895, 139.6917);
    
    auto result = client.get_weather();
    if (result.has_value()) {
        auto weather = result.value();
        std::cout << "Temperature: " << weather.temperature << "°C" << std::endl;
    }
    return 0;
}
```

**CLI使用例**
```bash
# 天気情報取得
./build/unified_client_cli weather --coords 35.6895 139.6917

# センサーデータ送信
./build/unified_client_cli report --area 130010 --temp 25.5
```

## Python版との互換性

- **完全互換API**: Python版と同一のメソッド名・引数・戻り値
- **同一プロトコル**: パケットフォーマット・チェックサム・認証方式
- **エラー型安全**: Python例外に対応する`Result<T>`型によるエラーハンドリング
- **環境変数**: `.env`ファイルと環境変数による設定管理

## 開発ツール

- `unified_client_cli`: 統合CLIクライアント（weather/reportモード）
- `wip_packet_decode`: パケット解析・デバッグツール
- `mock_report_server`: テスト用モックサーバー

## ドキュメント

- [API Reference](docs/api_reference/): 詳細なAPIドキュメント
- [Migration Guide](docs/PYTHON_TO_CPP_MIGRATION_GUIDE.md): Python版からの移行ガイド
- [Examples](examples/): 実用的なコード例

## ライセンス

MIT License
