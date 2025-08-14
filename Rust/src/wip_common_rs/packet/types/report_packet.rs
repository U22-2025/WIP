/// ReportRequest/ReportResponse パケット実装
/// Python版 report_packet.py と同等の機能
/// IoT機器データ収集専用パケット

use crate::wip_common_rs::packet::core::{
    PacketFormat, AutoChecksumPacket, WipResult, WipPacketError, PacketParseError,
    BitField, PacketFields, bytes_to_u128_le, u128_to_bytes_le
};
use std::time::{SystemTime, UNIX_EPOCH};
use std::collections::HashMap;

/// ReportRequest パケット (Type=4)
/// IoT機器からサーバーへのセンサーデータプッシュ配信
#[derive(Debug, Clone, PartialEq)]
pub struct ReportRequest {
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
    pub area_code: String,
    pub weather_code: u16,
    pub temperature: u16, // 内部表現（摂氏+100）
    pub precipitation_prob: u8,
    pub checksum: u16,
    pub binary_data: Option<Vec<u8>>, // バイナリデータ
    pub extended_fields: Option<HashMap<String, String>>, // 拡張フィールド
}

impl ReportRequest {
    /// センサーデータレポートリクエストを作成（Type 4）
    pub fn create_sensor_data_report(
        area_code: &str,
        weather_code: Option<u16>,
        temperature: Option<f64>,
        precipitation_prob: Option<u8>,
        alert: Option<Vec<String>>,
        disaster: Option<Vec<String>>,
        version: u8,
    ) -> Self {
        use crate::wip_common_rs::clients::utils::packet_id_generator::PacketIdGenerator;
        
        // パケットIDを自動生成
        let packet_id = PacketIdGenerator::next_id();
        
        // エリアコードを6桁の文字列に正規化
        let area_code_str = if area_code.len() >= 6 {
            area_code.to_string()
        } else {
            format!("{:0>6}", area_code)
        };

        // フラグの設定（データが提供されている場合のみ有効にする）
        let weather_flag = weather_code.is_some();
        let temperature_flag = temperature.is_some();
        let pop_flag = precipitation_prob.is_some();
        let alert_flag = alert.as_ref().map_or(false, |a| !a.is_empty());
        let disaster_flag = disaster.as_ref().map_or(false, |d| !d.is_empty());

        // 固定長フィールドの値を設定
        let weather_code_value = weather_code.unwrap_or(0);
        // 気温は摂氏から内部表現（+100）に変換
        let temperature_value = temperature
            .map(|t| (t as i32 + 100) as u16)
            .unwrap_or(100); // 0℃相当
        let pop_value = precipitation_prob.unwrap_or(0);

        // 拡張フィールドの準備
        let mut extended_fields = HashMap::new();
        if let Some(alert_data) = alert {
            if !alert_data.is_empty() {
                extended_fields.insert("alert".to_string(), alert_data.join(","));
            }
        }
        if let Some(disaster_data) = disaster {
            if !disaster_data.is_empty() {
                extended_fields.insert("disaster".to_string(), disaster_data.join(","));
            }
        }

        let ex_flag = !extended_fields.is_empty();
        let extended = if ex_flag { Some(extended_fields) } else { None };

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
            ex_flag,
            request_auth: false,
            response_auth: false,
            day: 0, // リアルタイムデータ
            timestamp,
            area_code: area_code_str,
            weather_code: weather_code_value,
            temperature: temperature_value,
            precipitation_prob: pop_value,
            checksum: 0,
            binary_data: None,
            extended_fields: extended,
        }
    }

    /// 新しいReportRequestを作成（汎用）
    pub fn new(
        packet_id: u16,
        area_code: &str,
        weather_code: u16,
        temperature: u16,
        precipitation_prob: u8,
        weather_flag: bool,
        temperature_flag: bool,
        pop_flag: bool,
        alert_flag: bool,
        disaster_flag: bool,
    ) -> Self {
        let timestamp = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap()
            .as_secs();

        Self {
            version: 1,
            packet_id,
            weather_flag,
            temperature_flag,
            pop_flag,
            alert_flag,
            disaster_flag,
            ex_flag: false,
            request_auth: false,
            response_auth: false,
            day: 0,
            timestamp,
            area_code: area_code.to_string(),
            weather_code,
            temperature,
            precipitation_prob,
            checksum: 0,
            binary_data: None,
            extended_fields: None,
        }
    }

    /// バイナリデータを設定
    pub fn set_binary_data(&mut self, data: Vec<u8>) {
        self.binary_data = Some(data);
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

    /// 温度を摂氏で取得
    pub fn get_temperature_celsius(&self) -> f64 {
        (self.temperature as i32 - 100) as f64
    }
}

