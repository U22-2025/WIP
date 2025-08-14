/// LocationRequest/LocationResponse パケット実装
/// Python版 location_packet.py と同等の機能

use crate::wip_common_rs::packet::core::{
    PacketFormat, AutoChecksumPacket, WipResult, WipPacketError, PacketParseError,
    BitField, PacketFields, bytes_to_u128_le, u128_to_bytes_le
};
use std::time::{SystemTime, UNIX_EPOCH};

/// LocationRequest パケット (Type=0)
/// 座標からエリアコードへの変換要求
#[derive(Debug, Clone, PartialEq)]
pub struct LocationRequest {
    pub version: u8,
    pub packet_id: u16,
    pub weather_flag: bool,
    pub temperature_flag: bool,
    pub pop_flag: bool,
    pub alert_flag: bool,
    pub disaster_flag: bool,
    pub ex_flag: bool,
    pub request_auth: bool,
    pub response_auth: bool,
    pub day: u8,
    pub timestamp: u64,
    pub latitude: f64,
    pub longitude: f64,
    pub checksum: u16,
}

impl LocationRequest {
    /// 新しいLocationRequestを作成
    pub fn new(
        packet_id: u16,
        latitude: f64,
        longitude: f64,
        weather: bool,
        temperature: bool,
        precipitation_prob: bool,
        alert: bool,
        disaster: bool,
        day: u8,
    ) -> Self {
        let timestamp = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap()
            .as_secs();
            
        Self {
            version: 1,
            packet_id,
            weather_flag: weather,
            temperature_flag: temperature,
            pop_flag: precipitation_prob,
            alert_flag: alert,
            disaster_flag: disaster,
            ex_flag: false,
            request_auth: false,
            response_auth: false,
            day: day & 0x07,
            timestamp,
            latitude,
            longitude,
            checksum: 0,
        }
    }
    
    /// 座標解決用のLocationRequestを作成
    pub fn create_coordinate_lookup(
        packet_id: u16,
        latitude: f64,
        longitude: f64,
        weather: bool,
        temperature: bool,
        precipitation_prob: bool,
        alert: bool,
        disaster: bool,
        version: u8,
    ) -> Self {
        Self {
            version,
            packet_id,
            weather_flag: weather,
            temperature_flag: temperature,
            pop_flag: precipitation_prob,
            alert_flag: alert,
            disaster_flag: disaster,
            ex_flag: false,
            request_auth: false,
            response_auth: false,
            day: 0,
            timestamp: SystemTime::now()
                .duration_since(UNIX_EPOCH)
                .unwrap()
                .as_secs(),
            latitude,
            longitude,
            checksum: 0,
        }
    }
    
    /// 座標を固定小数点形式に変換
    fn coord_to_fixed_point(coord: f64) -> u64 {
        // 座標を1000000倍して整数に変換（6桁精度）
        ((coord * 1_000_000.0).round() as i64) as u64
    }
    
    /// 固定小数点形式から座標に変換
    fn fixed_point_to_coord(fixed: u64) -> f64 {
        (fixed as i64) as f64 / 1_000_000.0
    }
}

impl PacketFormat for LocationRequest {
    fn to_bytes(&self) -> Vec<u8> {
        let mut data = [0u8; 24]; // 24バイト想定
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
            field.set(&mut bits_data, 0u128); // Type = 0 for LocationRequest
        }
        if let Some(field) = fields.get_field("weather_flag") {
            field.set(&mut bits_data, self.weather_flag as u128);
        }
        if let Some(field) = fields.get_field("temperature_flag") {
            field.set(&mut bits_data, self.temperature_flag as u128);
        }
        if let Some(field) = fields.get_field("pop_flag") {
            field.set(&mut bits_data, self.pop_flag as u128);
        }
        if let Some(field) = fields.get_field("alert_flag") {
            field.set(&mut bits_data, self.alert_flag as u128);
        }
        if let Some(field) = fields.get_field("disaster_flag") {
            field.set(&mut bits_data, self.disaster_flag as u128);
        }
        if let Some(field) = fields.get_field("ex_flag") {
            field.set(&mut bits_data, self.ex_flag as u128);
        }
        if let Some(field) = fields.get_field("request_auth") {
            field.set(&mut bits_data, self.request_auth as u128);
        }
        if let Some(field) = fields.get_field("response_auth") {
            field.set(&mut bits_data, self.response_auth as u128);
        }
        if let Some(field) = fields.get_field("day") {
            field.set(&mut bits_data, self.day as u128);
        }
        if let Some(field) = fields.get_field("timestamp") {
            field.set(&mut bits_data, self.timestamp as u128);
        }
        
