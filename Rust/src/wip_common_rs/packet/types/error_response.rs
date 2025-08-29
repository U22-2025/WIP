/// ErrorResponse パケット実装
/// Python版 error_response.py と同等の機能
/// Type 7 エラーパケット、送信元情報をオプションで含む

use crate::wip_common_rs::packet::core::{
    PacketFormat, AutoChecksumPacket, WipResult, WipPacketError, PacketParseError,
    BitField, PacketFields, bytes_to_u128_le, u128_to_bytes_le
};
use std::time::{SystemTime, UNIX_EPOCH};
use std::collections::HashMap;

/// ErrorResponse パケット (Type=7)
/// エラー情報を含むレスポンスパケット
#[derive(Debug, Clone, PartialEq)]
pub struct ErrorResponse {
    pub version: u8,
    pub packet_id: u16,
    pub ex_flag: bool,
    pub timestamp: u64,
    pub error_code: u16, // weather_code フィールドを流用
    pub checksum: u16,
    pub extended_fields: Option<HashMap<String, String>>, // 拡張フィールド
}

impl ErrorResponse {
    /// バイト列から ErrorResponse を作成（Optional を返すバージョン）
    pub fn parse_bytes(data: &[u8]) -> Option<Self> {
        if data.len() < 16 {
            eprintln!("ErrorResponse: insufficient length {}", data.len());
            return None;
        }
        
        use bitvec::prelude::*;
        let bits = BitSlice::<u8, Lsb0>::from_slice(data);
        
        let packet_type: u8 = bits[16..19].load();
        if packet_type != 7 {
            eprintln!("ErrorResponse: wrong type, expected 7 got {}", packet_type);
            return None;
        }
        
        let version: u8 = bits[0..4].load();
        let packet_id: u16 = bits[4..16].load();
        let ex_flag: bool = bits[25..26].load::<u8>() != 0;
        let timestamp: u64 = bits[32..96].load();
        let error_code: u16 = bits[128..144].load(); // weather_code field position
        let checksum: u16 = bits[116..128].load();
        
        Some(Self {
            version,
            packet_id,
            ex_flag,
            timestamp,
            error_code,
            checksum,
            extended_fields: None,
        })
    }
    
    /// 新しいErrorResponseを作成
    pub fn new(
        packet_id: u16,
        error_code: u16,
        version: u8,
        timestamp: Option<u64>,
        extended_fields: Option<HashMap<String, String>>,
    ) -> Self {
        let timestamp = timestamp.unwrap_or_else(|| {
            SystemTime::now()
                .duration_since(UNIX_EPOCH)
                .unwrap()
                .as_secs()
        });

        let ex_flag = extended_fields.is_some();

        Self {
            version,
            packet_id,
            ex_flag,
            timestamp,
            error_code,
            checksum: 0,
            extended_fields,
        }
    }

    /// シンプルなエラー応答を作成
    pub fn simple_error(packet_id: u16, error_code: u16) -> Self {
        Self::new(packet_id, error_code, 1, None, None)
    }

    /// 送信元情報付きエラー応答を作成
    pub fn with_source(packet_id: u16, error_code: u16, source_ip: &str, source_port: u16) -> Self {
        let mut extended_fields = HashMap::new();
        extended_fields.insert("source".to_string(), format!("{}:{}", source_ip, source_port));

        Self::new(packet_id, error_code, 1, None, Some(extended_fields))
    }

    /// 拡張フィールドを設定
    pub fn set_extended_field(&mut self, key: &str, value: &str) {
        if self.extended_fields.is_none() {
            self.extended_fields = Some(HashMap::new());
        }
        if let Some(ref mut fields) = self.extended_fields {
            fields.insert(key.to_string(), value.to_string());
        }
        self.ex_flag = true;
    }

    /// 送信元情報を取得
    pub fn get_source_info(&self) -> Option<(String, u16)> {
        self.extended_fields.as_ref()
            .and_then(|fields| fields.get("source"))
            .and_then(|source| {
                let parts: Vec<&str> = source.split(':').collect();
                if parts.len() == 2 {
                    if let (Ok(port), ip) = (parts[1].parse::<u16>(), parts[0]) {
                        return Some((ip.to_string(), port));
                    }
                }
                None
            })
    }

