# WIP Rust - Command Reference Guide

このドキュメントでは、WIP Rust実装での各種リクエスト送信コマンド、認証機能、レポート通信の使用方法を詳しく説明します。

## 目次

1. [認証機能](#認証機能)
2. [天気データリクエスト](#天気データリクエスト)
3. [位置情報リクエスト](#位置情報リクエスト)
4. [クエリリクエスト](#クエリリクエスト)
5. [レポート通信](#レポート通信)
6. [実行可能ファイル](#実行可能ファイル)
7. [設定とカスタマイズ](#設定とカスタマイズ)

## 認証機能

WIP Rust実装では、SHA256ベースのトークン認証システムが実装されています。

### 基本的な認証

```rust
use wip_rust::wip_common_rs::utils::auth::{WIPAuth, SecurityPolicy};

// 認証システムの初期化
let mut auth = WIPAuth::new("your-secure-passphrase".to_string());

// セッションタイムアウトを設定（デフォルト：1時間）
let mut auth = WIPAuth::with_timeout("your-passphrase".to_string(), 7200); // 2時間

// 認証実行
match auth.authenticate("your-secure-passphrase") {
    Ok(token) => {
        println!("認証成功。トークン: {}", token);
        
        // トークンの検証
        if auth.validate_token(&token) {
            println!("トークンは有効です");
        }
        
        // 権限の確認
        if auth.has_permission(&token, "write") {
            println!("書き込み権限があります");
        }
    },
    Err(e) => println!("認証失敗: {}", e),
}

// セキュリティポリシーの設定
let policy = SecurityPolicy {
    min_passphrase_length: 12,
    require_special_chars: true,
    max_session_duration: 3600,
    max_concurrent_sessions: 10,
};

// パスフレーズの検証
match policy.validate_passphrase("MySecureP@ssw0rd!") {
    Ok(()) => println!("パスフレーズは安全です"),
    Err(e) => println!("パスフレーズエラー: {}", e),
}
```

### 認証付きクライアント使用例

```rust
use wip_rust::wip_common_rs::clients::weather_client::WeatherClient;
use wip_rust::wip_common_rs::utils::auth::WIPAuth;

async fn authenticated_weather_request() -> Result<(), Box<dyn std::error::Error>> {
    // 認証システム初期化
    let mut auth = WIPAuth::new("server-shared-secret".to_string());
    let token = auth.authenticate("server-shared-secret")?;
    
    // クライアント作成（認証トークン付き）
    let mut client = WeatherClient::new("127.0.0.1", 4110, true)?;
    client.set_auth_token(Some(token));
    
    // 認証付きリクエスト送信
    let result = client.get_weather_simple(11000, true, true, true, false, false, 0)?;
    
    if let Some(response) = result {
        println!("認証付き天気データ取得成功: {:?}", response);
    }
    
    Ok(())
}
```

## 天気データリクエスト

### 基本的な天気データ取得

```rust
use wip_rust::wip_common_rs::clients::weather_client::WeatherClient;

fn main() -> Result<(), Box<dyn std::error::Error>> {
    // WeatherClient作成
    let mut client = WeatherClient::new("127.0.0.1", 4110, true)?;
    
    // 基本的な天気データリクエスト
    let area_code = 11000; // 東京のエリアコード
    let result = client.get_weather_simple(
        area_code,
        true,  // weather（天気コード）
        true,  // temperature（気温）
        true,  // precipitation_prob（降水確率）
        false, // alerts（警報）
        false, // disaster（災害情報）
        0      // day（今日=0、明日=1）
    )?;
    
    match result {
        Some(response) => {
            println!("=== 天気データ ===");
            println!("エリアコード: {}", response.area_code);
            
            if let Some(weather_code) = response.weather_code {
                println!("天気コード: {}", weather_code);
            }
            
            if let Some(temperature) = response.temperature {
                println!("気温: {}°C", temperature);
            }
            
            if let Some(precipitation) = response.precipitation {
                println!("降水確率: {}%", precipitation);
            }
        },
        None => println!("レスポンスなし"),
    }
    
    Ok(())
}
```

### 詳細な天気データリクエスト

```rust
use wip_rust::wip_common_rs::clients::weather_client::WeatherClient;

fn detailed_weather_request() -> Result<(), Box<dyn std::error::Error>> {
    let mut client = WeatherClient::new("127.0.0.1", 4110, true)?;
    
    // 警報・災害情報付きリクエスト
    let result = client.get_weather_simple(
        11000, // 東京
        true,  // 天気
        true,  // 気温
        true,  // 降水確率
        true,  // 警報情報
        true,  // 災害情報
        0      // 今日
    )?;
    
    if let Some(response) = result {
        println!("=== 詳細天気データ ===");
        println!("パケットID: {}", response.packet_id);
        println!("バージョン: {}", response.version);
        
        // 警報情報チェック
        if response.alert_flag {
            println!("⚠️ 気象警報が発令されています");
        }
        
        // 災害情報チェック
        if response.disaster_flag {
            println!("🚨 災害情報があります");
        }
    }
    
    Ok(())
}
```

### 複数日の予報取得

```rust
fn multi_day_forecast() -> Result<(), Box<dyn std::error::Error>> {
    let mut client = WeatherClient::new("127.0.0.1", 4110, true)?;
    
    for day in 0..3 {
        let day_name = match day {
            0 => "今日",
            1 => "明日",
            2 => "明後日",
            _ => "その他",
        };
        
        let result = client.get_weather_simple(11000, true, true, true, false, false, day)?;
        
        if let Some(response) = result {
            println!("=== {} ===", day_name);
            if let Some(weather_code) = response.weather_code {
                let weather_desc = match weather_code {
                    100..=199 => "晴れ",
                    200..=299 => "曇り",
                    300..=399 => "雨",
                    400..=499 => "雪",
                    _ => "不明",
                };
                println!("天気: {} (コード: {})", weather_desc, weather_code);
            }
            
            if let Some(temp) = response.temperature {
                println!("気温: {}°C", temp);
            }
        }
    }
    
    Ok(())
}
```

## 位置情報リクエスト

### 座標からエリアコード取得

```rust
use wip_rust::wip_common_rs::clients::location_client::LocationClient;
use tokio;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    // LocationClient作成
    let location_client = LocationClient::new("127.0.0.1:4109".parse()?).await?;
    
    // 座標からエリアコード解決
    let tokyo_lat = 35.6812;
    let tokyo_lng = 139.7671;
    
    let area_code = location_client.resolve_coordinates(tokyo_lat, tokyo_lng).await?;
    println!("東京 ({:.4}, {:.4}) のエリアコード: {}", tokyo_lat, tokyo_lng, area_code);
    
    // 複数の場所を一括処理
    let locations = vec![
        (35.6812, 139.7671, "東京"),
        (34.6937, 135.5023, "大阪"),
        (43.0642, 141.3469, "札幌"),
        (33.5904, 130.4017, "福岡"),
    ];
    
    for (lat, lng, name) in locations {
        match location_client.resolve_coordinates(lat, lng).await {
            Ok(area_code) => {
                println!("{}: ({:.4}, {:.4}) -> エリアコード {}", name, lat, lng, area_code);
            },
            Err(e) => {
                println!("{}の座標解決エラー: {}", name, e);
            }
        }
    }
    
    Ok(())
}
```

### 座標付き天気リクエスト（LocationRequest使用）

```rust
use wip_rust::wip_common_rs::packet::types::location_packet::LocationRequest;

fn coordinate_weather_request() -> Result<(), Box<dyn std::error::Error>> {
    // 座標から天気データを取得するLocationRequest作成
    let request = LocationRequest::create_coordinate_lookup(
        35.6812,  // 緯度（東京）
        139.7671, // 経度
        1001,     // パケットID
        true,     // weather
        true,     // temperature
        true,     // precipitation
        false,    // alerts
        false,    // disaster
        0,        // today
        1         // version
    );
    
    // パケットをバイト列に変換
    let packet_bytes = request.to_bytes();
    println!("LocationRequestパケット生成: {} bytes", packet_bytes.len());
    
    // ここで実際にUDPでサーバーに送信
    // （実装は省略、UdpSocketを使用）
    
    Ok(())
}
```

### 位置情報クライアントの詳細設定

```rust
use wip_rust::wip_common_rs::clients::location_client::{LocationClientConfig, CoordinateBounds};
use std::time::Duration;

async fn configured_location_client() -> Result<(), Box<dyn std::error::Error>> {
    // カスタム設定
    let config = LocationClientConfig {
        timeout: Duration::from_secs(30),
        precision_digits: 4,
        bounds: CoordinateBounds::japan(), // 日本国内のみ
        enable_validation: true,
        cache_enabled: true,
        cache_ttl: Duration::from_hours(1),
    };
    
    let mut location_client = LocationClient::with_config("127.0.0.1:4109".parse()?, config).await?;
    
    // 日本国内の座標検証付きリクエスト
    let result = location_client.resolve_coordinates_validated(35.6812, 139.7671).await?;
    println!("検証済みエリアコード: {}", result);
    
    Ok(())
}
```

## クエリリクエスト

### 基本的なクエリリクエスト

```rust
use wip_rust::wip_common_rs::clients::query_client::QueryClient;
use wip_rust::wip_common_rs::packet::types::query_packet::QueryRequest;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    // QueryClient作成
    let query_client = QueryClient::new("127.0.0.1:4111".parse()?).await?;
    
    // エリアコードから天気データ要求
    let area_code = "011000"; // 東京のエリアコード
    let result = query_client.execute_query("status", &format!("region={}", area_code)).await?;
    
    println!("クエリ結果: {:?}", result);
    
    Ok(())
}
```

### 構造化クエリリクエスト

```rust
fn structured_query_request() -> Result<(), Box<dyn std::error::Error>> {
    // QueryRequest直接作成
    let query_request = QueryRequest::create_query_request(
        "011000", // エリアコード
        2001,     // パケットID
        true,     // weather
        true,     // temperature
        true,     // precipitation
        false,    // alerts
        false,    // disaster
        0,        // today
        1         // version
    );
    
    // パケット生成
    let packet_bytes = query_request.to_bytes();
    println!("QueryRequestパケット: {} bytes", packet_bytes.len());
    
    // 送信処理（実装は省略）
    
    Ok(())
}
```

### 様々なクエリタイプ

```rust
async fn various_queries() -> Result<(), Box<dyn std::error::Error>> {
    let query_client = QueryClient::new("127.0.0.1:4111".parse()?).await?;
    
    // システム状態クエリ
    let status = query_client.execute_query("status", "region=tokyo").await?;
    println!("システム状態: {:?}", status);
    
    // 気象警報クエリ
    let alerts = query_client.execute_query("alerts", "severity=high&region=kanto").await?;
    println!("気象警報: {:?}", alerts);
    
    // 履歴データクエリ
    let history = query_client.execute_query(
        "history", 
        "type=earthquake&from=2024-01-01&to=2024-12-31"
    ).await?;
    println!("履歴データ: {:?}", history);
    
    // 予報データクエリ
    let forecast = query_client.execute_query("forecast", "location=tokyo&period=7days").await?;
    println!("予報データ: {:?}", forecast);
    
    // 避難所情報クエリ
    let shelters = query_client.execute_query(
        "resources", 
        "type=shelter&location=tokyo&radius=5km"
    ).await?;
    println!("避難所情報: {:?}", shelters);
    
    Ok(())
}
```

## レポート通信

### 基本的なセンサーレポート送信

```rust
use wip_rust::wip_common_rs::clients::report_client::ReportClient;
use wip_rust::wip_common_rs::packet::types::report_packet::ReportRequest;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    // ReportClient作成
    let report_client = ReportClient::new("127.0.0.1:4112".parse()?).await?;
    
    // 基本的なセンサーデータレポート
    let report_id = report_client.send_sensor_report(
        "earthquake",                          // 災害タイプ
        7,                                     // 重要度（1-10）
        "強い地震を検知しました",                  // 説明
        Some(35.6812),                        // 緯度
        Some(139.7671)                        // 経度
    ).await?;
    
    println!("レポート送信成功 ID: {}", report_id);
    
    Ok(())
}
```

### 詳細なレポート送信

```rust
async fn detailed_sensor_report() -> Result<(), Box<dyn std::error::Error>> {
    let report_client = ReportClient::new("127.0.0.1:4112".parse()?).await?;
    
    // 構造化レポートリクエスト作成
    let report_request = ReportRequest::create_sensor_data_report(
        "011000",        // エリアコード
        Some(200),       // 天気コード（曇り）
        Some(25.5),      // 気温（25.5°C）
        Some(70),        // 降水確率（70%）
        Some(vec!["高温注意報".to_string()]), // 警報
        Some(vec!["河川氾濫注意".to_string()]), // 災害情報
        1,               // バージョン
        3001            // パケットID
    );
    
    // パケット送信
    let packet_bytes = report_request.to_bytes();
    println!("ReportRequestパケット: {} bytes", packet_bytes.len());
    
    // ここで実際の送信処理
    
    Ok(())
}
```

### バッチレポート送信

```rust
use wip_rust::wip_common_rs::clients::report_client::{ReportClientConfig, BatchConfig};
use std::time::Duration;

async fn batch_sensor_reports() -> Result<(), Box<dyn std::error::Error>> {
    // バッチ処理設定
    let config = ReportClientConfig {
        timeout: Duration::from_secs(30),
        max_concurrent_reports: 200,
        retry_attempts: 5,
        retry_delay: Duration::from_millis(1000),
        batching: BatchConfig {
            enable_batching: true,
            max_batch_size: 100,
            max_batch_wait_time: Duration::from_millis(2000),
            max_batch_memory_size: 2 * 1024 * 1024, // 2MB
        },
        ..Default::default()
    };
    
    let report_client = ReportClient::with_config("127.0.0.1:4112".parse()?, config).await?;
    
    // 複数のセンサーデータを送信
    let sensor_data = vec![
        ("temperature", 1, "通常温度", 35.6812, 139.7671),
        ("humidity", 2, "高湿度", 35.6813, 139.7672),
        ("seismic", 6, "地震活動", 35.6814, 139.7673),
        ("wind", 4, "強風", 35.6815, 139.7674),
        ("flood", 8, "洪水警報", 35.6816, 139.7675),
    ];
    
    for (disaster_type, severity, description, lat, lng) in sensor_data {
        let result = report_client.send_sensor_report(
            disaster_type,
            severity,
            description,
            Some(lat),
            Some(lng)
        ).await;
        
        match result {
            Ok(id) => println!("{}レポート送信成功 ID: {}", disaster_type, id),
            Err(e) => println!("{}レポート送信エラー: {}", disaster_type, e),
        }
    }
    
    Ok(())
}
```

### レポート通信の圧縮・暗号化

```rust
use wip_rust::wip_common_rs::clients::report_client::{CompressionConfig, EncryptionConfig};

async fn secure_reports() -> Result<(), Box<dyn std::error::Error>> {
    // セキュア設定
    let config = ReportClientConfig {
        compression: CompressionConfig {
            enable_compression: true,
            compression_level: 9,
            min_size_for_compression: 512,
        },
        encryption: EncryptionConfig {
            enable_encryption: true,
            encryption_key: Some(b"secure-32-byte-encryption-key!!".to_vec()),
            encryption_algorithm: "AES-256-GCM".to_string(),
        },
        ..Default::default()
    };
    
    let report_client = ReportClient::with_config("127.0.0.1:4112".parse()?, config).await?;
    
    // 暗号化・圧縮されたレポート送信
    let report_id = report_client.send_sensor_report(
        "confidential_data",
        9,
        "機密センサーデータ - 暗号化・圧縮済み",
        Some(35.6812),
        Some(139.7671)
    ).await?;
    
    println!("セキュアレポート送信完了 ID: {}", report_id);
    
    Ok(())
}
```

## 実行可能ファイル

### コマンドライン例

```bash
# Rust実装をビルド
cargo build --release

# 基本的なクライアント実行
cargo run --example client

# 構造化クライアント実行
cargo run --example structured_client

# パケット構造デモ実行
cargo run --example packet_showcase

# 単体テスト実行
cargo test

# 統合テスト実行
cargo test --test test_packets_fixed

# パフォーマンステスト実行
cargo test test_performance --release -- --nocapture

# ドキュメント生成
cargo doc --no-deps --open
```

### カスタムクライアント作成

```rust
// custom_client.rs
use wip_rust::prelude::*;
use std::env;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    // 環境変数から設定取得
    let server_host = env::var("WIP_SERVER_HOST").unwrap_or("127.0.0.1".to_string());
    let server_port: u16 = env::var("WIP_SERVER_PORT")
        .unwrap_or("4110".to_string())
        .parse()
        .unwrap_or(4110);
    
    // コマンドライン引数解析
    let args: Vec<String> = env::args().collect();
    if args.len() < 2 {
        println!("使用方法: {} <command> [args...]", args[0]);
        println!("コマンド:");
        println!("  weather <area_code>     - 天気データ取得");
        println!("  location <lat> <lng>    - 座標解決");
        println!("  report <type> <severity> <desc> - レポート送信");
        return Ok(());
    }
    
    match args[1].as_str() {
        "weather" => {
            if args.len() < 3 {
                println!("使用方法: weather <area_code>");
                return Ok(());
            }
            let area_code: u32 = args[2].parse()?;
            
            let mut client = WeatherClient::new(&server_host, server_port, true)?;
            if let Some(response) = client.get_weather_simple(area_code, true, true, true, false, false, 0)? {
                println!("天気データ: {:?}", response);
            } else {
                println!("レスポンスなし");
            }
        },
        
        "location" => {
            if args.len() < 4 {
                println!("使用方法: location <latitude> <longitude>");
                return Ok(());
            }
            let lat: f64 = args[2].parse()?;
            let lng: f64 = args[3].parse()?;
            
            let client = LocationClient::new(format!("{}:4109", server_host).parse()?).await?;
            let area_code = client.resolve_coordinates(lat, lng).await?;
            println!("エリアコード: {}", area_code);
        },
        
        "report" => {
            if args.len() < 5 {
                println!("使用方法: report <type> <severity> <description>");
                return Ok(());
            }
            let disaster_type = &args[2];
            let severity: u8 = args[3].parse()?;
            let description = &args[4];
            
            let client = ReportClient::new(format!("{}:4112", server_host).parse()?).await?;
            let report_id = client.send_sensor_report(
                disaster_type,
                severity,
                description,
                None,
                None
            ).await?;
            println!("レポートID: {}", report_id);
        },
        
        _ => {
            println!("不明なコマンド: {}", args[1]);
        }
    }
    
    Ok(())
}
```

## 設定とカスタマイズ

### 環境変数設定

```bash
# .env ファイル例
WIP_SERVER_HOST=127.0.0.1
WIP_WEATHER_PORT=4110
WIP_LOCATION_PORT=4109
WIP_QUERY_PORT=4111
WIP_REPORT_PORT=4112
WIP_AUTH_PASSPHRASE=your-secure-passphrase
WIP_ENABLE_DEBUG=true
WIP_TIMEOUT=30
WIP_RETRY_COUNT=3
```

### 設定ファイル使用

```rust
use wip_rust::wip_common_rs::utils::config_loader::ConfigLoader;

fn main() -> Result<(), Box<dyn std::error::Error>> {
    // 設定ファイル読み込み
    let config = ConfigLoader::from_file("wip_config.toml")?;
    
    let server_host = config.get_string("server.host").unwrap_or("127.0.0.1".to_string());
    let server_port = config.get_u16("server.port").unwrap_or(4110);
    let timeout = config.get_u64("client.timeout").unwrap_or(30);
    let debug = config.get_bool("client.debug").unwrap_or(false);
    
    let mut client = WeatherClient::new(&server_host, server_port, debug)?;
    client.set_timeout(Duration::from_secs(timeout));
    
    // 設定を使ってリクエスト実行
    // ...
    
    Ok(())
}
```

### ログ設定

```rust
use log::{info, warn, error, debug};
use env_logger;

fn main() {
    // ログ初期化
    env_logger::init();
    
    // ログレベル設定（環境変数RUST_LOG=debug）
    debug!("デバッグメッセージ");
    info!("情報メッセージ");
    warn!("警告メッセージ");
    error!("エラーメッセージ");
}
```

## トラブルシューティング

### 一般的なエラーと対処法

```rust
// 接続エラーの処理
fn handle_connection_error() {
    match WeatherClient::new("127.0.0.1", 4110, true) {
        Ok(client) => println!("接続成功"),
        Err(e) => {
            match e.kind() {
                std::io::ErrorKind::ConnectionRefused => {
                    println!("サーバーが起動していません");
                },
                std::io::ErrorKind::TimedOut => {
                    println!("接続タイムアウト");
                },
                _ => {
                    println!("接続エラー: {}", e);
                }
            }
        }
    }
}

// レスポンスタイムアウトの処理
async fn handle_timeout() {
    let client = LocationClient::new("127.0.0.1:4109".parse().unwrap()).await.unwrap();
    
    match tokio::time::timeout(
        Duration::from_secs(5),
        client.resolve_coordinates(35.6812, 139.7671)
    ).await {
        Ok(Ok(area_code)) => println!("エリアコード: {}", area_code),
        Ok(Err(e)) => println!("サーバーエラー: {}", e),
        Err(_) => println!("タイムアウトエラー"),
    }
}
```

このコマンドリファレンスを使用して、WIP Rust実装の全機能を効果的に活用してください。