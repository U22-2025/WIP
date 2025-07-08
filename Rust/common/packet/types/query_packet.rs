use bitvec::prelude::*;
use std::time::{SystemTime, UNIX_EPOCH};

/// Query パケット(Type=2) を表す簡易構造体
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
    pub timestamp: u64,
    pub day: u8,
    pub area_code: u32,
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
            timestamp,
            day: day & 0x07,
            area_code: area_code & 0xFFFFF,
        }
    }

    fn flags_bits(&self) -> u8 {
        (self.weather_flag as u8) << 0
            | (self.temperature_flag as u8) << 1
            | (self.pop_flag as u8) << 2
            | (self.alert_flag as u8) << 3
            | (self.disaster_flag as u8) << 4
            | (self.ex_flag as u8) << 5
    }

    /// パケットをバイト列に変換する (Little Endian)
    pub fn to_bytes(&self) -> [u8; 20] {
        let mut bits = bitvec![u8, Lsb0; 0; 160];

        // フィールド配置
        bits[0..4].store(self.version);
        bits[4..16].store(self.packet_id);
        bits[16..19].store(2u8); // type=2
        bits[19..25].store(self.flags_bits());
        bits[25..89].store(self.timestamp);
        // checksum はここでは計算しないため 0
        bits[89..101].store(0u16);
        bits[101..104].store(self.day);
        bits[104..124].store(self.area_code);
        bits[124..140].store(0u16); // weather_code (unused in request)
        bits[140..148].store(0u8); // temperature
        bits[148..156].store(0u8); // precipitation
        bits[156..160].store(0u8); // reserved

        let mut out = [0u8; 20];
        out.copy_from_slice(bits.as_raw_slice());
        out
    }
}

/// QueryResponse (Type=3) の最小実装
#[derive(Debug, Clone)]
pub struct QueryResponse {
    pub version: u8,
    pub packet_id: u16,
    pub area_code: u32,
    pub weather_code: Option<u16>,
    pub temperature: Option<i8>,
    pub precipitation: Option<u8>,
}

impl QueryResponse {
    /// バイト列から QueryResponse を生成する
    pub fn from_bytes(data: &[u8]) -> Option<Self> {
        if data.len() < 20 {
            return None;
        }
        let bits = BitSlice::<u8, Lsb0>::from_slice(&data[..20]);

        let version: u8 = bits[0..4].load();
        let packet_id: u16 = bits[4..16].load();
        let area_code: u32 = bits[104..124].load();
        let weather_code: u16 = bits[124..140].load();
        let temp_raw: u8 = bits[140..148].load();
        let precip: u8 = bits[148..156].load();

        let temperature = if temp_raw != 0 {
            Some(temp_raw as i8)
        } else {
            None
        };
        let weather_code = if weather_code != 0 {
            Some(weather_code)
        } else {
            None
        };
        let precipitation = if precip != 0 { Some(precip) } else { None };

        Some(Self {
            version,
            packet_id,
            area_code,
            weather_code,
            temperature,
            precipitation,
        })
    }
}
