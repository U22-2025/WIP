# WIP Rust Implementation

Weather Information Protocol (WIP) クライアントライブラリのRust実装です。Python版と完全なプロトコル互換性を持ちながら、Rustの安全性と性能を活用します。

## 主な機能

- **完全Python互換プロトコル**: Python版と同一のパケット仕様・通信方式
- **高性能**: Python版の5-10倍高速なパケット処理
- **メモリ安全**: Rustの所有権システムによる安全なメモリ管理
- **非同期処理**: tokioベースの高効率並行処理
- **型安全**: コンパイル時エラー検出による堅牢性
- **全パケットタイプ対応**: Weather/Location/Query/Report/Error packets

## ビルドとインストール

**必要環境:**
- Rust 1.70+
- Cargo

**ビルド手順:**
```bash
# ライブラリとCLIツールをビルド
cargo build --release

# すべてのバイナリをビルド
cargo build --release --bins

# テスト実行
cargo test

# CLI ツール実行
cargo run --bin wip-weather get 130010 --weather --temperature
cargo run --bin wip-location resolve 35.6895 139.6917
cargo run --bin wip-cli weather get 130010 --weather
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

**Rust版:**
```rust
use wip_rust::prelude::*;

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let client = WeatherClient::new("localhost", 4110, true)?;
    
    // 座標から天気データを取得
    if let Some(weather_data) = client.get_weather_by_coordinates(
        35.6895, 139.6917, // 緯度, 経度
        true, true, true, false, false, 0 // weather, temperature, precipitation, alerts, disaster, day
    )? {
        if let Some(temp) = weather_data.temperature {
            println!("Temperature: {}°C", temp);
        }
    }
    Ok(())
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

**Rust版:**
```rust
use wip_rust::prelude::*;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let client = LocationClient::new("localhost", 4109, true).await?;
    
    if let Some(area_code) = client.get_area_code(35.6895, 139.6917).await? {
        println!("Area code: {}", area_code);
    }
    Ok(())
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

**Rust版:**
```rust
use wip_rust::prelude::*;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let client = QueryClient::new("localhost", 4111, true).await?;
    
    if let Some(response) = client.get_weather_data(
        130010, // area_code
        true, true, true, false, false, // weather, temp, precipitation, alerts, disaster
        0 // day
    ).await? {
        if let Some(weather) = response.weather_code {
            println!("Weather: {}", weather);
        }
        if let Some(temp) = response.temperature {
            println!("Temperature: {}°C", temp);
        }
    }
    Ok(())
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

**Rust版:**
```rust
use wip_rust::prelude::*;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let client = ReportClient::new("localhost", 4112, true).await?;
    
    let mut request = ReportRequest::new();
    request.set_area_code(130010);
    request.set_weather_code(Some(100));
    request.set_temperature(Some(25.5));
    request.set_precipitation_prob(Some(30));
    request.add_alert("大雨警報".to_string());
    request.add_disaster("地震情報".to_string());
    
    if let Some(response) = client.send_report(request).await? {
        println!("Success: {}", response.success);
    }
    Ok(())
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

**Rust版:**
```rust
use wip_rust::prelude::*;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let mut client = WipClient::new(
        "localhost", 4110, // weather server
        4109,              // location server
        4111,              // query server
        4112,              // report server
        true               // debug
    ).await?;
    
    client.set_coordinates(35.6895, 139.6917);
    client.set_area_code(130010);
    
    if let Some(weather) = client.get_weather(
        true, true, true, false, false, // weather, temp, precipitation, alerts, disaster
        0 // day
    ).await? {
        if let Some(temp) = weather.temperature {
            println!("Temperature: {}°C", temp);
        }
    }
    Ok(())
}
```

### 6. エラーハンドリングの違い

**Python版 (例外処理):**
```python
try:
    weather = client.get_weather()
    process_weather(weather)
