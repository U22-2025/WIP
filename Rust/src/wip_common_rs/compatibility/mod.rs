/*!
 * Python互換性モジュール
 * Python版WIPとの完全互換性を提供
 */

pub mod python_protocol;
pub mod python_packet_format_adapter;

// 便利な再エクスポート
pub use python_protocol::{
    PythonCompatibleErrorCode,
    PythonCompatibleConfig,
    PythonCompatibleProtocol,
    ErrorLevel,
    ServerConfig,
    ClientConfig,
    LoggingConfig,
    CacheConfig,
    NetworkConfig,
    AuthConfig,
};

pub use python_packet_format_adapter::{
    PythonPacketFormat,
    PythonFieldDefinition,
    PythonPacketFormatAdapter,
};