    /// エラーコードを取得
    pub fn get_error_code(&self) -> u16 {
        self.error_code
    }

    /// エラーコードを設定
    pub fn set_error_code(&mut self, code: u16) {
        self.error_code = code;
    }

    /// エラーが致命的かどうかを判定
    pub fn is_fatal_error(&self) -> bool {
        // 一般的なエラーコードの分類
        match self.error_code {
            400..=499 => false, // クライアントエラー（リトライ可能）
            500..=599 => true,  // サーバーエラー（致命的）
            _ => false,
        }
    }

    /// エラー種別の文字列表現を取得
    pub fn get_error_type(&self) -> &'static str {
        match self.error_code {
            400 => "Bad Request",
            401 => "Unauthorized", 
            403 => "Forbidden",
            404 => "Not Found",
            408 => "Request Timeout",
            429 => "Too Many Requests",
            500 => "Internal Server Error",
            502 => "Bad Gateway",
            503 => "Service Unavailable",
            504 => "Gateway Timeout",
            _ => "Unknown Error",
        }
    }
}

impl PacketFormat for ErrorResponse {
    fn to_bytes(&self) -> Vec<u8> {
        let mut data = [0u8; 16]; // 16バイト想定
        let mut bits_data = bytes_to_u128_le(&data);
        
        let fields = Self::get_field_definitions();
        
        // フィールドを設定
        if let Some(field) = fields.get_field("version") {
            field.set(&mut bits_data, self.version as u128);
        }
        if let Some(field) = fields.get_field("packet_id") {
            field.set(&mut bits_data, self.packet_id as u128);
        }
        if let Some(field) = fields.get_field("type") {
            field.set(&mut bits_data, 7u128); // Type = 7 for ErrorResponse
        }
        if let Some(field) = fields.get_field("ex_flag") {
            field.set(&mut bits_data, self.ex_flag as u128);
        }
        if let Some(field) = fields.get_field("timestamp") {
            field.set(&mut bits_data, self.timestamp as u128);
        }
        if let Some(field) = fields.get_field("weather_code") { // error_code として使用
            field.set(&mut bits_data, self.error_code as u128);
        }
        
        // チェックサムを自動計算
        let checksum = self.calculate_checksum();
        if let Some(field) = fields.get_field("checksum") {
            field.set(&mut bits_data, checksum as u128);
        }
        
        u128_to_bytes_le(bits_data, &mut data);
        data.to_vec()
    }
    
    fn from_bytes(data: &[u8]) -> WipResult<Self> {
        Self::parse_bytes(data)
            .ok_or_else(|| WipPacketError::Parse(PacketParseError::UnexpectedFormat("Failed to parse ErrorResponse".to_string())))
    }
    
    fn packet_size() -> usize {
        16 // ErrorResponse は16バイト
    }
    
    fn packet_type() -> u8 {
        7 // ErrorResponse のタイプ
    }
    
    fn version(&self) -> u8 {
        self.version
    }
    
    fn packet_id(&self) -> u16 {
        self.packet_id
    }
    
    fn get_field_definitions() -> &'static PacketFields {
        use std::sync::OnceLock;
        static FIELDS: OnceLock<PacketFields> = OnceLock::new();
        
        FIELDS.get_or_init(|| {
            let mut fields = PacketFields::new();
            fields.add_field("version", 4);
            fields.add_field("packet_id", 12);
            fields.add_field("type", 3);
            fields.add_field("ex_flag", 1);
            fields.add_field("reserved", 12); // 未使用領域
            fields.add_field("timestamp", 64);
            fields.add_field("weather_code", 16); // error_code として使用
            fields.add_field("checksum", 12);
            fields
        })
    }
    
    fn get_checksum_field() -> Option<&'static BitField> {
        Self::get_field_definitions().get_field("checksum")
    }
}

impl AutoChecksumPacket for ErrorResponse {}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_error_response_creation() {
        let error_resp = ErrorResponse::simple_error(123, 404);
        
