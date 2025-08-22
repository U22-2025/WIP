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


    /// 12ビットチェックサムを計算する
    fn calc_checksum12(data: &[u8]) -> u16 {
        let mut total = 0u32;
        
        println!("Checksum calculation for {} bytes:", data.len());
        println!("Data: {:02X?}", data);
        
        // 1バイトずつ加算
        for &byte in data {
            total += byte as u32;
        }
        
        println!("Initial total: 0x{:X}", total);
        
        // キャリーを12ビットに折り返し
        while total >> 12 != 0 {
            let carry = total >> 12;
            total = (total & 0xFFF) + carry;
            println!("Carry fold: 0x{:X}", total);
        }
        
        // 1の補数を返す（12ビットマスク）
        let checksum = (!total) & 0xFFF;
        println!("Final checksum: 0x{:X}", checksum);
        
        checksum as u16
    }

    /// パケットをバイト列に変換する (Little Endian)
    pub fn to_bytes(&self) -> [u8; 16] {
        println!("Creating packet with ID: {} (0x{:03X})", self.packet_id, self.packet_id);
        
        let mut bits = bitvec![u8, Lsb0; 0; 128];

        // 16バイト (128bit) パケット用フィールド配置
        bits[0..4].store(self.version);                    // version (4bit) -> 0-3
        bits[4..16].store(self.packet_id);                 // packet_id (12bit) -> 4-15
        bits[16..19].store(2u8);                           // type=2 (3bit) -> 16-18
        bits[19..20].store(self.weather_flag as u8);       // weather_flag (1bit) -> 19
        bits[20..21].store(self.temperature_flag as u8);   // temperature_flag (1bit) -> 20
        bits[21..22].store(self.pop_flag as u8);           // pop_flag (1bit) -> 21
        bits[22..23].store(self.alert_flag as u8);         // alert_flag (1bit) -> 22
        bits[23..24].store(self.disaster_flag as u8);      // disaster_flag (1bit) -> 23
        bits[24..25].store(self.ex_flag as u8);            // ex_flag (1bit) -> 24
        bits[25..26].store(0u8);                           // request_auth (1bit) -> 25
        bits[26..27].store(0u8);                           // response_auth (1bit) -> 26
        bits[27..30].store(self.day);                      // day (3bit) -> 27-29
        bits[30..32].store(0u8);                           // reserved (2bit) -> 30-31
        bits[32..96].store(self.timestamp);                // timestamp (64bit) -> 32-95
        bits[96..116].store(self.area_code);               // area_code (20bit) -> 96-115  
        bits[116..128].store(0u16);                        // checksum (12bit) -> 116-127

        let mut out = [0u8; 16];
        out.copy_from_slice(bits.as_raw_slice());
        
        // チェックサム部分を0にしたデータでチェックサムを計算
        let checksum = Self::calc_checksum12(&out);
        
        // 計算されたチェックサムを設定
        let mut bits = bitvec![u8, Lsb0; 0; 128];
        bits.copy_from_bitslice(&BitSlice::<u8, Lsb0>::from_slice(&out));
        bits[116..128].store(checksum);  // チェックサム位置 (16バイト用)
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

        println!("Parsing response packet: {:02X?}", &data[..20]);

        // レスポンス仕様に基づくフィールド位置 (20バイト/160bit)
        let version: u8 = bits[0..4].load();                      // version (4bit) -> 0-3
        let packet_id: u16 = bits[4..16].load();                  // packet_id (12bit) -> 4-15
        // type (3bit) -> 16-18
        // flags (8bit) -> 19-26  
        // day (3bit) -> 27-29
        // reserved (2bit) -> 30-31
        // timestamp (64bit) -> 32-95
        let area_code: u32 = bits[96..116].load();                // area_code (20bit) -> 96-115
        // checksum (12bit) -> 116-127
        let weather_code: u16 = bits[128..144].load();            // weather_code (16bit) -> 128-143
        let temp_raw: u8 = bits[144..152].load();                 // temperature (8bit) -> 144-151
        let precip: u8 = bits[152..160].load();                   // precipitation (8bit) -> 152-159

        println!("Parsed: version={}, packet_id={}, area_code={}, weather_code={}, temp={}, precip={}", 
                version, packet_id, area_code, weather_code, temp_raw, precip);

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
        bits[104..124].store(123u32);
        bits[124..140].store(10u16);
        bits[140..148].store(120u8);
        bits[148..156].store(80u8);
        let mut data = [0u8; 20];
        data.copy_from_slice(bits.as_raw_slice());
        let resp = QueryResponse::from_bytes(&data).unwrap();
        assert_eq!(resp.packet_id, 1);
        assert_eq!(resp.area_code, 123);
        assert_eq!(resp.weather_code, Some(10));
        assert_eq!(resp.temperature, Some(120i8));
        assert_eq!(resp.precipitation, Some(80u8));
    }
}
