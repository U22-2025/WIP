# Python版ReportClient → C++版SimpleReportClient 移植ガイド

## 📋 概要

このガイドでは、Python版`ReportClient`からC++版`SimpleReportClient`への移植方法を詳しく説明します。C++版は**Python版と完全互換**のAPIを提供しており、最小限の変更で移植が可能です。

## 🔄 基本的な対応関係

### クラス名の対応

| Python版 | C++版 |
|----------|--------|
| `ReportClient` | `wiplib::client::SimpleReportClient` |

### ヘッダーファイルのインクルード

```cpp
// C++版で必要なインクルード
#include "wiplib/client/simple_report_client.hpp"
```

## 📚 API変換表

### 1. コンストラクタ

**Python版:**
```python
from report_client import ReportClient

client = ReportClient("127.0.0.1", 4110, debug=True)
```

**C++版:**
```cpp
#include "wiplib/client/simple_report_client.hpp"

wiplib::client::SimpleReportClient client("127.0.0.1", 4110, true);
```

### 2. データ設定メソッド

#### 一括設定 (`set_sensor_data`)

**Python版:**
```python
client.set_sensor_data(
    "123456",
    weather_code=1,
    temperature=25.5,
    precipitation_prob=30,
    alert=["地震", "津波"],
    disaster=["台風", "洪水"]
)
```

**C++版:**
```cpp
client.set_sensor_data(
    "123456",
    1,                                      // weather_code
    25.5f,                                  // temperature
    30,                                     // precipitation_prob
    std::vector<std::string>{"地震", "津波"}, // alert
    std::vector<std::string>{"台風", "洪水"}  // disaster
);
```

#### 個別設定メソッド

| Python版 | C++版 |
|----------|--------|
| `client.set_area_code("123456")` | `client.set_area_code("123456");` |
| `client.set_weather_code(1)` | `client.set_weather_code(1);` |
| `client.set_temperature(25.5)` | `client.set_temperature(25.5f);` |
| `client.set_precipitation_prob(30)` | `client.set_precipitation_prob(30);` |
| `client.set_alert(["大雨", "雷"])` | `client.set_alert({"大雨", "雷"});` |
| `client.set_disaster(["竜巻"])` | `client.set_disaster({"竜巻"});` |

### 3. データ送信メソッド

#### 同期送信

**Python版:**
```python
result = client.send_report_data()
if result['success']:
    print(f"送信成功: {result}")
else:
    print(f"送信失敗: {result}")
```

**C++版:**
```cpp
auto result = client.send_report_data();
if (result.has_value() && result.value().success) {
    std::cout << "送信成功: " << result.value().type << std::endl;
} else {
    std::cout << "送信失敗" << std::endl;
}
```

#### 非同期送信

**Python版:**
```python
import asyncio

async def async_send():
    result = await client.send_report_data_async()
    return result

result = asyncio.run(async_send())
```

**C++版:**
```cpp
auto future_result = client.send_report_data_async();
auto result = future_result.get();  // 結果を待機
```

### 4. データ管理メソッド

#### 現在のデータ取得

**Python版:**
```python
current_data = client.get_current_data()
print(f"エリアコード: {current_data.get('area_code')}")
print(f"天気コード: {current_data.get('weather_code')}")
```

**C++版:**
```cpp
auto current_data = client.get_current_data();
if (current_data.count("area_code")) {
    auto area_code = std::any_cast<std::string>(current_data["area_code"]);
    std::cout << "エリアコード: " << area_code << std::endl;
}
if (current_data.count("weather_code")) {
    auto weather_code = std::any_cast<int>(current_data["weather_code"]);
    std::cout << "天気コード: " << weather_code << std::endl;
}
```

#### データクリア

| Python版 | C++版 |
|----------|--------|
| `client.clear_data()` | `client.clear_data();` |
| `client.close()` | `client.close();` |

### 5. 後方互換性メソッド

| Python版 | C++版 |
|----------|--------|
| `client.send_report()` | `client.send_report();` |
| `client.send_current_data()` | `client.send_current_data();` |
| `client.send_data_simple()` | `client.send_data_simple();` |

### 6. 便利関数

#### 一括送信関数