impl PacketFormat for ReportRequest {
    fn to_bytes(&self) -> Vec<u8> {
        // 基本的には24バイト + バイナリデータサイズ
        let base_size = 24;
        let binary_size = self.binary_data.as_ref().map_or(0, |d| d.len());
        let total_size = base_size + binary_size;
        
        let mut data = vec![0u8; total_size];
        let mut bits_data = bytes_to_u128_le(&data[..base_size]);
        
        let fields = Self::get_field_definitions();
        
        // フィールドを設定
        if let Some(field) = fields.get_field("version") {
            field.set(&mut bits_data, self.version as u128);
        }
        if let Some(field) = fields.get_field("packet_id") {
            field.set(&mut bits_data, self.packet_id as u128);
        }
        if let Some(field) = fields.get_field("type") {
            field.set(&mut bits_data, 4u128); // Type = 4 for ReportRequest
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
        if let Some(field) = fields.get_field("weather_code") {
            field.set(&mut bits_data, self.weather_code as u128);
        }
        if let Some(field) = fields.get_field("temperature") {
            field.set(&mut bits_data, self.temperature as u128);
        }
        if let Some(field) = fields.get_field("precipitation_prob") {
            field.set(&mut bits_data, self.precipitation_prob as u128);
        }
        
        u128_to_bytes_le(bits_data, &mut data[..base_size]);
        
        // バイナリデータを追加
        if let Some(binary) = &self.binary_data {
            data[base_size..].copy_from_slice(binary);
        }
        
        data
    }
    
    fn from_bytes(data: &[u8]) -> WipResult<Self> {
        if data.len() < 24 {
            return Err(WipPacketError::Parse(PacketParseError::insufficient_data(24, data.len())));
        }
        
        let bits_data = bytes_to_u128_le(&data[..24]);
        let fields = Self::get_field_definitions();
        
        // パケット型チェック
        let packet_type = fields.get_field("type")
            .map(|f| f.extract(bits_data) as u8)
            .unwrap_or(255);
        if packet_type != 4 {
            return Err(WipPacketError::Parse(PacketParseError::invalid_packet_type(packet_type)));
        }
        
        // フィールドから値を抽出
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
        let weather_code = fields.get_field("weather_code")
            .map(|f| f.extract(bits_data) as u16)
            .unwrap_or(0);
        let temperature = fields.get_field("temperature")
            .map(|f| f.extract(bits_data) as u16)
            .unwrap_or(100);
        let precipitation_prob = fields.get_field("precipitation_prob")
            .map(|f| f.extract(bits_data) as u8)
            .unwrap_or(0);
        let checksum = fields.get_field("checksum")
            .map(|f| f.extract(bits_data) as u16)
            .unwrap_or(0);
        
        // バイナリデータを抽出
        let binary_data = if data.len() > 24 {
            Some(data[24..].to_vec())
        } else {
            None
        };
        
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
            area_code: "000000".to_string(), // デフォルト値、実際の値は拡張フィールドから
            weather_code,
            temperature,
            precipitation_prob,
            checksum,
            binary_data,
            extended_fields: None,
        })
    }
    
    fn packet_size() -> usize {
        24 // ReportRequest の基本サイズは24バイト
    }
    
    fn packet_type() -> u8 {
        4 // ReportRequest のタイプ
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
            fields.add_field("weather_code", 16);
            fields.add_field("temperature", 16);
            fields.add_field("precipitation_prob", 8);
            fields.add_field("checksum", 12);
            fields
        })
    }
    
    fn get_checksum_field() -> Option<&'static BitField> {
        Self::get_field_definitions().get_field("checksum")
    }
}

impl AutoChecksumPacket for ReportRequest {}

/// ReportResponse パケット (Type=5)
/// IoT機器へのACK専用
#[derive(Debug, Clone, PartialEq)]
pub struct ReportResponse {
    pub version: u8,
    pub packet_id: u16,
    pub weather_flag: bool,
    pub temperature_flag: bool,
    pub pop_flag: bool,
    pub alert_flag: bool,
    pub disaster_flag: bool,
    pub ex_flag: bool,
    pub day: u8,
    pub timestamp: u64,
    pub area_code: String,
    pub weather_code: u16,
    pub temperature: u16,
    pub precipitation_prob: u8,
    pub checksum: u16,
    pub extended_fields: Option<HashMap<String, String>>,
}

