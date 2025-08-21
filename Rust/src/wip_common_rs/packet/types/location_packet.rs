/// LocationRequest/LocationResponse パケット実装
/// Python版 location_packet.py の挙動に合わせ、拡張フィールドで座標を送る

use crate::wip_common_rs::packet::core::{
    PacketFormat, AutoChecksumPacket, WipResult, WipPacketError, PacketParseError,
    BitField, PacketFields, bytes_to_u128_le, u128_to_bytes_le
};
use crate::wip_common_rs::packet::core::checksum::{embed_checksum12_at};
use crate::wip_common_rs::packet::core::format_base::JsonPacketSpecLoader;
use crate::wip_common_rs::packet::core::extended_field::{ExtendedFieldManager, FieldDefinition, FieldType, FieldValue, unpack_ext_fields, pack_ext_fields};
use once_cell::sync::Lazy;
use std::collections::HashMap;
use std::time::{SystemTime, UNIX_EPOCH};
use bitvec::prelude::*;
use crate::wip_common_rs::packet::core::checksum::verify_checksum12;

static REQUEST_FIELDS: Lazy<PacketFields> = Lazy::new(|| {
    let json = include_str!("../format_spec/request_fields.json");
    let (fields, _specs) = JsonPacketSpecLoader::load_from_json(json).expect("request spec parse");
    fields
});

static RESPONSE_FIELDS: Lazy<PacketFields> = Lazy::new(|| {
    let json = include_str!("../format_spec/response_fields.json");
    let (fields, _specs) = JsonPacketSpecLoader::load_from_json(json).expect("response spec parse");
    fields
});

#[derive(Debug, Clone, PartialEq)]
pub struct LocationRequest {
    pub version: u8,
    pub packet_id: u16,
    pub weather_flag: bool,
    pub temperature_flag: bool,
    pub pop_flag: bool,
    pub alert_flag: bool,
    pub disaster_flag: bool,
    pub day: u8,
    pub timestamp: u64,
    pub latitude: f64,
    pub longitude: f64,
}

impl LocationRequest {
    /// Python互換：座標からエリアコードを検索するリクエスト（Type=0）
    pub fn create_coordinate_lookup(
        latitude: f64,
        longitude: f64,
        packet_id: u16,
        weather: bool,
        temperature: bool,
        precipitation_prob: bool,
        alert: bool,
        disaster: bool,
        day: u8,
        version: u8,
    ) -> Self {
        let timestamp = SystemTime::now().duration_since(UNIX_EPOCH).unwrap().as_secs();
        Self {
            version,
            packet_id,
            weather_flag: weather,
            temperature_flag: temperature,
            pop_flag: precipitation_prob,
            alert_flag: alert,
            disaster_flag: disaster,
            day: day & 0x07,
            timestamp,
            latitude,
            longitude,
        }
    }

    /// パケットをエンコード（Python互換: 全体でチェックサム計算）
    pub fn to_bytes(&self) -> Vec<u8> {
        // Python版と同じ手順：
        // 1. チェックサムを0にしてヘッダを構築
        // 2. 拡張フィールドを追加
        // 3. 全体でチェックサムを計算
        // 4. チェックサムを埋め込み
        
        // 拡張フィールド（latitude/longitude）をPython準拠でpack
        let mut map = HashMap::new();
        map.insert("latitude".to_string(), FieldValue::F64(self.latitude));
        map.insert("longitude".to_string(), FieldValue::F64(self.longitude));
        let ext = pack_ext_fields(&map);
        
        // 全パケットサイズでバッファを確保
        let total_size = 16 + ext.len();
        let mut packet = vec![0u8; total_size];
        
        // ヘッダを構築（チェックサムは0のまま）
        {
            let bits = BitSlice::<u8, Lsb0>::from_slice_mut(&mut packet[..16]);
            bits[0..4].store(self.version);
            bits[4..16].store(self.packet_id);
            bits[16..19].store(0u8); // type=0
            bits[19..20].store(self.weather_flag as u8);
            bits[20..21].store(self.temperature_flag as u8);
            bits[21..22].store(self.pop_flag as u8);
            bits[22..23].store(self.alert_flag as u8);
            bits[23..24].store(self.disaster_flag as u8);
            bits[24..25].store(1u8); // ex_flag = 1
            bits[25..26].store(0u8); // request_auth
            bits[26..27].store(0u8); // response_auth
            bits[27..30].store(self.day);
            bits[30..32].store(0u8); // reserved
            bits[32..96].store(self.timestamp);
            bits[96..116].store(0u32); // area_code無し
            bits[116..128].store(0u16); // checksum placeholder
        }
        
        // 拡張フィールドをコピー
        packet[16..].copy_from_slice(&ext);
        
        // Python版と同様：全パケット（最小サイズまでパディング）でチェックサムを計算
        let min_packet_size = 16; // 基本ヘッダサイズ（Python版のget_min_packet_size相当）
        if packet.len() < min_packet_size {
            packet.resize(min_packet_size, 0);
        }
        
        // 全体でチェックサムを計算して埋め込み
        embed_checksum12_at(&mut packet, 116, 12);
        
        packet
    }
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
        Self::create_coordinate_lookup(
            latitude,
            longitude,
            packet_id,
            weather,
            temperature,
            precipitation_prob,
            alert,
            disaster,
            day,
            1, // version
        )
    }
}

