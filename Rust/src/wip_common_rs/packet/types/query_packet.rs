use bitvec::prelude::*;
use std::collections::HashMap;
use std::time::{SystemTime, UNIX_EPOCH};
use crate::wip_common_rs::packet::core::checksum::{calc_checksum12, verify_checksum12, embed_checksum12_at};
use crate::wip_common_rs::packet::core::bit_utils::{u128_to_bytes_le, PacketFields};
use crate::wip_common_rs::packet::core::format_base::JsonPacketSpecLoader;
use crate::wip_common_rs::packet::core::extended_field::{
    ExtendedFieldManager, FieldDefinition, FieldValue,
    pack_ext_fields, unpack_ext_fields
};
use once_cell::sync::Lazy;

// JSON仕様からフィールド定義を構築（コンパイル時埋め込み）
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

/// Query パケット(Type=2) を表す構造体
/// Python 実装の `QueryRequest.create_query_request` を参考に実装
#[derive(Debug, Clone)]
pub struct QueryRequest {
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
    pub timestamp: u64,
    pub day: u8,
    pub area_code: u32,
    pub ex_field: Option<ExtendedFieldManager>,
}

impl QueryRequest {
    /// QueryRequest を作成する
    pub fn new(
        area_code: u32,
        packet_id: u16,
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
            timestamp,
            day: day & 0x07,
            area_code: area_code & 0xFFFFF,
            ex_field: None,
        }
    }

    /// Test用に固定タイムスタンプでQueryRequestを作成する
    pub fn new_with_timestamp(
        area_code: u32,
        packet_id: u16,
        weather: bool,
        temperature: bool,
        precipitation_prob: bool,
        alert: bool,
        disaster: bool,
        day: u8,
        timestamp: u64,
    ) -> Self {
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
            timestamp,
            day: day & 0x07,
            area_code: area_code & 0xFFFFF,
            ex_field: None,
        }
    }

    /// Python実装に合わせた外部API（エリアコードを6桁文字列で受け取る）
    pub fn create_query_request(
        area_code_str: &str,
        packet_id: u16,
        weather: bool,
        temperature: bool,
        precipitation_prob: bool,
        alert: bool,
        disaster: bool,
        day: u8,
        version: u8,
    ) -> Self {
        let normalized = if area_code_str.len() >= 6 {
            area_code_str[..6].to_string()
        } else {
            format!("{:0>6}", area_code_str)
        };
        let area_num = normalized.parse::<u32>().unwrap_or(0) & 0xFFFFF;
        let mut s = Self::new(
            area_num,
            packet_id,
            weather,
            temperature,
            precipitation_prob,
            alert,
            disaster,
            day,
        );
        s.version = version;
        s
    }

    /// バイト列から QueryRequest を生成する
    pub fn from_bytes(data: &[u8]) -> Option<Self> {
        if data.len() < 16 {
            return None;
        }
        let bits = BitSlice::<u8, Lsb0>::from_slice(&data[..16]);
        let version: u8 = bits[0..4].load();
        let packet_id: u16 = bits[4..16].load();
        let weather_flag = bits[19];
        let temperature_flag = bits[20];
        let pop_flag = bits[21];
        let alert_flag = bits[22];
        let disaster_flag = bits[23];
        let ex_flag = bits[24];
        let day: u8 = bits[27..30].load();
        let timestamp: u64 = bits[32..96].load();
        let area_code: u32 = bits[96..116].load();

        // 拡張フィールド
        let ex_field = if ex_flag && data.len() > 16 {
            let map = unpack_ext_fields(&data[16..]);
            if map.is_empty() {
                None
            } else {
                let mut mgr = ExtendedFieldManager::new();
                for (k, v) in map {
                    let def = FieldDefinition::new(k.clone(), v.get_type());
                    mgr.add_definition(def);
                    let _ = mgr.set_value(k, v);
                }
                Some(mgr)
            }
        } else {
            None
        };

        Some(Self {
            version,
            packet_id,
            weather_flag,
            temperature_flag,
            pop_flag,
            alert_flag,
            disaster_flag,
            ex_flag,
            request_auth: false,
            response_auth: false,
            timestamp,
            day,
            area_code,
            ex_field,
        })
    }

    pub fn get_packet_id(&self) -> u16 {
        self.packet_id
    }

    pub fn set_packet_id(&mut self, id: u16) {
        self.packet_id = id;
    }

    pub fn get_packet_type(&self) -> u8 {
        2  // Query packet type
    }

    /// パケットをバイト列に変換する (Little Endian)
    /// Python実装と互換性を保つため、手動でビットフィールドを配置
    pub fn to_bytes(&self) -> Vec<u8> {
        let mut out = [0u8; 16];
        let mut bits_u128 = 0u128;

        // 正しいビット順序でフィールドを配置（Python実装準拠）
        bits_u128 |= (self.version as u128) & 0x0F;
        bits_u128 |= ((self.packet_id as u128) & 0x0FFF) << 4;
        bits_u128 |= (2u128 & 0x07) << 16;
        
        if self.weather_flag { bits_u128 |= 1u128 << 19; }
        if self.temperature_flag { bits_u128 |= 1u128 << 20; }
        if self.pop_flag { bits_u128 |= 1u128 << 21; }
        if self.alert_flag { bits_u128 |= 1u128 << 22; }
        if self.disaster_flag { bits_u128 |= 1u128 << 23; }
        if self.ex_flag || self.ex_field.is_some() { bits_u128 |= 1u128 << 24; }
        if self.request_auth { bits_u128 |= 1u128 << 25; }
        if self.response_auth { bits_u128 |= 1u128 << 26; }
        
        bits_u128 |= ((self.day as u128) & 0x07) << 27;
        bits_u128 |= (self.timestamp as u128) << 32;
        bits_u128 |= ((self.area_code as u128) & 0xFFFFF) << 96;
        
        u128_to_bytes_le(bits_u128, &mut out);
        let mut packet = out.to_vec();

        if let Some(ext) = &self.ex_field {
            let mut map = HashMap::new();
            for (k, v) in ext.get_all_values() {
                map.insert(k.clone(), v.clone());
            }
            let ext_bytes = pack_ext_fields(&map);
            packet.extend_from_slice(&ext_bytes);
        }

        let checksum = calc_checksum12(&packet);
        bits_u128 |= ((checksum as u128) & 0x0FFF) << 116;
        u128_to_bytes_le(bits_u128, &mut packet[..16]);

        packet
    }
}