**Python版:**
```python
from report_client import send_sensor_report

result = send_sensor_report(
    "123456",
    weather_code=1,
    temperature=25.5,
    precipitation_prob=30,
    host="127.0.0.1",
    port=4110,
    debug=True
)
```

**C++版:**
```cpp
#include "wiplib/client/simple_report_client.hpp"

auto result = wiplib::client::utils::send_sensor_report(
    "123456",
    1,              // weather_code
    25.5f,          // temperature
    30,             // precipitation_prob
    {},             // alert (空)
    {},             // disaster (空)
    "127.0.0.1",
    4110,
    true            // debug
);
```

## 🔧 主な型変換

### 基本型

| Python版 | C++版 |
|----------|--------|
| `str` | `std::string` |
| `int` | `int` |
| `float` | `float` (注: `f`サフィックス必要) |
| `bool` | `bool` |
| `List[str]` | `std::vector<std::string>` |
| `Optional[int]` | `std::optional<int>` |

### オプション値の扱い

**Python版:**
```python
# None を使用
client.set_sensor_data("123456", weather_code=None)
```

**C++版:**
```cpp
// std::optional の空値を使用
client.set_sensor_data("123456", {});  // {} は空のoptional
```

### リスト初期化

**Python版:**
```python
alert_list = ["地震", "津波"]
client.set_alert(alert_list)
```

**C++版:**
```cpp
std::vector<std::string> alert_list = {"地震", "津波"};
client.set_alert(alert_list);

// または直接初期化
client.set_alert({"地震", "津波"});
```

## 🌍 環境変数の使用

Python版と同じ環境変数がサポートされています：

| 環境変数名 | 用途 | 例 |
|-----------|------|-----|
| `REPORT_SERVER_HOST` | サーバーホスト | `"192.168.1.100"` |
| `REPORT_SERVER_PORT` | サーバーポート | `"4110"` |
| `REPORT_SERVER_REQUEST_AUTH_ENABLED` | 認証有効化 | `"true"` |
| `REPORT_SERVER_PASSPHRASE` | 認証パスフレーズ | `"secret123"` |

**使用例（Python版と同等）:**
```cpp
// 環境変数が設定されている場合、自動的に使用される
wiplib::client::SimpleReportClient client("localhost", 4110, true);
```

## ⚠️ エラーハンドリングの変更

### Python版のエラーハンドリング

```python
try:
    result = client.send_report_data()
    if result['success']:
        print("成功")
    else:
        print(f"失敗: {result.get('error_code', 'Unknown')}")
except Exception as e:
    print(f"例外: {e}")
```

### C++版のエラーハンドリング

```cpp
try {
    auto result = client.send_report_data();
    if (result.has_value()) {
        if (result.value().success) {
            std::cout << "成功" << std::endl;
        } else {
            std::cout << "失敗: " << result.value().type << std::endl;
        }
    } else {
        // エラーコードを取得
        auto error_code = static_cast<int>(result.error());
        std::cout << "エラー: " << error_code << std::endl;
    }
} catch (const std::exception& e) {
    std::cout << "例外: " << e.what() << std::endl;
}
```

## 📦 パッケージ管理

### Python版
```python
# requirements.txt または setup.py
report-client==1.0.0
```

### C++版
```cmake
# CMakeLists.txt
find_package(wiplib REQUIRED)
target_link_libraries(your_target PRIVATE wiplib)
```

## 🔄 移植手順

### ステップ1: ヘッダーファイルの変更

**Before (Python版):**
```python
from report_client import ReportClient, send_sensor_report
```

**After (C++版):**
```cpp
#include "wiplib/client/simple_report_client.hpp"
using namespace wiplib::client;
```

### ステップ2: インスタンス作成の変更

**Before:**
```python
client = ReportClient("127.0.0.1", 4110, debug=True)
```

**After:**
```cpp
SimpleReportClient client("127.0.0.1", 4110, true);
```

### ステップ3: メソッド呼び出しの変更

**Before:**
```python
client.set_sensor_data("123456", weather_code=1, temperature=25.5)
result = client.send_report_data()
```

**After:**
```cpp
client.set_sensor_data("123456", 1, 25.5f);
auto result = client.send_report_data();
```

### ステップ4: エラーハンドリングの変更