impl PacketFormat for LocationRequest {
    fn to_bytes(&self) -> Vec<u8> {
        // Call the LocationRequest specific implementation
        LocationRequest::to_bytes(self)
    }
    
    fn from_bytes(data: &[u8]) -> WipResult<Self> {
        if data.len() < 16 {
            return Err(WipPacketError::Parse(PacketParseError::insufficient_data(16, data.len())));
        }
        
        let bits_data = bytes_to_u128_le(data);
        let fields = &*REQUEST_FIELDS;
        
        // パケット型チェック
        let packet_type = fields.get_field("type")
            .map(|f| f.extract(bits_data) as u8)
            .unwrap_or(255);
        if packet_type != 0 {
            return Err(WipPacketError::Parse(PacketParseError::invalid_packet_type(packet_type)));
        }
        
        let version = fields.get_field("version")
            .map(|f| f.extract(bits_data) as u8)
            .unwrap_or(1);
        let packet_id = fields.get_field("packet_id")
            .map(|f| f.extract(bits_data) as u16)
            .unwrap_or(0);
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
        let day = fields.get_field("day")
            .map(|f| f.extract(bits_data) as u8)
            .unwrap_or(0);
        let timestamp = fields.get_field("timestamp")
            .map(|f| f.extract(bits_data) as u64)
            .unwrap_or(0);
        
        // 座標データはデフォルト値を使用（実際の座標は拡張フィールドから取得）
        let latitude = 0.0;
        let longitude = 0.0;
        
        Ok(Self {
            version,
            packet_id,
            weather_flag,
            temperature_flag,
            pop_flag,
            alert_flag,
            disaster_flag,
            day,
            timestamp,
            latitude,
            longitude,
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
        &*REQUEST_FIELDS
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
    
    /// エリアコードを取得
    pub fn get_area_code(&self) -> u32 {
        self.area_code
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
        
        // Use BitSlice approach like LocationResponseEx for correct area code extraction
        let bits = BitSlice::<u8, Lsb0>::from_slice(&data[..data.len().min(20)]);
        
        // Extract fields using bit positions (same as LocationResponseEx)
        let version = bits[0..4].load::<u8>();
        let packet_id = bits[4..16].load::<u16>();
        let packet_type = bits[16..19].load::<u8>();
        
        if packet_type != 1 {
            return Err(WipPacketError::Parse(PacketParseError::invalid_packet_type(packet_type)));
        }
        
        // Extract area code from bits 96-115 (20 bits) - ensure we have enough data
        let area_code = if data.len() >= 16 {
            // For 32-byte response, ensure we read from the full packet
            let full_bits = BitSlice::<u8, Lsb0>::from_slice(data);
            full_bits[96..116].load::<u32>()
        } else {
            0
        };
        
        // For LocationResponse, these fields may not be present in the same way
        let success = true; // Assume success for valid response
        let error_code = 0;
        let checksum = if data.len() >= 16 {
            bits[116..128].load::<u16>()
        } else {
            0
        };
        
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
        // Use the same field definitions as response_fields.json
        &*RESPONSE_FIELDS
    }
    
    fn get_checksum_field() -> Option<&'static BitField> {
        Self::get_field_definitions().get_field("checksum")
    }
}

impl AutoChecksumPacket for LocationResponse {}

/// Python互換の拡張レスポンス（拡張フィールド復号を含む）
#[derive(Debug, Clone, PartialEq)]
pub struct LocationResponseEx {
    pub version: u8,
    pub packet_id: u16,
    pub area_code: u32,
    pub latitude: Option<f64>,
    pub longitude: Option<f64>,
    pub source: Option<(String, u16)>,
}

impl LocationResponseEx {
    pub fn from_bytes(data: &[u8]) -> Option<Self> {
        if data.len() < 16 { return None; }

        // ヘッダチェックサム
        if !verify_checksum12(&data[..16], 116, 12) { return None; }

        // 20Bヘッダ（response_fields）/16Bヘッダ（request_fields）の両対応
        let (version, packet_id, packet_type, area_code, header_len) = if data.len() >= 20 {
            let bits = BitSlice::<u8, Lsb0>::from_slice(&data[..20]);
            (bits[0..4].load::<u8>(), bits[4..16].load::<u16>(), bits[16..19].load::<u8>(), bits[96..116].load::<u32>(), 20usize)
        } else {
            let bits = BitSlice::<u8, Lsb0>::from_slice(&data[..16]);
            (bits[0..4].load::<u8>(), bits[4..16].load::<u16>(), bits[16..19].load::<u8>(), bits[96..116].load::<u32>(), 16usize)
        };
        if packet_type != 1 { return None; }

        // 拡張フィールド（任意）: Python準拠の unpack_ext_fields で復号
        let mut latitude: Option<f64> = None;
        let mut longitude: Option<f64> = None;
        let mut source: Option<(String, u16)> = None;
        if data.len() > header_len {
            let map = unpack_ext_fields(&data[header_len..]);
            if let Some(FieldValue::F64(v)) = map.get("latitude") { latitude = Some(*v); }
            if let Some(FieldValue::F64(v)) = map.get("longitude") { longitude = Some(*v); }
            if let Some(FieldValue::String(s)) = map.get("source") {
                if let Some((ip, port)) = parse_source_str(s) { source = Some((ip, port)); }
            }
        }

        Some(Self { version, packet_id, area_code, latitude, longitude, source })
    }

    pub fn get_area_code_str(&self) -> String { format!("{:06}", self.area_code) }
    
    pub fn get_coordinates(&self) -> Option<(f64, f64)> {
        if let (Some(lat), Some(lon)) = (self.latitude, self.longitude) {
            Some((lat, lon))
        } else {
            None
        }
    }
    
    pub fn get_source_info(&self) -> Option<(String, u16)> {
        self.source.clone()
    }
}

fn parse_source_str(s: &str) -> Option<(String, u16)> {
    let parts: Vec<&str> = s.split(':').collect();
    if parts.len() == 2 { if let Ok(port) = parts[1].parse::<u16>() { return Some((parts[0].to_string(), port)); } }
    None
}

#[cfg(test)]
mod tests {
    use super::*;
    use bitvec::prelude::*;
    use crate::wip_common_rs::packet::core::checksum::{verify_checksum12, calc_checksum12};

    #[test]
    fn test_location_request_to_bytes_checksum() {
        let req = LocationRequest::create_coordinate_lookup(
            35.0, 139.0, 0x123, true, true, true, false, false, 0, 1,
        );
        let bytes = req.to_bytes();
        assert!(bytes.len() >= 16);
        
        // デバッグ出力
        println!("Generated full packet bytes ({} bytes): {:02X?}", bytes.len(), &bytes);
        
        // 全パケットでチェックサムの検証（116..128, 12bit）
        let checksum_valid = verify_checksum12(&bytes, 116, 12);
        println!("Checksum validation result: {}", checksum_valid);
        assert!(checksum_valid);
        let head_bits = BitSlice::<u8, Lsb0>::from_slice(&bytes[..16]);
        let ty: u8 = head_bits[16..19].load();
        assert_eq!(ty, 0u8); // Type=0
        // ex_flag should be 1
        let ex_flag: u8 = head_bits[24..25].load();
        assert_eq!(ex_flag, 1);
    }

    #[test]
    fn test_location_response_ex_from_bytes_with_ext() {
        // Build 20-byte header with type=1 and area_code
        let mut bits = bitvec![u8, Lsb0; 0; 160];
        bits[0..4].store(1u8);            // version
        bits[4..16].store(0x123u16);      // packet_id
        bits[16..19].store(1u8);          // type = 1
        bits[96..116].store(11000u32);    // area_code
        // checksum placeholder 116..128
        let mut data = [0u8; 20];
        data.copy_from_slice(bits.as_raw_slice());
        // Compute and embed checksum for header (first 16 bytes)
        let checksum = calc_checksum12(&data[..16]);
        let mut head_bits = bitvec![u8, Lsb0; 0; 128];
        head_bits.copy_from_bitslice(&BitSlice::<u8, Lsb0>::from_slice(&data[..16]));
        head_bits[116..128].store(checksum);
        let mut head = [0u8; 16];
        head.copy_from_slice(head_bits.as_raw_slice());
        data[..16].copy_from_slice(&head);

        // Extended fields: latitude, longitude, source (Python準拠のpackで付加)
        let mut map = std::collections::HashMap::new();
        map.insert("latitude".to_string(), FieldValue::F64(35.0));
        map.insert("longitude".to_string(), FieldValue::F64(139.0));
        map.insert("source".to_string(), FieldValue::String("127.0.0.1:12345".to_string()));
        let ext = pack_ext_fields(&map);

        // Build full packet
        let mut packet = Vec::with_capacity(20 + ext.len());
        packet.extend_from_slice(&data);
        packet.extend_from_slice(&ext);

        let resp = LocationResponseEx::from_bytes(&packet).expect("parse");
        assert_eq!(resp.version, 1);
        assert_eq!(resp.packet_id, 0x123);
        assert_eq!(resp.area_code, 11000);
        assert_eq!(resp.get_area_code_str(), "011000");
        assert_eq!(resp.get_coordinates(), Some((35.0, 139.0)));
        assert_eq!(resp.get_source_info(), Some(("127.0.0.1".to_string(), 12345)));
    }
}