        assert_eq!(error_resp.version, 1);
        assert_eq!(error_resp.packet_id, 123);
        assert_eq!(error_resp.error_code, 404);
        assert!(!error_resp.ex_flag);
        assert_eq!(error_resp.get_error_type(), "Not Found");
    }

    #[test]
    fn test_error_response_with_source() {
        let error_resp = ErrorResponse::with_source(456, 500, "192.168.1.100", 8080);
        
        assert_eq!(error_resp.packet_id, 456);
        assert_eq!(error_resp.error_code, 500);
        assert!(error_resp.ex_flag);
        
        let source = error_resp.get_source_info();
        assert_eq!(source, Some(("192.168.1.100".to_string(), 8080)));
        assert_eq!(error_resp.get_error_type(), "Internal Server Error");
        assert!(error_resp.is_fatal_error());
    }

    #[test]
    fn test_error_response_bytes_conversion() {
        let error_resp = ErrorResponse::simple_error(789, 403);
        
        let bytes = error_resp.to_bytes();
        assert_eq!(bytes.len(), 16);
        
        let parsed = ErrorResponse::from_bytes(&bytes).unwrap();
        assert_eq!(parsed.packet_id, error_resp.packet_id);
        assert_eq!(parsed.error_code, error_resp.error_code);
        assert_eq!(parsed.ex_flag, error_resp.ex_flag);
        assert_eq!(parsed.version, error_resp.version);
    }

    #[test]
    fn test_packet_type_validation() {
        let error_resp = ErrorResponse::simple_error(1, 400);
        let mut bytes = error_resp.to_bytes();
        // パケット型(Type)はヘッダ内の 16..19bit（3bit）
        {
            use bitvec::prelude::*;
            let bits = BitSlice::<u8, Lsb0>::from_slice_mut(&mut bytes[..16]);
            bits[16..19].store(0u8); // 不正タイプに書き換え
        }
        let result = ErrorResponse::from_bytes(&bytes);
        assert!(result.is_err());
    }

    #[test]
    fn test_extended_fields() {
        let mut error_resp = ErrorResponse::simple_error(1, 502);
        error_resp.set_extended_field("source", "10.0.0.1:9000");
        error_resp.set_extended_field("details", "Database connection failed");
        
        assert!(error_resp.ex_flag);
        let source = error_resp.get_source_info();
        assert_eq!(source, Some(("10.0.0.1".to_string(), 9000)));
        
        if let Some(fields) = &error_resp.extended_fields {
            assert_eq!(fields.get("details"), Some(&"Database connection failed".to_string()));
        }
    }

    #[test]
    fn test_error_code_types() {
        let test_cases = [
            (400, "Bad Request", false),
            (401, "Unauthorized", false),
            (404, "Not Found", false),
            (500, "Internal Server Error", true),
            (503, "Service Unavailable", true),
            (999, "Unknown Error", false),
        ];

        for (code, expected_type, expected_fatal) in test_cases {
            let error_resp = ErrorResponse::simple_error(1, code);
            assert_eq!(error_resp.get_error_type(), expected_type);
            assert_eq!(error_resp.is_fatal_error(), expected_fatal);
        }
    }

    #[test]
    fn test_error_code_modification() {
        let mut error_resp = ErrorResponse::simple_error(1, 400);
        assert_eq!(error_resp.get_error_code(), 400);
        
        error_resp.set_error_code(500);
        assert_eq!(error_resp.get_error_code(), 500);
        assert!(error_resp.is_fatal_error());
    }

    #[test]
    fn test_timestamp_handling() {
        let custom_timestamp = 1609459200; // 2021-01-01 00:00:00 UTC
        let error_resp = ErrorResponse::new(1, 404, 1, Some(custom_timestamp), None);
        
        assert_eq!(error_resp.timestamp, custom_timestamp);
        
        // デフォルトタイムスタンプのテスト
        let error_resp_default = ErrorResponse::simple_error(1, 404);
        assert!(error_resp_default.timestamp > 0);
        
        // 現在時刻に近いことを確認（10秒以内の誤差を許容）
        let now = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap()
            .as_secs();
        assert!((error_resp_default.timestamp as i64 - now as i64).abs() < 10);
    }
}
