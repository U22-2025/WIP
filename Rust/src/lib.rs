/// WIP Rust Implementation
/// Weather Information Protocol client and utilities in Rust

// 新しい構造化されたライブラリ
pub mod wip_common_rs;

// 便利な再エクスポート
pub mod prelude {
    pub use crate::wip_common_rs::clients::weather_client::WeatherClient;
    pub use crate::wip_common_rs::clients::utils::packet_id_generator::PacketIDGenerator12Bit;
    pub use crate::wip_common_rs::packet::types::{QueryRequest, QueryResponse};
}

// 後方互換性のための古い構造（廃止予定）
// 旧構成はテストからは除外（レガシーモジュールのテストが新仕様と競合するため）
#[cfg(not(test))]
#[path = "../common/mod.rs"]
pub mod common;
#[cfg(not(test))]
#[path = "../WIP_Client/mod.rs"]
pub mod wip_client;