except NetworkError as e:
    print(f"Network error: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

**Rust版 (Result型):**
```rust
use wip_rust::prelude::*;

match client.get_weather(true, true, true, false, false, 0).await {
    Ok(Some(weather)) => {
        // 成功時の処理
        if let Some(temp) = weather.temperature {
            println!("Temperature: {}°C", temp);
        }
    }
    Ok(None) => {
        println!("No weather data received");
    }
    Err(e) => {
        println!("Error: {}", e);
    }
}

// または ? オペレーターを使用
let weather = client.get_weather(true, true, true, false, false, 0).await?;
```

## CLI完全使用ガイド

### 統合CLIツール (wip-cli)

**気象データ取得**
```bash
# 基本的な天気データ取得
cargo run --bin wip-cli weather get 130010 --weather --temperature --precipitation

# 座標指定での天気取得
cargo run --bin wip-cli weather coords 35.6895 139.6917 --weather --temperature

# 未来の天気取得（day=0-7）
cargo run --bin wip-cli weather get 130010 --weather --temperature --day 3

# カスタムサーバー指定
cargo run --bin wip-cli weather get 130010 --host 192.168.1.100 --port 4110 --weather
```

**座標・エリアコード変換**
```bash
# 座標からエリアコード取得
cargo run --bin wip-location resolve 35.6895 139.6917

# エリアコードから座標取得
cargo run --bin wip-location coords 130010

# カスタムLocationサーバー指定
cargo run --bin wip-location resolve 35.6895 139.6917 --host localhost --port 4109
```

**データベースクエリ**
```bash
# 直接データベースクエリ
cargo run --bin wip-query get 130010 --weather --temperature --precipitation

# 警報・災害情報取得
cargo run --bin wip-query get 130010 --alerts --disaster

# カスタムQueryサーバー指定
cargo run --bin wip-query get 130010 --host localhost --port 4111 --weather
```

**センサーデータレポート**
```bash
# 基本的なセンサーデータ送信
cargo run --bin wip-report send 130010 --temperature 25.5

# 包括的なレポート送信
cargo run --bin wip-report send 130010 --weather-code 200 --temperature 18.2 --precipitation 60

# 警報・災害情報付きレポート
cargo run --bin wip-report send 130010 --temperature 30.1 --alert "大雨警報" --disaster "地震情報"

# カスタムReportサーバー指定
cargo run --bin wip-report send 130010 --host localhost --port 4112 --temperature 22.0
```

### 個別CLIツール

**wip-weather (天気データ専用)**
```bash
# 天気データ取得
cargo run --bin wip-weather get 130010 --weather --temperature --precipitation

# プロキシ経由での天気取得
cargo run --bin wip-weather proxy 35.6895 139.6917 --weather --temperature

# 認証付きでの天気取得
cargo run --bin wip-weather get 130010 --auth-token "your_token" --weather
```

**wip-location (座標・エリアコード専用)**
```bash
# 座標→エリアコード変換
cargo run --bin wip-location resolve 35.6895 139.6917

# エリアコード→座標変換
cargo run --bin wip-location coords 130010

# デバッグモード
cargo run --bin wip-location resolve 35.6895 139.6917 --debug
```

**wip-query (データベースクエリ専用)**
```bash
# 包括的なデータ取得
cargo run --bin wip-query get 130010 --weather --temperature --precipitation --alerts --disaster

# 特定の日のデータ
cargo run --bin wip-query get 130010 --weather --day 5
```

**wip-report (レポート送信専用)**
```bash
# 温度レポート
cargo run --bin wip-report send 130010 --temperature 25.5

# 包括的なセンサーレポート
cargo run --bin wip-report send 130010 --weather-code 100 --temperature 22.0 --precipitation 45

# 複数警報レポート
cargo run --bin wip-report send 130010 --alert "大雨警報" --alert "洪水注意報" --disaster "地震情報"
```

**wip-auth (認証管理専用)**
```bash
# 認証トークン生成
cargo run --bin wip-auth generate --service weather

# 認証トークン検証
cargo run --bin wip-auth verify --token "your_token"

# 認証設定表示
cargo run --bin wip-auth status
```

### 高度な使用例

**バッチ処理**
```bash
# 複数エリアの天気データ一括取得
for area in 130010 140010 270000; do
  cargo run --bin wip-cli weather get $area --weather --temperature
done

# 認証環境変数設定
export WIP_AUTH_TOKEN="your_global_token"
cargo run --bin wip-cli weather get 130010 --weather
```

**設定ファイル使用**
```bash
# 設定ファイル指定
cargo run --bin wip-cli --config config.toml weather get 130010 --weather

# 環境変数オーバーライド
WIP_HOST=production.server.com cargo run --bin wip-cli weather get 130010 --weather
```

## 全パケットタイプ対応

### 対応パケット一覧
- **LocationRequest/Response**: GPS座標↔エリアコード変換
- **QueryRequest/Response**: 気象データベース直接アクセス  
- **ReportRequest/Response**: IoTセンサーデータ・警報情報送信
- **ErrorResponse**: エラーハンドリングとデバッグ情報
- **ExtendedField**: 拡張データ（警報・災害・座標・タイムスタンプ）

### パケット機能詳細
```rust
use wip_rust::prelude::*;

// Location packet example
let mut location_req = LocationRequest::new();
location_req.set_coordinates(35.6895, 139.6917);

// Query packet example  
let mut query_req = QueryRequest::new();
query_req.set_area_code(130010);
query_req.set_weather_flag(true);
query_req.set_temperature_flag(true);
query_req.set_day(0);

// Report packet example
let mut report_req = ReportRequest::new();
report_req.set_area_code(130010);
report_req.set_weather_code(Some(100));
report_req.set_temperature(Some(25.5));
report_req.add_alert("大雨警報".to_string());
report_req.add_disaster("地震情報".to_string());
```

## 認証・セキュリティ

**環境変数による認証:**
```bash
export WIP_AUTH_ENABLED=true
export WIP_AUTH_TOKEN="your_global_token"
export WIP_AUTH_WEATHER="weather_specific_token"
export WIP_AUTH_LOCATION="location_specific_token"
export WIP_AUTH_QUERY="query_specific_token"  
export WIP_AUTH_REPORT="report_specific_token"
```

**プログラム内認証:**
```rust
use wip_rust::prelude::*;

// 認証設定は環境変数で管理
std::env::set_var("WIP_AUTH_ENABLED", "true");
std::env::set_var("WIP_AUTH_TOKEN", "your_token");

let client = WeatherClient::new("localhost", 4110, true)?;
```

## 性能特徴

**期待される性能向上:**
- パケット処理速度: Python版の5-10倍
- メモリ使用量: Python版の1/3-1/5
- 並行処理能力: GIL制約なしの真の並列処理
- 起動時間: Python版の1/10以下

## 開発・デバッグ

**詳細ログ出力:**
```bash
# 環境変数でログレベル設定
RUST_LOG=debug cargo run --bin wip weather get 130010 --weather

# トレース レベルログ
RUST_LOG=trace cargo run --bin wip-weather get 130010 --weather --debug
```

**パケット解析:**
```rust
use wip_rust::prelude::*;

// パケットの手動生成・解析
let mut req = QueryRequest::new();
req.set_area_code(130010);
req.set_weather_flag(true);
req.set_temperature_flag(true);

let bytes = req.to_bytes()?;
println!("Encoded packet: {:?}", bytes);

let decoded = QueryRequest::from_bytes(&bytes)?;
println!("Decoded area code: {}", decoded.get_area_code());
```

## ライセンス

MIT License - Python版WIPと同一ライセンス