impl ReportResponse {
    /// ACKレスポンスを作成（Type 5）
    pub fn create_ack_response(request: &ReportRequest, version: u8) -> Self {
        let timestamp = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap()
            .as_secs();

        // 送信元情報を保持（ルーティング用）
        let extended_fields = request.get_source_info()
            .map(|(ip, port)| {
                let mut fields = HashMap::new();
                fields.insert("source".to_string(), format!("{}:{}", ip, port));
                fields
            });

        let ex_flag = extended_fields.is_some();

        Self {
            version,
            packet_id: request.packet_id,
            weather_flag: request.weather_flag,
            temperature_flag: request.temperature_flag,
            pop_flag: request.pop_flag,
            alert_flag: request.alert_flag,
            disaster_flag: request.disaster_flag,
            ex_flag,
            day: request.day,
            timestamp,
            area_code: request.area_code.clone(),
            weather_code: 0, // レスポンスデータは通常空
            temperature: 100, // 0℃相当（デフォルト値）
            precipitation_prob: 0,
            checksum: 0,
            extended_fields,
        }
    }

    /// データ付きレスポンスを作成（Type 5）
    pub fn create_data_response(
        request: &ReportRequest,
        sensor_data: &HashMap<String, String>,
        version: u8,
    ) -> Self {
        let timestamp = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap()
            .as_secs();

        // 送信元情報を保持
        let mut extended_fields = request.get_source_info()
            .map(|(ip, port)| {
                let mut fields = HashMap::new();
                fields.insert("source".to_string(), format!("{}:{}", ip, port));
                fields
            })
            .unwrap_or_else(HashMap::new);

        // センサーデータを設定
        let weather_code = if request.weather_flag {
            sensor_data.get("weather_code")
                .and_then(|s| s.parse().ok())
                .unwrap_or(0)
        } else { 0 };

        let temperature = if request.temperature_flag {
            sensor_data.get("temperature")
                .and_then(|s| s.parse::<f64>().ok())
                .map(|t| (t as i32 + 100) as u16)
                .unwrap_or(100)
        } else { 100 };

        let precipitation_prob = if request.pop_flag {
            sensor_data.get("precipitation_prob")
                .and_then(|s| s.parse().ok())
                .unwrap_or(0)
        } else { 0 };

        // 警報・災害情報を拡張フィールドに追加
        if request.alert_flag {
            if let Some(alert_data) = sensor_data.get("alert") {
                extended_fields.insert("alert".to_string(), alert_data.clone());
            }
        }

        if request.disaster_flag {
            if let Some(disaster_data) = sensor_data.get("disaster") {
                extended_fields.insert("disaster".to_string(), disaster_data.clone());
            }
        }

        let ex_flag = !extended_fields.is_empty();
        let extended = if ex_flag { Some(extended_fields) } else { None };

        Self {
            version,
            packet_id: request.packet_id,
            weather_flag: request.weather_flag,
            temperature_flag: request.temperature_flag,
            pop_flag: request.pop_flag,
            alert_flag: request.alert_flag,
            disaster_flag: request.disaster_flag,
            ex_flag,
            day: request.day,
            timestamp,
            area_code: request.area_code.clone(),
            weather_code,
            temperature,
            precipitation_prob,
            checksum: 0,
            extended_fields: extended,
        }
    }

    /// 送信元情報を取得（ルーティング用）
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

    /// レスポンスが成功かどうかを判定
    pub fn is_success(&self) -> bool {
        // Type 5であればエラーパケットとは別なので常に成功
        true
    }

    /// レスポンスの要約情報を取得
    pub fn get_response_summary(&self) -> HashMap<String, String> {
        let mut summary = HashMap::new();
        summary.insert("type".to_string(), "report_response".to_string());
        summary.insert("success".to_string(), "true".to_string());
        summary.insert("area_code".to_string(), self.area_code.clone());
        summary.insert("packet_id".to_string(), self.packet_id.to_string());
        if let Some((ip, port)) = self.get_source_info() {
            summary.insert("source".to_string(), format!("{}:{}", ip, port));
        }
        summary
    }

