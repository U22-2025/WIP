//! パケットコア機能
//! チェックサム計算、ビット操作、エラー処理等のコア機能

pub mod checksum;
pub mod bit_utils;
pub mod exceptions;
pub mod format_base;
pub mod extended_field;

// 便利な再エクスポート
pub use checksum::{calc_checksum12, verify_checksum12, calc_checksum12_optimized};
pub use bit_utils::{extract_bits, set_bits, bytes_to_u128_le, u128_to_bytes_le, BitField, PacketFields};
pub use exceptions::{PacketParseError, ChecksumError, InvalidFieldError, WipPacketError, WipResult};
pub use format_base::{PacketFormat, AutoChecksumPacket, PacketDefinitionBuilder, JsonPacketSpecLoader, PacketValidator};
pub use extended_field::{FieldType, FieldDefinition, FieldValue, ExtendedFieldManager};