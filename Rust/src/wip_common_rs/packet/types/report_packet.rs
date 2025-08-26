use crate::wip_common_rs::packet::core::bit_utils::{
    PacketFields,
};
use crate::wip_common_rs::packet::core::checksum::{
    calc_checksum12, verify_checksum12,
};
use crate::wip_common_rs::packet::core::extended_field::{
    pack_ext_fields, unpack_ext_fields, ExtendedFieldManager, FieldDefinition, FieldType,
    FieldValue,
};
use crate::wip_common_rs::packet::core::format_base::JsonPacketSpecLoader;
use bitvec::prelude::*;
use once_cell::sync::Lazy;
use std::collections::HashMap;
use std::time::{SystemTime, UNIX_EPOCH};

static RESPONSE_FIELDS: Lazy<PacketFields> = Lazy::new(|| {
    let json = include_str!("../format_spec/response_fields.json");
    let (fields, _specs) = JsonPacketSpecLoader::load_from_json(json).expect("response spec parse");
    fields
});

#[derive(Debug, Clone)]
pub struct ReportRequest {
    pub version: u8,
    pub packet_id: u16,
    pub weather_flag: bool,
    pub temperature_flag: bool,
    pub pop_flag: bool,
    pub alert_flag: bool,
    pub disaster_flag: bool,
    pub ex_flag: bool,
    pub request_auth: bool,  // 認証フラグ
    pub response_auth: bool, // レスポンス認証フラグ
    pub day: u8,
    pub timestamp: u64,
    pub area_code: u32, // 内部20bit
    pub weather_code: u16,
    pub temperature: u8, // +100 オフセット済み
    pub pop: u8,
    pub ext: Option<ExtendedFieldManager>,
    // 認証関連（内部状態）
    _auth_enabled: bool,
    _auth_passphrase: Option<String>,
}

impl ReportRequest {
    pub fn new_disaster(
        disaster_type: &str,
        severity: u8,
        description: &str,
        latitude: Option<f64>,
        longitude: Option<f64>,
    ) -> Self {
        let mut ext = ExtendedFieldManager::new();
        ext.add_definition(FieldDefinition::new(
            "disaster_type".to_string(),
            FieldType::String,
        ));
        let _ = ext.set_value(
            "disaster_type".to_string(),
            FieldValue::String(disaster_type.to_string()),
        );
        ext.add_definition(FieldDefinition::new("severity".to_string(), FieldType::U8));
        let _ = ext.set_value("severity".to_string(), FieldValue::U8(severity));
        ext.add_definition(FieldDefinition::new(
            "description".to_string(),
            FieldType::String,
        ));
        let _ = ext.set_value(
            "description".to_string(),
            FieldValue::String(description.to_string()),
        );
        if let Some(lat) = latitude {
            ext.add_definition(FieldDefinition::new("latitude".to_string(), FieldType::F64));
            let _ = ext.set_value("latitude".to_string(), FieldValue::F64(lat));
        }
        if let Some(lon) = longitude {
            ext.add_definition(FieldDefinition::new(
                "longitude".to_string(),
                FieldType::F64,
            ));
            let _ = ext.set_value("longitude".to_string(), FieldValue::F64(lon));
        }
        let timestamp = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap()
            .as_secs();
        Self {
            version: 1,
            packet_id: 0,
            weather_flag: false,
            temperature_flag: false,
            pop_flag: false,
            alert_flag: false,
            disaster_flag: true,
            ex_flag: true,
            request_auth: false,
            response_auth: false,
            day: 0,
            timestamp,
            area_code: 0,
            weather_code: 0,
            temperature: 0,
            pop: 0,
            ext: Some(ext),
            _auth_enabled: false,
            _auth_passphrase: None,
        }
    }