    /// 温度を摂氏で取得
    pub fn get_temperature_celsius(&self) -> f64 {
        (self.temperature as i32 - 100) as f64
    }
}

impl PacketFormat for ReportResponse {
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
            field.set(&mut bits_data, 5u128); // Type = 5 for ReportResponse
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
        if let Some(field) = fields.get_field("day") {
            field.set(&mut bits_data, self.day as u128);
        }
        if let Some(field) = fields.get_field("timestamp") {
            field.set(&mut bits_data, self.timestamp as u128);
        }
        if let Some(field) = fields.get_field("weather_code") {
            field.set(&mut bits_data, self.weather_code as u128);
        }
        if let Some(field) = fields.get_field("temperature") {
            field.set(&mut bits_data, self.temperature as u128);
        }
        if let Some(field) = fields.get_field("precipitation_prob") {
            field.set(&mut bits_data, self.precipitation_prob as u128);
        }
        
        u128_to_bytes_le(bits_data, &mut data);
        data.to_vec()
    }
    
    fn from_bytes(data: &[u8]) -> WipResult<Self> {
        if data.len() < 24 {
            return Err(WipPacketError::Parse(PacketParseError::insufficient_data(24, data.len())));
        }
        
        let bits_data = bytes_to_u128_le(data);
        let fields = Self::get_field_definitions();
        
        // パケット型チェック
        let packet_type = fields.get_field("type")
            .map(|f| f.extract(bits_data) as u8)
            .unwrap_or(255);
        if packet_type != 5 {
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
        let ex_flag = fields.get_field("ex_flag")
            .map(|f| f.extract(bits_data) != 0)
            .unwrap_or(false);
        let day = fields.get_field("day")
            .map(|f| f.extract(bits_data) as u8)
            .unwrap_or(0);
        let timestamp = fields.get_field("timestamp")
            .map(|f| f.extract(bits_data) as u64)
            .unwrap_or(0);
        let weather_code = fields.get_field("weather_code")
            .map(|f| f.extract(bits_data) as u16)
            .unwrap_or(0);
        let temperature = fields.get_field("temperature")
            .map(|f| f.extract(bits_data) as u16)
            .unwrap_or(100);
        let precipitation_prob = fields.get_field("precipitation_prob")
            .map(|f| f.extract(bits_data) as u8)
            .unwrap_or(0);
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
            day,
            timestamp,
            area_code: "000000".to_string(), // デフォルト値
            weather_code,
            temperature,
            precipitation_prob,
            checksum,
            extended_fields: None,
        })
    }
    
    fn packet_size() -> usize {
        24 // ReportResponse は24バイト
    }
    
    fn packet_type() -> u8 {
        5 // ReportResponse のタイプ
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
            fields.add_field("weather_code", 16);
            fields.add_field("temperature", 16);
            fields.add_field("precipitation_prob", 8);
            fields.add_field("checksum", 12);
            fields
        })
    }
    
    fn get_checksum_field() -> Option<&'static BitField> {
        Self::get_field_definitions().get_field("checksum")
    }
}

impl AutoChecksumPacket for ReportResponse {}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_report_request_creation() {
        let req = ReportRequest::create_sensor_data_report(
            "011000",
            Some(100),
            Some(25.5),
            Some(30),
            Some(vec!["風警報".to_string()]),
            None,
            1,
        );
        