        // 座標を固定小数点に変換して設定
        let lat_fixed = Self::coord_to_fixed_point(self.latitude);
        let lon_fixed = Self::coord_to_fixed_point(self.longitude);
        
        // 座標データは拡張フィールドとして扱うか、別の方法で格納
        // u128の範囲内で座標を格納（64ビットずつ）
        // 緯度・経度は拡張データとして実装予定
        
        u128_to_bytes_le(bits_data, &mut data);
        data.to_vec()
    }
    
    fn from_bytes(data: &[u8]) -> WipResult<Self> {
        if data.len() < 24 {
            return Err(WipPacketError::Parse(PacketParseError::insufficient_data(24, data.len())));
        }
        
        let bits_data = bytes_to_u128_le(data);
        let fields = Self::get_field_definitions();
        
        // フィールドから値を抽出
        let version = fields.get_field("version")
            .map(|f| f.extract(bits_data) as u8)
            .unwrap_or(1);
        let packet_id = fields.get_field("packet_id")
            .map(|f| f.extract(bits_data) as u16)
            .unwrap_or(0);
        
        // パケット型チェック
        let packet_type = fields.get_field("type")
            .map(|f| f.extract(bits_data) as u8)
            .unwrap_or(255);
        if packet_type != 0 {
            return Err(WipPacketError::Parse(PacketParseError::invalid_packet_type(packet_type)));
        }
        
        let weather_flag = fields.get_field("weather_flag")
            .map(|f| f.extract(bits_data) != 0)
            .unwrap_or(false);
        let temperature_flag = fields.get_field("temperature_flag")
            .map(|f| f.extract(bits_data) != 0)
            .unwrap_or(false);
        let pop_flag = fields.get_field("pop_flag")
            .map(|f| f.extract(bits_data) != 0)
            .unwrap_or(false);
        let alert_flag = fields.get_field("alert_flag")
            .map(|f| f.extract(bits_data) != 0)
            .unwrap_or(false);
        let disaster_flag = fields.get_field("disaster_flag")
            .map(|f| f.extract(bits_data) != 0)
            .unwrap_or(false);
        let ex_flag = fields.get_field("ex_flag")
            .map(|f| f.extract(bits_data) != 0)
            .unwrap_or(false);
        let request_auth = fields.get_field("request_auth")
            .map(|f| f.extract(bits_data) != 0)
            .unwrap_or(false);
        let response_auth = fields.get_field("response_auth")
            .map(|f| f.extract(bits_data) != 0)
            .unwrap_or(false);
        let day = fields.get_field("day")
            .map(|f| f.extract(bits_data) as u8)
            .unwrap_or(0);
        let timestamp = fields.get_field("timestamp")
            .map(|f| f.extract(bits_data) as u64)
            .unwrap_or(0);
        
        // 座標データはデフォルト値を使用（実際の座標は拡張フィールドから取得）
        let latitude = 0.0;
        let longitude = 0.0;
        
        let checksum = fields.get_field("checksum")
            .map(|f| f.extract(bits_data) as u16)
            .unwrap_or(0);
        
        Ok(Self {
            version,
            packet_id,
            weather_flag,
            temperature_flag,
            pop_flag,
            alert_flag,
            disaster_flag,
            ex_flag,
            request_auth,
            response_auth,
            day,
            timestamp,
            latitude,
            longitude,
            checksum,
        })
    }
    
    fn packet_size() -> usize {
        24 // LocationRequest は24バイト
    }
    
    fn packet_type() -> u8 {
        0 // LocationRequest のタイプ
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
            fields.add_field("weather_flag", 1);
            fields.add_field("temperature_flag", 1);
            fields.add_field("pop_flag", 1);
            fields.add_field("alert_flag", 1);
            fields.add_field("disaster_flag", 1);
            fields.add_field("ex_flag", 1);
            fields.add_field("request_auth", 1);
            fields.add_field("response_auth", 1);
            fields.add_field("day", 3);
            fields.add_field("reserved", 2);
            fields.add_field("timestamp", 64);
            fields.add_field("checksum", 12);
            fields
        })
    }
    
    fn get_checksum_field() -> Option<&'static BitField> {
        Self::get_field_definitions().get_field("checksum")
    }
}