    pub fn create_sensor_data_report(
        area_code: &str,
        weather_code: Option<u16>,
        temperature_c: Option<f64>,
        precipitation_prob: Option<u8>,
        alert: Option<Vec<String>>,
        disaster: Option<Vec<String>>,
        version: u8,
        packet_id: u16,
    ) -> Self {
        let normalized = if area_code.len() >= 6 {
            area_code[..6].to_string()
        } else {
            format!("{:0>6}", area_code)
        };
        let area_num = normalized.parse::<u32>().unwrap_or(0) & 0xFFFFF;
        let weather_flag = weather_code.is_some();
        let temperature_flag = temperature_c.is_some();
        let pop_flag = precipitation_prob.is_some();
        let alert_flag = alert.as_ref().map_or(false, |a| !a.is_empty());
        let disaster_flag = disaster.as_ref().map_or(false, |d| !d.is_empty());

        let weather_code_val = weather_code.unwrap_or(0);
        let temp_val = temperature_c.map(|t| (t as i16 + 100) as u8).unwrap_or(100);
        let pop_val = precipitation_prob.unwrap_or(0);

        let mut ext = ExtendedFieldManager::new();
        let mut has_ext = false;
        if let Some(a) = alert {
            if !a.is_empty() {
                ext.add_definition(FieldDefinition::new("alert".to_string(), FieldType::String));
                let joined = a.join(",");
                let _ = ext.set_value("alert".to_string(), FieldValue::String(joined));
                has_ext = true;
            }
        }
        if let Some(d) = disaster {
            if !d.is_empty() {
                ext.add_definition(FieldDefinition::new(
                    "disaster".to_string(),
                    FieldType::String,
                ));
                let joined = d.join(",");
                let _ = ext.set_value("disaster".to_string(), FieldValue::String(joined));
                has_ext = true;
            }
        }

        let timestamp = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap()
            .as_secs();

        Self {
            version,
            packet_id,
            weather_flag,
            temperature_flag,
            pop_flag,
            alert_flag,
            disaster_flag,
            ex_flag: has_ext,
            request_auth: false,  // デフォルトは無効
            response_auth: false, // デフォルトは無効
            day: 0,
            timestamp,
            area_code: area_num,
            weather_code: weather_code_val,
            temperature: temp_val,
            pop: pop_val,
            ext: if has_ext { Some(ext) } else { None },
            _auth_enabled: false,
            _auth_passphrase: None,
        }
    }

    /// Python版と同じ認証機能を有効にする
    pub fn enable_auth(&mut self, passphrase: &str) {
        self._auth_enabled = true;
        self._auth_passphrase = Some(passphrase.to_string());
    }

    /// Python版と同じ認証フラグを設定し、拡張フィールドに認証ハッシュを追加
    pub fn set_auth_flags(&mut self) {
        // 認証が有効でない場合は何もしない
        if !self._auth_enabled {
            return;
        }

        // パスフレーズが設定されていない場合は何もしない
        let passphrase = match &self._auth_passphrase {
            Some(p) => p,
            None => return,
        };

        // 拡張フィールドが存在しない場合は作成
        if self.ext.is_none() {
            self.ext = Some(ExtendedFieldManager::new());
        }

        if let Some(ref mut ext) = self.ext {
            println!("[DEBUG] set_auth_flags()呼び出し:");
            println!("  使用するpacket_id: {}", self.packet_id);
            println!("  使用するtimestamp: {}", self.timestamp);
            println!("  使用するpassphrase: '{}'", passphrase);

            // 認証ハッシュを計算
            use crate::wip_common_rs::utils::auth::WIPAuth;
            let auth_hash_bytes =
                WIPAuth::calculate_auth_hash(self.packet_id, self.timestamp, passphrase);

            // バイト列をhex文字列として保存
            let auth_hash_str = hex::encode(&auth_hash_bytes);
            println!(
                "[DEBUG] 拡張フィールドに設定するauth_hash: {}",
                auth_hash_str
            );

            // auth_hashフィールドを追加
            let field_def = FieldDefinition::new("auth_hash".to_string(), FieldType::String);
            ext.add_definition(field_def);
            let _ = ext.set_value("auth_hash".to_string(), FieldValue::String(auth_hash_str));

            // 拡張フィールドフラグを有効に設定
            self.ex_flag = true;

            // 認証フラグを設定
            self.request_auth = true;

            println!("[DEBUG] 認証フラグ設定完了");
        }
    }