        assert_eq!(req.version, 1);
        assert_eq!(req.area_code, "011000");
        assert_eq!(req.weather_code, 100);
        assert_eq!(req.get_temperature_celsius(), 25.0); // 内部表現から変換
        assert_eq!(req.precipitation_prob, 30);
        assert!(req.weather_flag);
        assert!(req.temperature_flag);
        assert!(req.pop_flag);
        assert!(req.alert_flag);
        assert!(!req.disaster_flag);
        assert!(req.ex_flag); // 拡張フィールドありのため
    }

    #[test]
    fn test_report_request_bytes_conversion() {
        let req = ReportRequest::new(
            123, "013101", 200, 125, 50, 
            true, true, true, false, false
        );
        
        let bytes = req.to_bytes();
        assert_eq!(bytes.len(), 24);
        
        let parsed = ReportRequest::from_bytes(&bytes).unwrap();
        assert_eq!(parsed.packet_id, req.packet_id);
        assert_eq!(parsed.weather_code, req.weather_code);
        assert_eq!(parsed.temperature, req.temperature);
        assert_eq!(parsed.precipitation_prob, req.precipitation_prob);
        assert_eq!(parsed.weather_flag, req.weather_flag);
    }

    #[test]
    fn test_report_response_ack_creation() {
        let req = ReportRequest::new(
            456, "014000", 300, 110, 20,
            true, true, true, false, false
        );
        
        let resp = ReportResponse::create_ack_response(&req, 1);
        
        assert_eq!(resp.version, 1);
        assert_eq!(resp.packet_id, req.packet_id);
        assert_eq!(resp.area_code, req.area_code);
        assert_eq!(resp.weather_flag, req.weather_flag);
        assert!(resp.is_success());
        
        // ACKレスポンスではデータは空
        assert_eq!(resp.weather_code, 0);
        assert_eq!(resp.temperature, 100); // 0℃相当
        assert_eq!(resp.precipitation_prob, 0);
    }

    #[test]
    fn test_report_response_data_creation() {
        let req = ReportRequest::new(
            789, "015000", 100, 120, 40,
            true, true, true, false, false
        );
        
        let mut sensor_data = HashMap::new();
        sensor_data.insert("weather_code".to_string(), "400".to_string());
        sensor_data.insert("temperature".to_string(), "18.5".to_string());
        sensor_data.insert("precipitation_prob".to_string(), "60".to_string());
        
        let resp = ReportResponse::create_data_response(&req, &sensor_data, 1);
        
        assert_eq!(resp.packet_id, req.packet_id);
        assert_eq!(resp.weather_code, 400);
        assert_eq!(resp.get_temperature_celsius(), 18.0); // 内部表現から変換
        assert_eq!(resp.precipitation_prob, 60);
        assert!(resp.is_success());
    }

    #[test]
    fn test_report_response_bytes_conversion() {
        let req = ReportRequest::new(
            999, "016000", 500, 105, 80,
            true, true, true, false, false
        );
        let resp = ReportResponse::create_ack_response(&req, 1);
        
        let bytes = resp.to_bytes();
        assert_eq!(bytes.len(), 24);
        
        let parsed = ReportResponse::from_bytes(&bytes).unwrap();
        assert_eq!(parsed.packet_id, resp.packet_id);
        assert_eq!(parsed.weather_flag, resp.weather_flag);
        assert_eq!(parsed.temperature_flag, resp.temperature_flag);
        assert_eq!(parsed.pop_flag, resp.pop_flag);
        assert!(parsed.is_success());
    }

    #[test]
    fn test_packet_type_validation() {
        let req = ReportRequest::new(1, "000000", 0, 100, 0, false, false, false, false, false);
        let mut bytes = req.to_bytes();
        
        // パケット型を不正に変更
        bytes[2] = 0xFF; // type フィールドを破壊
        
        let result = ReportRequest::from_bytes(&bytes);
        assert!(result.is_err());
    }

    #[test]
    fn test_temperature_conversion() {
        let test_temps = [0.0, 25.5, -10.0, 50.0];
        
        for temp in test_temps {
            let req = ReportRequest::create_sensor_data_report(
                "000000", None, Some(temp), None, None, None, 1
            );
            
            // 整数精度での比較（内部表現は整数）
            let expected_internal = (temp as i32 + 100) as u16;
            assert_eq!(req.temperature, expected_internal);
            
            let recovered_temp = req.get_temperature_celsius();
            assert_eq!(recovered_temp, temp as i32 as f64);
        }
    }

    #[test]
    fn test_binary_data_handling() {
        let mut req = ReportRequest::new(1, "000000", 0, 100, 0, false, false, false, false, false);
        let binary_data = vec![0xAA, 0xBB, 0xCC, 0xDD];
        req.set_binary_data(binary_data.clone());
        
        let bytes = req.to_bytes();
        assert_eq!(bytes.len(), 24 + binary_data.len());
        
        let parsed = ReportRequest::from_bytes(&bytes).unwrap();
        assert_eq!(parsed.binary_data, Some(binary_data));
    }

    #[test]
    fn test_extended_fields() {
        let mut req = ReportRequest::new(1, "000000", 0, 100, 0, false, false, false, false, false);
        req.set_extended_field("source", "192.168.1.100:8080");
        
        assert!(req.ex_flag);
        let source_info = req.get_source_info();
        assert_eq!(source_info, Some(("192.168.1.100".to_string(), 8080)));
    }
}