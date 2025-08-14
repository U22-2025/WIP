# WIP Rust Implementation

Weather Information Protocol (WIP) クライアントライブラリのRust実装です。

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
    │   │   └── query_packet.rs         # QueryRequest/QueryResponse
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

### サンプル実行

```bash
# 新しい構造化されたクライアント
cargo run --example structured_client

# 旧クライアント（後方互換性）
cargo run --example client
```

## 機能

- ✅ QueryRequest/QueryResponse パケット処理
- ✅ 12ビットチェックサム計算
- ✅ パケットIDマッチング
- ✅ UDP通信（リトルエンディアン/LSB）
- ✅ WeatherServer統合

## Python版との対応

| Python | Rust |
|--------|------|
| `WIPCommonPy/clients/weather_client.py` | `wip_common_rs/clients/weather_client.rs` |
| `WIPCommonPy/clients/utils/packet_id_generator.py` | `wip_common_rs/clients/utils/packet_id_generator.rs` |
| `WIPCommonPy/packet/types/query_packet.py` | `wip_common_rs/packet/types/query_packet.rs` |

## 開発

```bash
# ビルド
cargo build

# テスト
cargo test

# サンプル実行
cargo run --example structured_client
```

## パケット仕様

- **リクエスト**: 16バイト (128bit)
- **レスポンス**: 20バイト (160bit)
- **エンディアン**: Little Endian
- **ビット順序**: LSB (Least Significant Bit first)