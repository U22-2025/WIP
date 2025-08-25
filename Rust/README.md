# WIP Rust Implementation

Weather Information Protocol (WIP) クライアントライブラリのRust実装です。

現在は `wip_common_rs` が正式な実装であり、従来の `common/` と `WIP_Client/` ディレクトリは `deprecated/` 以下に移動して非推奨となりました。

## 構造

```
src/
├── lib.rs                              # ライブラリエントリポイント
└── wip_common_rs/                      # 新しい構造化されたライブラリ
    ├── mod.rs
    ├── clients/                        # クライアント実装
    │   ├── mod.rs
    │   ├── weather_client.rs           # WeatherServer通信クライアント
    │   └── utils/                      # クライアント用ユーティリティ
    │       ├── mod.rs
    │       └── packet_id_generator.rs  # パケットID生成器
    ├── packet/                         # パケット処理
    │   ├── mod.rs
    │   ├── types/                      # パケット型定義
    │   │   ├── mod.rs
    │   │   ├── query_packet.rs         # QueryRequest/QueryResponse（仕様駆動）
    │   │   ├── location_packet.rs      # LocationRequest/LocationResponse（Ex対応）
    │   │   └── report_packet.rs        # ReportRequest/ReportResponse
    │   ├── core/                       # コア機能（チェックサム等）
    │   │   └── mod.rs
    │   └── models/                     # データモデル
    │       └── mod.rs
    └── utils/                          # 共通ユーティリティ
        └── mod.rs
```

## 使用方法

### 基本的な使用例

```rust
use wip_rust::prelude::*;

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let mut client = WeatherClient::new("127.0.0.1", 4110, true)?;
    
    match client.get_weather_simple(11000, true, true, true, false, false, 0) {
        Ok(Some(resp)) => {
            println!("Area Code: {}", resp.area_code);
            if let Some(temp) = resp.temperature {
                println!("Temperature: {}°C", temp);
            }
            if let Some(weather) = resp.weather_code {
                println!("Weather Code: {}", weather);
            }
        }
        Ok(None) => println!("No response received"),
        Err(e) => eprintln!("Error: {}", e),
    }
    
    Ok(())
}
```

### 統合クライアント `WipClient`

Python版 `WIPClientPy.Client` と同じ操作感を提供する高レベルAPIです。

```rust
use wip_rust::wip_common_rs::client::WipClient;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let mut client = WipClient::new("127.0.0.1", 4111, 4109, 4111, 4112, false).await?;
    client.set_area_code(11000);
    if let Some(resp) = client
        .get_weather(true, true, true, false, false, 0, true)
        .await?
    {
        if let Some(temp) = resp.temperature {
            println!("Temperature: {}°C", temp);
        }
    }
    Ok(())
}
```

### サンプル実行

```bash
# 新しい構造化されたクライアント（推奨）
cargo run --example structured_client

# シンプルなクライアント（Weatherのみの最小例）
cargo run --example client

# パケット生成/復号のショーケース（Query/Location/Report）
cargo run --example packet_showcase
```

## 機能

- ✅ QueryRequest/Response（仕様駆動・JSONフィールド定義）
- ✅ LocationRequest/Response（座標は拡張フィールド、Exレスポンス対応）
- ✅ ReportRequest/Response（Type4/5、温度+100オフセット、拡張フィールド）
- ✅ 12ビットチェックサム（calc/verify）
- ✅ パケットIDマッチング（version 4bit + id 12bit）
- ✅ UDP通信（Little Endian / LSB）

## Python版との対応

| Python | Rust |
|--------|------|
| `WIPCommonPy/clients/weather_client.py` | `wip_common_rs/clients/weather_client.rs` |
| `WIPCommonPy/clients/utils/packet_id_generator.py` | `wip_common_rs/clients/utils/packet_id_generator.rs` |
| `WIPCommonPy/packet/types/query_packet.py` | `wip_common_rs/packet/types/query_packet.rs` |
| `WIPCommonPy/packet/types/location_packet.py` | `wip_common_rs/packet/types/location_packet.rs` |
| `WIPCommonPy/packet/types/report_packet.py` | `wip_common_rs/packet/types/report_packet.rs` |
| `WIPClientPy.Client` | `wip_common_rs/client.rs` |

> Note: 旧構成は `deprecated/common/*` や `deprecated/WIP_Client/*` に移動され非推奨です。新規実装・サンプルは `src/wip_common_rs/*` を参照してください。

### 互換性ノート（重要）

- パケットID抽出はプロトコル準拠で処理します（先頭2バイトのうち、上位4bit=version、下位12bit=packet_id）。全クライアントで `(u16_le >> 4) & 0x0FFF` を適用しました。
- 温度はPython実装と同じく+100オフセットで格納／復号します（例: `22°C -> 122`）。
- エリアコードは外部APIでは6桁文字列、内部では20bit整数として扱います（ゼロ埋め正規化済み）。

## 開発

```bash
# ビルド
cargo build

# テスト
cargo test

# サンプル実行
cargo run --example structured_client

# 追加サンプル（例）
# - Location/Report の使い方は `src/wip_common_rs/packet/types/*.rs` のテストを参照
```

## パケット仕様

- **リクエスト**: 16バイト (128bit)
- **レスポンス**: 20バイト (160bit)
- **エンディアン**: Little Endian
- **ビット順序**: LSB (Least Significant Bit first)
