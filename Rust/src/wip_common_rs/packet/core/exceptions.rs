/// WIP パケット処理用エラー型定義
/// Python版の例外クラスに対応するRustのエラー型

use std::fmt;
use std::error::Error;

/// パケット解析エラー
#[derive(Debug, Clone, PartialEq)]
pub enum PacketParseError {
    /// データが短すぎる
    InsufficientData { required: usize, actual: usize },
    /// 不正なパケット型
    InvalidPacketType(u8),
    /// 不正なバージョン
    InvalidVersion(u8),
    /// フィールド値が範囲外
    FieldOutOfRange { field: String, value: u128, max: u128 },
    /// 予期しないデータ形式
    UnexpectedFormat(String),
}

impl fmt::Display for PacketParseError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            PacketParseError::InsufficientData { required, actual } => {
                write!(f, "データが不足しています: 必要 {}バイト, 実際 {}バイト", required, actual)
            }
            PacketParseError::InvalidPacketType(packet_type) => {
                write!(f, "不正なパケット型: {}", packet_type)
            }
            PacketParseError::InvalidVersion(version) => {
                write!(f, "サポートされていないバージョン: {}", version)
            }
            PacketParseError::FieldOutOfRange { field, value, max } => {
                write!(f, "フィールド '{}' の値が範囲外: {} (最大: {})", field, value, max)
            }
            PacketParseError::UnexpectedFormat(msg) => {
                write!(f, "予期しないデータ形式: {}", msg)
            }
        }
    }
}

impl Error for PacketParseError {}

/// チェックサムエラー
#[derive(Debug, Clone, PartialEq)]
pub enum ChecksumError {
    /// チェックサム不一致
    Mismatch { expected: u16, actual: u16 },
    /// チェックサム計算不能
    CalculationFailed(String),
    /// チェックサムフィールドが見つからない
    FieldNotFound,
}

impl fmt::Display for ChecksumError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            ChecksumError::Mismatch { expected, actual } => {
                write!(f, "チェックサム検証に失敗しました。期待値: 0x{:03X}, 実際: 0x{:03X}", expected, actual)
            }
            ChecksumError::CalculationFailed(msg) => {
                write!(f, "チェックサム計算に失敗しました: {}", msg)
            }
            ChecksumError::FieldNotFound => {
                write!(f, "チェックサムフィールドが見つかりません")
            }
        }
    }
}

impl Error for ChecksumError {}

/// フィールド値エラー
#[derive(Debug, Clone, PartialEq)]
pub enum InvalidFieldError {
    /// 必須フィールドが空
    RequiredFieldEmpty(String),
    /// フィールド型不一致
    TypeMismatch { field: String, expected: String, actual: String },
    /// フィールド値が制約に違反
    ConstraintViolation { field: String, constraint: String },
    /// 不明なフィールド
    UnknownField(String),
}

impl fmt::Display for InvalidFieldError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            InvalidFieldError::RequiredFieldEmpty(field) => {
                write!(f, "必須フィールド '{}' が空です", field)
            }
            InvalidFieldError::TypeMismatch { field, expected, actual } => {
                write!(f, "フィールド '{}' の型不一致: 期待 {}, 実際 {}", field, expected, actual)
            }
            InvalidFieldError::ConstraintViolation { field, constraint } => {
                write!(f, "フィールド '{}' が制約に違反: {}", field, constraint)
            }
            InvalidFieldError::UnknownField(field) => {
                write!(f, "不明なフィールド: {}", field)
            }
        }
    }
}

impl Error for InvalidFieldError {}

/// WIP パケット処理の統合エラー型
#[derive(Debug, Clone, PartialEq)]
pub enum WipPacketError {
    /// パケット解析エラー
    Parse(PacketParseError),
    /// チェックサムエラー
    Checksum(ChecksumError),
    /// フィールドエラー
    Field(InvalidFieldError),
    /// I/O エラー
    Io(String),
    /// ネットワークエラー
    Network(String),
}

