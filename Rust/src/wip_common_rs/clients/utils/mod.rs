/// クライアント用ユーティリティ

pub mod packet_id_generator;
pub mod receive_with_id;
pub mod safe_sock_sendto;
pub mod connection_pool;

// 便利な再エクスポート
pub use receive_with_id::{receive_with_id, receive_with_id_async, receive_multiple_with_ids, receive_multiple_with_ids_async, ReceiveConfig};
pub use safe_sock_sendto::{safe_sock_sendto, safe_sock_sendto_multiple, SafeSocketSender, SendConfig};
pub use connection_pool::{UdpConnectionPool, PooledUdpSocket, PoolConfig, ConnectionStats};