    pub fn to_bytes(&self) -> Vec<u8> {
        // 20バイト固定部（response仕様）
        let mut fixed = [0u8; 20];

        // 全フィールドを先に設定（チェックサム以外）
        {
            let bits = BitSlice::<u8, Lsb0>::from_slice_mut(&mut fixed);
            bits[0..4].store(self.version);
            bits[4..16].store(self.packet_id);
            bits[16..19].store(4u8); // type=4
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
            bits[116..128].store(0u16); // チェックサムは後で設定
                                        // 固定部の後半（weather_code, temperature, pop）
            bits[128..144].store(self.weather_code);
            bits[144..152].store(self.temperature);
            bits[152..160].store(self.pop);
        }

        // まず拡張フィールドを結合してから、全体のチェックサムを計算する
        let mut final_packet = if let Some(ext) = &self.ext {
            let mut map = HashMap::new();

            if let Some(FieldValue::String(s)) = ext.get_value("alert") {
                map.insert("alert".to_string(), FieldValue::String(s.clone()));
            }
            if let Some(FieldValue::String(s)) = ext.get_value("disaster") {
                map.insert("disaster".to_string(), FieldValue::String(s.clone()));
            }
            // 認証ハッシュフィールドも追加
            if let Some(FieldValue::String(s)) = ext.get_value("auth_hash") {
                map.insert("auth_hash".to_string(), FieldValue::String(s.clone()));
            }

            let ext_bytes = pack_ext_fields(&map);
            let mut out = Vec::with_capacity(20 + ext_bytes.len());
            out.extend_from_slice(&fixed);
            out.extend_from_slice(&ext_bytes);
            out
        } else {
            fixed.to_vec()
        };

        // 全体パケットが完成した後にチェックサムを計算
        // Python版と同様に、パケット全体でチェックサムを計算
        // チェックサム位置は116-127ビット（14.5-15.9バイト目）
        use crate::wip_common_rs::packet::core::checksum::embed_checksum12_at;
        embed_checksum12_at(&mut final_packet, 116, 12);

        final_packet
    }

    /// パケットIDを取得
    pub fn get_packet_id(&self) -> u16 {
        self.packet_id
    }

    /// パケットIDを設定
    pub fn set_packet_id(&mut self, id: u16) {
        self.packet_id = id;
    }

    /// バイナリデータを取得
    pub fn get_data(&self) -> &[u8] {
        &[] // ReportRequest doesn't have binary data field in the new structure
    }
}

#[derive(Debug, Clone, PartialEq)]
pub struct ReportResponse {
    pub version: u8,
    pub packet_id: u16,
    pub area_code: u32,
    pub weather_code: Option<u16>,
    pub temperature_c: Option<i8>,
    pub pop: Option<u8>,
    // 受信側での拡張フィールド復号（必要なキーのみ）
    pub alert: Option<Vec<String>>,
    pub disaster: Option<Vec<String>>,
    pub source: Option<String>,
}