impl fmt::Display for WipPacketError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            WipPacketError::Parse(err) => write!(f, "パケット解析エラー: {}", err),
            WipPacketError::Checksum(err) => write!(f, "チェックサムエラー: {}", err),
            WipPacketError::Field(err) => write!(f, "フィールドエラー: {}", err),
            WipPacketError::Io(msg) => write!(f, "I/Oエラー: {}", msg),
            WipPacketError::Network(msg) => write!(f, "ネットワークエラー: {}", msg),
        }
    }
}

impl Error for WipPacketError {
    fn source(&self) -> Option<&(dyn Error + 'static)> {
        match self {
            WipPacketError::Parse(err) => Some(err),
            WipPacketError::Checksum(err) => Some(err),
            WipPacketError::Field(err) => Some(err),
            _ => None,
        }
    }
}

// From実装で自動変換をサポート
impl From<PacketParseError> for WipPacketError {
    fn from(err: PacketParseError) -> Self {
        WipPacketError::Parse(err)
    }
}

impl From<ChecksumError> for WipPacketError {
    fn from(err: ChecksumError) -> Self {
        WipPacketError::Checksum(err)
    }
}

impl From<InvalidFieldError> for WipPacketError {
    fn from(err: InvalidFieldError) -> Self {
        WipPacketError::Field(err)
    }
}

impl From<std::io::Error> for WipPacketError {
    fn from(err: std::io::Error) -> Self {
        WipPacketError::Io(err.to_string())
    }
}

/// Result型のエイリアス
pub type WipResult<T> = Result<T, WipPacketError>;

/// エラーヘルパー関数
impl PacketParseError {
    /// データ不足エラーを作成
    pub fn insufficient_data(required: usize, actual: usize) -> Self {
        PacketParseError::InsufficientData { required, actual }
    }
    
    /// 不正なパケット型エラーを作成
    pub fn invalid_packet_type(packet_type: u8) -> Self {
        PacketParseError::InvalidPacketType(packet_type)
    }
    
    /// フィールド範囲外エラーを作成
    pub fn field_out_of_range(field: &str, value: u128, max: u128) -> Self {
        PacketParseError::FieldOutOfRange {
            field: field.to_string(),
            value,
            max,
        }
    }
}

impl ChecksumError {
    /// チェックサム不一致エラーを作成
    pub fn mismatch(expected: u16, actual: u16) -> Self {
        ChecksumError::Mismatch { expected, actual }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_packet_parse_error_display() {
        let err = PacketParseError::insufficient_data(20, 16);
        assert_eq!(
            format!("{}", err),
            "データが不足しています: 必要 20バイト, 実際 16バイト"
        );
        
        let err = PacketParseError::invalid_packet_type(255);
        assert_eq!(format!("{}", err), "不正なパケット型: 255");
    }

    #[test]
    fn test_checksum_error_display() {
        let err = ChecksumError::mismatch(0x123, 0x456);
        assert_eq!(
            format!("{}", err),
            "チェックサム検証に失敗しました。期待値: 0x123, 実際: 0x456"
        );
    }

    #[test]
    fn test_wip_packet_error_conversion() {
        let parse_err = PacketParseError::invalid_packet_type(99);
        let wip_err: WipPacketError = parse_err.clone().into();
        
        match wip_err {
            WipPacketError::Parse(err) => assert_eq!(err, parse_err),
            _ => panic!("Conversion failed"),
        }
    }

    #[test]
    fn test_error_chain() {
        let parse_err = PacketParseError::insufficient_data(10, 5);
        let wip_err = WipPacketError::from(parse_err);
        
        assert!(wip_err.source().is_some());
    }

    #[test]
    fn test_result_alias() {
        fn test_function() -> WipResult<u32> {
            Err(PacketParseError::invalid_packet_type(1).into())
        }
        
        assert!(test_function().is_err());
    }
}