/// QueryResponse (Type=3) の実装
#[derive(Debug, Clone)]
pub struct QueryResponse {
    pub version: u8,
    pub packet_id: u16,
    pub area_code: u32,
    pub weather_code: Option<u16>,
    pub temperature: Option<i8>,
    pub precipitation: Option<u8>,
    pub alert_flag: bool,
    pub disaster_flag: bool,
    pub timestamp: u64,
    pub response_auth: bool,
    pub ex_field: Option<ExtendedFieldManager>,
}

impl QueryResponse {
    /// 新規インスタンスを作成
    pub fn new() -> Self {
        Self {
            version: 1,
            packet_id: 0,
            area_code: 0,
            weather_code: None,
            temperature: None,
            precipitation: None,
            alert_flag: false,
            disaster_flag: false,
            timestamp: 0,
            response_auth: false,
            ex_field: None,
        }
    }

    /// 簡易的に成功レスポンスを生成
    pub fn success(packet_id: u16, weather: u16, temperature: i8, pop: u8) -> Self {
        Self {
            version: 1,
            packet_id,
            area_code: 0,
            weather_code: Some(weather),
            temperature: Some(temperature),
            precipitation: Some(pop),
            alert_flag: false,
            disaster_flag: false,
            timestamp: 0,
            response_auth: false,
            ex_field: None,
        }
    }