impl AutoChecksumPacket for LocationRequest {}

/// LocationResponse パケット (Type=1) 
/// エリアコード解決結果の応答
#[derive(Debug, Clone, PartialEq)]
pub struct LocationResponse {
    pub version: u8,
    pub packet_id: u16,
    pub area_code: u32,
    pub success: bool,
    pub error_code: u8,
    pub checksum: u16,
}

impl LocationResponse {
    /// 新しいLocationResponseを作成
    pub fn new(packet_id: u16, area_code: u32, success: bool) -> Self {
        Self {
            version: 1,
            packet_id,
            area_code,
            success,
            error_code: if success { 0 } else { 1 },
            checksum: 0,
        }
    }
    
    /// 成功応答を作成
    pub fn success(packet_id: u16, area_code: u32) -> Self {
        Self::new(packet_id, area_code, true)
    }
    
    /// エラー応答を作成
    pub fn error(packet_id: u16, error_code: u8) -> Self {
        Self {
            version: 1,
            packet_id,
            area_code: 0,
            success: false,
            error_code,
            checksum: 0,
        }
    }
}

impl PacketFormat for LocationResponse {
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
            field.set(&mut bits_data, 1u128); // Type = 1 for LocationResponse
        }
        if let Some(field) = fields.get_field("area_code") {
            field.set(&mut bits_data, self.area_code as u128);
        }
        if let Some(field) = fields.get_field("success") {
            field.set(&mut bits_data, self.success as u128);
        }
        if let Some(field) = fields.get_field("error_code") {
            field.set(&mut bits_data, self.error_code as u128);
        }
        
        u128_to_bytes_le(bits_data, &mut data);
        data.to_vec()
    }
    
    fn from_bytes(data: &[u8]) -> WipResult<Self> {
        if data.len() < 16 {
            return Err(WipPacketError::Parse(PacketParseError::insufficient_data(16, data.len())));
        }
        
        let bits_data = bytes_to_u128_le(data);
        let fields = Self::get_field_definitions();
        
        // パケット型チェック
        let packet_type = fields.get_field("type")
            .map(|f| f.extract(bits_data) as u8)
            .unwrap_or(255);
        if packet_type != 1 {
            return Err(WipPacketError::Parse(PacketParseError::invalid_packet_type(packet_type)));
        }
        
        let version = fields.get_field("version")
            .map(|f| f.extract(bits_data) as u8)
            .unwrap_or(1);
        let packet_id = fields.get_field("packet_id")
            .map(|f| f.extract(bits_data) as u16)
            .unwrap_or(0);
        let area_code = fields.get_field("area_code")
            .map(|f| f.extract(bits_data) as u32)
            .unwrap_or(0);
        let success = fields.get_field("success")
            .map(|f| f.extract(bits_data) != 0)
            .unwrap_or(false);
        let error_code = fields.get_field("error_code")
            .map(|f| f.extract(bits_data) as u8)
            .unwrap_or(0);
        let checksum = fields.get_field("checksum")
            .map(|f| f.extract(bits_data) as u16)
            .unwrap_or(0);
        
        Ok(Self {
            version,
            packet_id,
            area_code,
            success,
            error_code,
            checksum,
        })
    }
    
    fn packet_size() -> usize {
        16 // LocationResponse は16バイト
    }
    
    fn packet_type() -> u8 {
        1 // LocationResponse のタイプ
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
            fields.add_field("area_code", 20);
            fields.add_field("success", 1);
            fields.add_field("error_code", 8);
            fields.add_field("checksum", 12);
            fields
        })
    }
    
    fn get_checksum_field() -> Option<&'static BitField> {
        Self::get_field_definitions().get_field("checksum")
    }
}