**Before:**
```python
if result['success']:
    print("成功")
```

**After:**
```cpp
if (result.has_value() && result.value().success) {
    std::cout << "成功" << std::endl;
}
```

## 💡 移植のコツ

### 1. 型注意事項

- **float リテラル**: `25.5` → `25.5f`
- **文字列リテラル**: Python版と同じ
- **リスト初期化**: `["a", "b"]` → `{"a", "b"}`

### 2. メモリ管理

```cpp
// 自動変数（推奨）
SimpleReportClient client("127.0.0.1", 4110, true);

// または動的確保
auto client = std::make_unique<SimpleReportClient>("127.0.0.1", 4110, true);
```

### 3. RAII パターン

```cpp
// コンストラクタ・デストラクタで自動管理
{
    SimpleReportClient client("127.0.0.1", 4110, true);
    client.set_area_code("123456");
    auto result = client.send_report_data();
    // デストラクタで自動的にcloseが呼ばれる
}
```

## 🧪 テスト

### 単体テスト例

```cpp
#include <gtest/gtest.h>
#include "wiplib/client/simple_report_client.hpp"

TEST(SimpleReportClientTest, BasicUsage) {
    wiplib::client::SimpleReportClient client("127.0.0.1", 4110, true);
    client.set_area_code("123456");
    
    auto data = client.get_current_data();
    EXPECT_EQ(data.size(), 1);
    EXPECT_EQ(std::any_cast<std::string>(data["area_code"]), "123456");
}
```

## 🚀 パフォーマンス最適化

### 再利用パターン

```cpp
// クライアントインスタンスの再利用
SimpleReportClient client("127.0.0.1", 4110, true);

for (const auto& sensor_data : sensor_data_list) {
    client.clear_data();
    client.set_sensor_data(
        sensor_data.area_code,
        sensor_data.weather_code,
        sensor_data.temperature
    );
    auto result = client.send_report_data();
    // 結果処理...
}
```

## 📚 完全なサンプルコード

```cpp
#include <iostream>
#include "wiplib/client/simple_report_client.hpp"

int main() {
    try {
        // Python版と同等のクライアント作成
        wiplib::client::SimpleReportClient client("127.0.0.1", 4110, true);
        
        // Python版と同等のデータ設定
        client.set_sensor_data(
            "123456",                           // area_code
            1,                                  // weather_code
            25.5f,                             // temperature
            30,                                // precipitation_prob
            std::vector<std::string>{"地震"},    // alert
            std::vector<std::string>{"台風"}     // disaster
        );
        
        // Python版と同等の送信処理
        auto result = client.send_report_data();
        
        // Python版と同等の結果確認
        if (result.has_value() && result.value().success) {
            std::cout << "✅ 送信成功!" << std::endl;
            std::cout << "   レスポンス時間: " 
                      << result.value().response_time_ms << "ms" << std::endl;
        } else {
            std::cout << "❌ 送信失敗" << std::endl;
        }
        
        // Python版と同等のクリーンアップ
        client.close();
        
    } catch (const std::exception& e) {
        std::cout << "エラー: " << e.what() << std::endl;
        return 1;
    }
    
    return 0;
}
```

## 📋 チェックリスト

移植完了前に以下を確認してください：

- [ ] 必要なヘッダーファイルをインクルード
- [ ] クラス名を`ReportClient`から`SimpleReportClient`に変更
- [ ] 名前空間`wiplib::client`を使用
- [ ] float型リテラルに`f`サフィックスを追加
- [ ] エラーハンドリングを`Result<T>`型に対応
- [ ] メモリ管理（RAII）を活用
- [ ] 環境変数設定が正しく適用されることを確認
- [ ] テストコードを作成・実行

## 🔗 関連ドキュメント

- [SimpleReportClient API リファレンス](simple_report_client.hpp)
- [パケット形式ドキュメント](../include/wiplib/packet/report_packet_compat.hpp)
- [エラーコード一覧](../include/wiplib/error.hpp)
- [使用例とチュートリアル](../examples/simple_report_client_tutorial.cpp)

---

このガイドにより、Python版ReportClientからC++版SimpleReportClientへの移植を効率的に行うことができます。完全互換性により、既存のPython版ロジックをほぼそのままC++版に移植できます。