    /// バイト列から QueryResponse を生成する
    pub fn from_bytes(data: &[u8]) -> Option<Self> {
        if data.len() < 20 {
            eprintln!("DEBUG: QueryResponse::from_bytes - insufficient data length: {}", data.len());
            return None;
        }
        let bits = BitSlice::<u8, Lsb0>::from_slice(&data[..20]);

        // ヘッダ部のチェックサムを検証
        if !verify_checksum12(&data[..16], 116, 12) {
            eprintln!("DEBUG: QueryResponse::from_bytes - checksum verification failed");
            return None;
        }

        let version: u8  = bits[0..4].load();
        let packet_id: u16 = bits[4..16].load();
        let alert_flag_bit = bits[22];
        let disaster_flag_bit = bits[23];
        let ex_flag = bits[24];
        let response_auth = bits[26];
        let timestamp: u64 = bits[32..96].load();
        let area_code: u32 = bits[96..116].load();
        let weather_code: u16 = bits[128..144].load();
        let temp_raw: u8    = bits[144..152].load();
        let precip: u8      = bits[152..160].load();

        // 温度は+100オフセットで格納される仕様（Python実装準拠）
        let temperature = if temp_raw != 0 {
            let val = (temp_raw as i16) - 100;
            Some(val as i8)
        } else {
            None
        };
        let weather_code = if weather_code != 0 {
            Some(weather_code)
        } else {
            None
        };
        let precipitation = if precip != 0 { Some(precip) } else { None };

        // 拡張フィールド
        let ex_field = if ex_flag && data.len() > 20 {
            let map = unpack_ext_fields(&data[20..]);
            if !map.is_empty() {
                let mut mgr = ExtendedFieldManager::new();
                for (k, v) in map {
                    let def = FieldDefinition::new(k.clone(), v.get_type());
                    mgr.add_definition(def);
                    let _ = mgr.set_value(k, v);
                }
                Some(mgr)
            } else {
                None
            }
        } else {
            None
        };

        let alert_flag = alert_flag_bit
            && ex_field
                .as_ref()
                .map_or(false, |ext| ext.get_value("alert").is_some());
        let disaster_flag = disaster_flag_bit
            && ex_field
                .as_ref()
                .map_or(false, |ext| ext.get_value("disaster").is_some());

        Some(Self {
            version,
            packet_id,
            area_code,
            weather_code,
            temperature,
            precipitation,
             alert_flag,
             disaster_flag,
            timestamp,
            response_auth,
            ex_field,
        })
    }

    /// パケットをバイト列に変換する
    pub fn to_bytes(&self) -> Vec<u8> {
        let mut fixed = [0u8; 20];
        {
            let bits = BitSlice::<u8, Lsb0>::from_slice_mut(&mut fixed);
            bits[0..4].store(self.version);
            bits[4..16].store(self.packet_id);
            bits[16..19].store(3u8);
            bits[19..20].store(self.weather_code.is_some() as u8);
            bits[20..21].store(self.temperature.is_some() as u8);
            bits[21..22].store(self.precipitation.is_some() as u8);
            let alert_bit = self.alert_flag || self.get_alert().is_some();
            let disaster_bit = self.disaster_flag || self.get_disaster().is_some();
            bits[22..23].store(alert_bit as u8);
            bits[23..24].store(disaster_bit as u8);
            let has_ext = self.ex_field.is_some();
            bits[24..25].store(has_ext as u8);
            bits[25..26].store(0u8);
            bits[26..27].store(self.response_auth as u8);
            bits[27..30].store(0u8);
            bits[30..32].store(0u8);
            bits[32..96].store(self.timestamp);
            bits[96..116].store(self.area_code);
            bits[116..128].store(0u16);
            bits[128..144].store(self.weather_code.unwrap_or(0));
            let temp_store = self.temperature.map(|t| (t as i16 + 100) as u8).unwrap_or(0);
            bits[144..152].store(temp_store);
            bits[152..160].store(self.precipitation.unwrap_or(0));
        }

        let mut packet = if let Some(ref ext) = self.ex_field {
            let mut map = HashMap::new();
            for (k, v) in ext.get_all_values() {
                map.insert(k.clone(), v.clone());
            }
            let ext_bytes = pack_ext_fields(&map);
            let mut out = Vec::with_capacity(20 + ext_bytes.len());
            out.extend_from_slice(&fixed);
            out.extend_from_slice(&ext_bytes);
            out
        } else {
            fixed.to_vec()
        };

        embed_checksum12_at(&mut packet, 116, 12);
        packet
    }