impl AutoChecksumPacket for LocationResponse {}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_location_request_creation() {
        let req = LocationRequest::new(
            123, 35.6762, 139.6503, true, true, false, false, false, 0
        );
        
        assert_eq!(req.version, 1);
        assert_eq!(req.packet_id, 123);
        assert_eq!(req.latitude, 35.6762);
        assert_eq!(req.longitude, 139.6503);
        assert!(req.weather_flag);
        assert!(req.temperature_flag);
        assert!(!req.pop_flag);
    }

    #[test]
    fn test_location_request_bytes_conversion() {
        let req = LocationRequest::new(
            456, 35.123456, 139.123456, true, false, true, false, true, 1
        );
        
        let bytes = req.to_bytes();
        assert_eq!(bytes.len(), 24);
        
        let parsed = LocationRequest::from_bytes(&bytes).unwrap();
        assert_eq!(parsed.packet_id, req.packet_id);
        assert_eq!(parsed.version, req.version);
        assert_eq!(parsed.weather_flag, req.weather_flag);
        assert_eq!(parsed.temperature_flag, req.temperature_flag);
        // 座標の精度チェック（小数点6桁の精度）
        assert!((parsed.latitude - req.latitude).abs() < 0.000001);
        assert!((parsed.longitude - req.longitude).abs() < 0.000001);
    }

    #[test]
    fn test_location_response_creation() {
        let resp = LocationResponse::success(789, 13101);
        
        assert_eq!(resp.version, 1);
        assert_eq!(resp.packet_id, 789);
        assert_eq!(resp.area_code, 13101);
        assert!(resp.success);
        assert_eq!(resp.error_code, 0);
    }

    #[test]
    fn test_location_response_error() {
        let resp = LocationResponse::error(999, 255);
        
        assert_eq!(resp.packet_id, 999);
        assert_eq!(resp.area_code, 0);
        assert!(!resp.success);
        assert_eq!(resp.error_code, 255);
    }

    #[test]
    fn test_location_response_bytes_conversion() {
        let resp = LocationResponse::success(111, 11000);
        
        let bytes = resp.to_bytes();
        assert_eq!(bytes.len(), 16);
        
        let parsed = LocationResponse::from_bytes(&bytes).unwrap();
        assert_eq!(parsed.packet_id, resp.packet_id);
        assert_eq!(parsed.area_code, resp.area_code);
        assert_eq!(parsed.success, resp.success);
        assert_eq!(parsed.error_code, resp.error_code);
    }

    #[test]
    fn test_packet_type_validation() {
        let req = LocationRequest::new(1, 0.0, 0.0, true, false, false, false, false, 0);
        let mut bytes = req.to_bytes();
        
        // パケット型を不正に変更
        bytes[2] = 0xFF; // type フィールドを破壊
        
        let result = LocationRequest::from_bytes(&bytes);
        assert!(result.is_err());
    }

    #[test]
    fn test_coordinate_precision() {
        let test_coords = [
            (0.0, 0.0),
            (90.0, 180.0),
            (-90.0, -180.0),
            (35.123456, 139.654321),
            (-12.345678, -98.765432),
        ];
        
        for (lat, lon) in test_coords {
            let req = LocationRequest::new(1, lat, lon, true, false, false, false, false, 0);
            let bytes = req.to_bytes();
            let parsed = LocationRequest::from_bytes(&bytes).unwrap();
            
            // 6桁精度での比較
            assert!((parsed.latitude - lat).abs() < 0.000001, 
                    "Latitude precision error: {} vs {}", parsed.latitude, lat);
            assert!((parsed.longitude - lon).abs() < 0.000001, 
                    "Longitude precision error: {} vs {}", parsed.longitude, lon);
        }
    }
}