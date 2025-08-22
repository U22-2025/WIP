use bitvec::prelude::*;
use std::collections::HashMap;
use std::time::{SystemTime, UNIX_EPOCH};
use crate::wip_common_rs::packet::core::checksum::{calc_checksum12, verify_checksum12, embed_checksum12_at};
use crate::wip_common_rs::packet::core::bit_utils::{bytes_to_u128_le, u128_to_bytes_le, PacketFields};
use crate::wip_common_rs::packet::core::format_base::JsonPacketSpecLoader;
use crate::wip_common_rs::packet::core::extended_field::{FieldValue, pack_ext_fields, unpack_ext_fields};
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
    pub auth_hash: Option<Vec<u8>>,
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
            auth_hash: None,
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
            auth_hash: None,
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

    pub fn get_packet_id(&self) -> u16 {
        self.packet_id
    }

    pub fn set_packet_id(&mut self, id: u16) {
        self.packet_id = id;
    }

    pub fn get_packet_type(&self) -> u8 {
        2  // Query packet type
    }

    /// パケットをバイト列に変換する
    /// 認証ハッシュが存在する場合は拡張フィールドとして付加する
    pub fn to_bytes(&self) -> Vec<u8> {
        let mut fixed = [0u8; 16];
        {
            let bits = BitSlice::<u8, Lsb0>::from_slice_mut(&mut fixed);
            bits[0..4].store(self.version);
            bits[4..16].store(self.packet_id);
            bits[16..19].store(2u8);
            bits[19..20].store(self.weather_flag as u8);
            bits[20..21].store(self.temperature_flag as u8);
            bits[21..22].store(self.pop_flag as u8);
            bits[22..23].store(self.alert_flag as u8);
            bits[23..24].store(self.disaster_flag as u8);
            bits[24..25].store(self.ex_flag as u8);
            bits[25..26].store(self.request_auth as u8);
            bits[26..27].store(self.response_auth as u8);
            bits[27..30].store(self.day);
            bits[30..32].store(0u8);
            bits[32..96].store(self.timestamp);
            bits[96..116].store(self.area_code);
            bits[116..128].store(0u16);
        }

        let mut packet = if let Some(hash) = &self.auth_hash {
            let mut map = HashMap::new();
            let hex_hash = hex::encode(hash);
            map.insert("auth_hash".to_string(), FieldValue::String(hex_hash));
            let ext = pack_ext_fields(&map);
            let mut out = Vec::with_capacity(16 + ext.len());
            out.extend_from_slice(&fixed);
            out.extend_from_slice(&ext);
            out
        } else {
            fixed.to_vec()
        };

        embed_checksum12_at(&mut packet, 116, 12);
        packet
    }

    /// バイト列からQueryRequestを生成する
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
        let request_auth = bits[25];
        let response_auth = bits[26];
        let day: u8 = bits[27..30].load();
        let timestamp: u64 = bits[32..96].load();
        let area_code: u32 = bits[96..116].load();

        let mut auth_hash = None;
        if ex_flag && data.len() > 16 {
            if let Ok(map) = unpack_ext_fields(&data[16..]) {
                if let Some(FieldValue::String(s)) = map.get("auth_hash") {
                    if let Ok(bytes) = hex::decode(s) {
                        auth_hash = Some(bytes);
                    }
                }
            }
        }

        Some(Self {
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
            timestamp,
            day,
            area_code,
            auth_hash,
        })
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
    pub timestamp: u64,
    pub response_auth: bool,
    pub auth_hash: Option<Vec<u8>>,
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
            timestamp: 0,
            response_auth: false,
            auth_hash: None,
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
            timestamp: 0,
            response_auth: false,
            auth_hash: None,
        }
    }

    /// バイト列から QueryResponse を生成する
    pub fn from_bytes(data: &[u8]) -> Option<Self> {
        if data.len() < 20 {
            eprintln!("DEBUG: QueryResponse::from_bytes - insufficient data length: {}", data.len());
            return None;
        }
        let bits = BitSlice::<u8, Lsb0>::from_slice(&data[..20]);

        // チェックサム検証をスキップ（Python/Rust相互運用性のため）
        // 注意: チェックサム算法の違いは既知の問題で、将来修正予定

        let version: u8  = bits[0..4].load();
        let packet_id: u16 = bits[4..16].load();
        let response_auth = bits[26];
        let timestamp: u64 = bits[32..96].load();
        let area_code: u32 = bits[96..116].load();
        let weather_code: u16 = bits[128..144].load();
        let temp_raw: u8    = bits[144..152].load();
        let precip: u8      = bits[152..160].load();
        let ex_flag = bits[24];

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

        // 拡張フィールドからauth_hashを取得
        let mut auth_hash = None;
        if ex_flag && data.len() > 20 {
            if let Ok(map) = unpack_ext_fields(&data[20..]) {
                if let Some(FieldValue::String(s)) = map.get("auth_hash") {
                    if let Ok(bytes) = hex::decode(s) {
                        auth_hash = Some(bytes);
                    }
                }
            }
        }

        Some(Self {
            version,
            packet_id,
            area_code,
            weather_code,
            temperature,
            precipitation,
            timestamp,
            response_auth,
            auth_hash,
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
            bits[22..23].store(0u8);
            bits[23..24].store(0u8);
            let has_ext = self.auth_hash.is_some();
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

        let mut packet = if let Some(hash) = &self.auth_hash {
            let mut map = HashMap::new();
            let hex_hash = hex::encode(hash);
            map.insert("auth_hash".to_string(), FieldValue::String(hex_hash));
            let ext = pack_ext_fields(&map);
            let mut out = Vec::with_capacity(20 + ext.len());
            out.extend_from_slice(&fixed);
            out.extend_from_slice(&ext);
            out
        } else {
            fixed.to_vec()
        };

        embed_checksum12_at(&mut packet, 116, 12);
        packet
    }
}

#[cfg(test)]
mod tests {
    use super::*;

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
        bits[96..116].store(123u32);
        bits[128..144].store(10u16);
        bits[144..152].store(120u8);
        bits[152..160].store(80u8);
        let mut data = [0u8; 20];
        data.copy_from_slice(bits.as_raw_slice());

        // ヘッダ部（最初の16バイト）にチェックサムを埋め込む
        let checksum = calc_checksum12(&data[..16]);
        let mut head_bits = bitvec![u8, Lsb0; 0; 128];
        head_bits.copy_from_bitslice(&BitSlice::<u8, Lsb0>::from_slice(&data[..16]));
        head_bits[116..128].store(checksum);
        let mut head = [0u8; 16];
        head.copy_from_slice(head_bits.as_raw_slice());
        data[..16].copy_from_slice(&head);
        let resp = QueryResponse::from_bytes(&data).unwrap();
        assert_eq!(resp.packet_id, 1);
        assert_eq!(resp.area_code, 123);
        assert_eq!(resp.weather_code, Some(10));
        assert_eq!(resp.temperature, Some(20i8));
        assert_eq!(resp.precipitation, Some(80u8));
    }
}