    /// 拡張フィールドからalertを取得
    pub fn get_alert(&self) -> Option<Vec<String>> {
        if self.alert_flag {
            if let Some(ref ext) = self.ex_field {
                if let Some(FieldValue::String(s)) = ext.get_value("alert") {
                    let v: Vec<String> = s
                        .split(',')
                        .filter(|x| !x.is_empty())
                        .map(|x| x.to_string())
                        .collect();
                    if !v.is_empty() {
                        return Some(v);
                    }
                }
            }
        }
        None
    }

    /// 拡張フィールドからdisasterを取得
    pub fn get_disaster(&self) -> Option<Vec<String>> {
        if self.disaster_flag {
            if let Some(ref ext) = self.ex_field {
                if let Some(FieldValue::String(s)) = ext.get_value("disaster") {
                    let v: Vec<String> = s
                        .split(',')
                        .filter(|x| !x.is_empty())
                        .map(|x| x.to_string())
                        .collect();
                    if !v.is_empty() {
                        return Some(v);
                    }
                }
            }
        }
        None
    }

    /// 拡張フィールドからauth_hashを取得
    pub fn get_auth_hash(&self) -> Option<Vec<u8>> {
        if let Some(ref ext) = self.ex_field {
            if let Some(FieldValue::String(hex_str)) = ext.get_value("auth_hash") {
                if let Ok(bytes) = hex::decode(hex_str) {
                    return Some(bytes);
                }
            }
        }
        None
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::collections::HashMap;

    #[test]
    fn request_to_bytes_length() {
        let req = QueryRequest::new(11000, 1, true, true, true, false, false, 0);
        assert_eq!(req.to_bytes().len(), 16);
    }

    #[test]
    fn response_from_bytes() {
        let mut bits = bitvec![u8, Lsb0; 0; 160];
        bits[0..4].store(1u8);
        bits[4..16].store(1u16);
        bits[16..19].store(3u8);
        bits.set(22, true);
        bits.set(23, true);
        bits[96..116].store(123u32);
        bits[128..144].store(10u16);
        bits[144..152].store(120u8);
        bits[152..160].store(80u8);
        let mut base = [0u8; 20];
        base.copy_from_slice(bits.as_raw_slice());

        // 拡張フィールドを追加
        let mut map = HashMap::new();
        map.insert("alert".to_string(), FieldValue::String("A,B".into()));
        map.insert("disaster".to_string(), FieldValue::String("X".into()));
        let ext = pack_ext_fields(&map);
        let mut packet = Vec::new();
        packet.extend_from_slice(&base);
        packet.extend_from_slice(&ext);

        // ヘッダ部（最初の16バイト）にチェックサムを埋め込む
        let checksum = calc_checksum12(&packet);
        let mut head_bits = BitSlice::<u8, Lsb0>::from_slice_mut(&mut packet[..16]);
        head_bits[116..128].store(checksum);

        let resp = QueryResponse::from_bytes(&packet).unwrap();
        assert_eq!(resp.packet_id, 1);
        assert_eq!(resp.area_code, 123);
        assert_eq!(resp.weather_code, Some(10));
        assert_eq!(resp.temperature, Some(20i8));
        assert_eq!(resp.precipitation, Some(80u8));
        assert!(resp.alert_flag);
        assert!(resp.disaster_flag);
        let ext = resp.ex_field.as_ref().expect("ext");
        assert_eq!(ext.get_value("alert"), Some(&FieldValue::String("A,B".into())));
        assert_eq!(ext.get_value("disaster"), Some(&FieldValue::String("X".into())));

        let encoded = resp.to_bytes();
        let bits2 = BitSlice::<u8, Lsb0>::from_slice(&encoded[..20]);
        assert!(bits2[22]);
        assert!(bits2[23]);
        let resp2 = QueryResponse::from_bytes(&encoded).unwrap();
        assert!(resp2.alert_flag);
        assert!(resp2.disaster_flag);
    }
}