impl ReportResponse {
    pub fn from_bytes(data: &[u8]) -> Option<Self> {
        if data.len() < 20 {
            eprintln!("ReportResponse: insufficient length {}", data.len());
            return None;
        }
        // 固定仕様: checksum はヘッダ内の 116..128（12bit）
        // 互換性のため、まずヘッダ16Bで検証し、失敗したら20B、最終的に全体でも試す
        let mut checksum_ok = verify_checksum12(&data[..16], 116, 12);
        if !checksum_ok && data.len() >= 20 {
            checksum_ok = verify_checksum12(&data[..20], 116, 12);
        }
        if !checksum_ok {
            checksum_ok = verify_checksum12(data, 116, 12);
        }
        if !checksum_ok {
            eprintln!("ReportResponse: checksum failed at bits 116..128");
            return None;
        }
        // 固定レイアウトで読み出し（JSON順序の差異に影響されないようにする）
        let bits = BitSlice::<u8, Lsb0>::from_slice(&data[..20]);
        let ty: u8 = bits[16..19].load();
        if ty != 5 {
            eprintln!("ReportResponse: wrong type, expected 5 got {}", ty);
            return None;
        }
        let version: u8 = bits[0..4].load();
        let packet_id: u16 = bits[4..16].load();
        let area_code: u32 = bits[96..116].load();
        let wc: u16 = bits[128..144].load();
        let temp_raw: u8 = bits[144..152].load();
        let pop_raw: u8 = bits[152..160].load();

        let weather_code = if wc != 0 { Some(wc) } else { None };
        let temperature_c = if temp_raw != 0 {
            Some((temp_raw as i16 - 100) as i8)
        } else {
            None
        };
        let pop = if pop_raw != 0 { Some(pop_raw) } else { None };

        // 20バイト以降があれば拡張フィールドをunpack
        let mut alert: Option<Vec<String>> = None;
        let mut disaster: Option<Vec<String>> = None;
        let mut source: Option<String> = None;
        if data.len() > 20 {
            let map = unpack_ext_fields(&data[20..]);
            if let Some(FieldValue::String(s)) = map.get("alert") {
                let v = s
                    .split(',')
                    .filter(|x| !x.is_empty())
                    .map(|x| x.to_string())
                    .collect::<Vec<_>>();
                if !v.is_empty() {
                    alert = Some(v);
                }
            }
            if let Some(FieldValue::String(s)) = map.get("disaster") {
                let v = s
                    .split(',')
                    .filter(|x| !x.is_empty())
                    .map(|x| x.to_string())
                    .collect::<Vec<_>>();
                if !v.is_empty() {
                    disaster = Some(v);
                }
            }
            if let Some(FieldValue::String(s)) = map.get("source") {
                if !s.is_empty() {
                    source = Some(s.clone());
                }
            }
        }

        Some(Self {
            version,
            packet_id,
            area_code,
            weather_code,
            temperature_c,
            pop,
            alert,
            disaster,
            source,
        })
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use bitvec::prelude::*;
    use std::collections::HashMap;

    #[test]
    fn test_report_request_to_bytes_checksum() {
        let req = ReportRequest::create_sensor_data_report(
            "011000",
            Some(10),
            Some(22.0),
            Some(30),
            None,
            None,
            1,
            0x234,
        );
        let bytes = req.to_bytes();
        assert!(bytes.len() >= 20);
        assert!(verify_checksum12(&bytes[..16], 116, 12));
        // Type should be 4
        let head_bits = BitSlice::<u8, Lsb0>::from_slice(&bytes[..16]);
        let ty: u8 = head_bits[16..19].load();
        assert_eq!(ty, 4);
        // Check tail values
        let tail_bits = BitSlice::<u8, Lsb0>::from_slice(&bytes[..20]);
        let weather_code: u16 = tail_bits[128..144].load();
        let temp_raw: u8 = tail_bits[144..152].load();
        let pop: u8 = tail_bits[152..160].load();
        assert_eq!(weather_code, 10);
        assert_eq!(temp_raw, 122); // 22C -> 122
        assert_eq!(pop, 30);
    }

    #[test]
    fn test_report_response_from_bytes() {
        // Build 20-byte response header with type=5 using BitVec directly
        let mut bits = bitvec![u8, Lsb0; 0; 160];
        bits[0..4].store(1u8);
        bits[4..16].store(0x321u16);
        bits[16..19].store(5u8);
        bits[96..116].store(11000u32);
        // checksum placeholder 116..128; tail fields below
        bits[128..144].store(10u16); // weather_code
        bits[144..152].store(122u8); // temperature (+100)
        bits[152..160].store(35u8); // pop
        let mut data = [0u8; 20];
        data.copy_from_slice(bits.as_raw_slice());

        // Compute checksum for header at fixed position and embed
        let checksum = calc_checksum12(&data[..16]);
        let mut head_bits = BitSlice::<u8, Lsb0>::from_slice_mut(&mut data[..16]);
        head_bits[116..128].store(checksum);

        let resp = ReportResponse::from_bytes(&data).expect("parse");
        assert_eq!(resp.version, 1);
        assert_eq!(resp.packet_id, 0x321);
        assert_eq!(resp.area_code, 11000);
        assert_eq!(resp.weather_code, Some(10));
        assert_eq!(resp.temperature_c, Some(22));
        assert_eq!(resp.pop, Some(35));
    }

    #[test]
    fn test_report_response_with_ext_unpack() {
        // Build 20-byte response header with type=5 and then append ext-field bytes
        let mut bits = bitvec![u8, Lsb0; 0; 160];
        bits[0..4].store(1u8);
        bits[4..16].store(0x400u16);
        bits[16..19].store(5u8);
        bits[96..116].store(11000u32);
        // checksum placeholder 116..128; tail fields below
        bits[128..144].store(0u16); // weather_code absent
        bits[144..152].store(0u8); // temp absent
        bits[152..160].store(0u8); // pop absent
        let mut data = [0u8; 20];
        data.copy_from_slice(bits.as_raw_slice());
        // checksum embed in header (first 16 bytes)
        let checksum = calc_checksum12(&data[..16]);
        let mut head_bits = BitSlice::<u8, Lsb0>::from_slice_mut(&mut data[..16]);
        head_bits[116..128].store(checksum);

        // ext-field: alert=A,B , source=1.2.3.4:5 (string)
        let mut map = HashMap::new();
        map.insert("alert".to_string(), FieldValue::String("A,B".into()));
        map.insert("source".to_string(), FieldValue::String("1.2.3.4:5".into()));
        let ext = pack_ext_fields(&map);

        let mut packet = Vec::with_capacity(20 + ext.len());
        packet.extend_from_slice(&data);
        packet.extend_from_slice(&ext);

        let resp = ReportResponse::from_bytes(&packet).expect("parse");
        assert_eq!(resp.version, 1);
        assert_eq!(resp.packet_id, 0x400);
        assert!(resp.weather_code.is_none());
        assert_eq!(resp.alert, Some(vec!["A".to_string(), "B".to_string()]));
        assert_eq!(resp.source, Some("1.2.3.4:5".to_string()));
    }
}
