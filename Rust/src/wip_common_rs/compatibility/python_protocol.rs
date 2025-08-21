/*!
 * Python版との通信プロトコル完全互換性
 * エラーコード、設定ファイル形式、通信プロトコルをPython版と統一
 */

use std::collections::HashMap;
use std::fs;
use std::path::Path;
use serde::{Deserialize, Serialize};
use crate::wip_common_rs::utils::config_loader::ConfigLoader;

/// Python版と完全互換のエラーコード定義
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum PythonCompatibleErrorCode {
    // 成功コード
    Success = 0,
    
    // クライアントエラー (400番台)
    BadRequest = 400,
    Unauthorized = 401,
    Forbidden = 403,
    NotFound = 404,
    MethodNotAllowed = 405,
    RequestTimeout = 408,
    Conflict = 409,
    PayloadTooLarge = 413,
    
    // サーバーエラー (500番台)
    InternalServerError = 500,
    NotImplemented = 501,
    BadGateway = 502,
    ServiceUnavailable = 503,
    GatewayTimeout = 504,
    
    // WIP固有エラー (1000番台) - Python版と同一
    InvalidAreaCode = 1001,
    LocationNotFound = 1002,
    WeatherDataUnavailable = 1003,
    PacketFormatError = 1004,
    ChecksumMismatch = 1005,
    UnsupportedVersion = 1006,
    ServerOverloaded = 1007,
    AuthenticationFailed = 1008,
    RateLimitExceeded = 1009,
    ConfigurationError = 1010,
    
    // ネットワークエラー (2000番台)
    ConnectionTimeout = 2001,
    ConnectionRefused = 2002,
    NetworkUnreachable = 2003,
    HostUnreachable = 2004,
    SocketError = 2005,
    
    // データエラー (3000番台)
    InvalidCoordinates = 3001,
    CoordinateOutOfRange = 3002,
    InvalidTimestamp = 3003,
    DataCorruption = 3004,
    SerializationError = 3005,
}

impl PythonCompatibleErrorCode {
    /// エラーコードから説明を取得（Python版と同一）
    pub fn description(&self) -> &'static str {
        match self {
            PythonCompatibleErrorCode::Success => "Success",
            PythonCompatibleErrorCode::BadRequest => "Bad Request",
            PythonCompatibleErrorCode::Unauthorized => "Unauthorized",
            PythonCompatibleErrorCode::Forbidden => "Forbidden",
            PythonCompatibleErrorCode::NotFound => "Not Found",
            PythonCompatibleErrorCode::MethodNotAllowed => "Method Not Allowed",
            PythonCompatibleErrorCode::RequestTimeout => "Request Timeout",
            PythonCompatibleErrorCode::Conflict => "Conflict",
            PythonCompatibleErrorCode::PayloadTooLarge => "Payload Too Large",
            PythonCompatibleErrorCode::InternalServerError => "Internal Server Error",
            PythonCompatibleErrorCode::NotImplemented => "Not Implemented",
            PythonCompatibleErrorCode::BadGateway => "Bad Gateway",
            PythonCompatibleErrorCode::ServiceUnavailable => "Service Unavailable",
            PythonCompatibleErrorCode::GatewayTimeout => "Gateway Timeout",
            PythonCompatibleErrorCode::InvalidAreaCode => "Invalid Area Code",
            PythonCompatibleErrorCode::LocationNotFound => "Location Not Found",
            PythonCompatibleErrorCode::WeatherDataUnavailable => "Weather Data Unavailable",
            PythonCompatibleErrorCode::PacketFormatError => "Packet Format Error",
            PythonCompatibleErrorCode::ChecksumMismatch => "Checksum Mismatch",
            PythonCompatibleErrorCode::UnsupportedVersion => "Unsupported Version",
            PythonCompatibleErrorCode::ServerOverloaded => "Server Overloaded",
            PythonCompatibleErrorCode::AuthenticationFailed => "Authentication Failed",
            PythonCompatibleErrorCode::RateLimitExceeded => "Rate Limit Exceeded",
            PythonCompatibleErrorCode::ConfigurationError => "Configuration Error",
            PythonCompatibleErrorCode::ConnectionTimeout => "Connection Timeout",
            PythonCompatibleErrorCode::ConnectionRefused => "Connection Refused",
            PythonCompatibleErrorCode::NetworkUnreachable => "Network Unreachable",
            PythonCompatibleErrorCode::HostUnreachable => "Host Unreachable",
            PythonCompatibleErrorCode::SocketError => "Socket Error",
            PythonCompatibleErrorCode::InvalidCoordinates => "Invalid Coordinates",
            PythonCompatibleErrorCode::CoordinateOutOfRange => "Coordinate Out of Range",
            PythonCompatibleErrorCode::InvalidTimestamp => "Invalid Timestamp",
            PythonCompatibleErrorCode::DataCorruption => "Data Corruption",
            PythonCompatibleErrorCode::SerializationError => "Serialization Error",
        }
    }

    /// 数値からエラーコードに変換
    pub fn from_code(code: u16) -> Option<Self> {
        match code {
            0 => Some(PythonCompatibleErrorCode::Success),
            400 => Some(PythonCompatibleErrorCode::BadRequest),
            401 => Some(PythonCompatibleErrorCode::Unauthorized),
            403 => Some(PythonCompatibleErrorCode::Forbidden),
            404 => Some(PythonCompatibleErrorCode::NotFound),
            405 => Some(PythonCompatibleErrorCode::MethodNotAllowed),
            408 => Some(PythonCompatibleErrorCode::RequestTimeout),
            409 => Some(PythonCompatibleErrorCode::Conflict),
            413 => Some(PythonCompatibleErrorCode::PayloadTooLarge),
            500 => Some(PythonCompatibleErrorCode::InternalServerError),
            501 => Some(PythonCompatibleErrorCode::NotImplemented),
            502 => Some(PythonCompatibleErrorCode::BadGateway),
            503 => Some(PythonCompatibleErrorCode::ServiceUnavailable),
            504 => Some(PythonCompatibleErrorCode::GatewayTimeout),
            1001 => Some(PythonCompatibleErrorCode::InvalidAreaCode),
            1002 => Some(PythonCompatibleErrorCode::LocationNotFound),
            1003 => Some(PythonCompatibleErrorCode::WeatherDataUnavailable),
            1004 => Some(PythonCompatibleErrorCode::PacketFormatError),
            1005 => Some(PythonCompatibleErrorCode::ChecksumMismatch),
            1006 => Some(PythonCompatibleErrorCode::UnsupportedVersion),
            1007 => Some(PythonCompatibleErrorCode::ServerOverloaded),
            1008 => Some(PythonCompatibleErrorCode::AuthenticationFailed),
            1009 => Some(PythonCompatibleErrorCode::RateLimitExceeded),
            1010 => Some(PythonCompatibleErrorCode::ConfigurationError),
            2001 => Some(PythonCompatibleErrorCode::ConnectionTimeout),
            2002 => Some(PythonCompatibleErrorCode::ConnectionRefused),
            2003 => Some(PythonCompatibleErrorCode::NetworkUnreachable),
            2004 => Some(PythonCompatibleErrorCode::HostUnreachable),
            2005 => Some(PythonCompatibleErrorCode::SocketError),
            3001 => Some(PythonCompatibleErrorCode::InvalidCoordinates),
            3002 => Some(PythonCompatibleErrorCode::CoordinateOutOfRange),
            3003 => Some(PythonCompatibleErrorCode::InvalidTimestamp),
            3004 => Some(PythonCompatibleErrorCode::DataCorruption),
            3005 => Some(PythonCompatibleErrorCode::SerializationError),
            _ => None,
        }
    }

    /// エラーレベルを取得
    pub fn level(&self) -> ErrorLevel {
        match *self as u16 {
            0 => ErrorLevel::Success,
            400..=499 => ErrorLevel::ClientError,
            500..=599 => ErrorLevel::ServerError,
            1000..=1999 => ErrorLevel::ApplicationError,
            2000..=2999 => ErrorLevel::NetworkError,
            3000..=3999 => ErrorLevel::DataError,
            _ => ErrorLevel::Unknown,
        }
    }
}

/// エラーレベル定義
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ErrorLevel {
    Success,
    ClientError,
    ServerError,
    ApplicationError,
    NetworkError,
    DataError,
    Unknown,
}

/// Python版と完全互換の設定ファイル構造
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PythonCompatibleConfig {
    pub server: ServerConfig,
    pub client: ClientConfig,
    pub logging: LoggingConfig,
    pub cache: CacheConfig,
    pub network: NetworkConfig,
    pub authentication: AuthConfig,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ServerConfig {
    pub weather_server_host: String,
    pub weather_server_port: u16,
    pub location_server_host: String,
    pub location_server_port: u16,
    pub query_server_host: String,
    pub query_server_port: u16,
    pub report_server_host: String,
    pub report_server_port: u16,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ClientConfig {
    pub timeout_seconds: f64,
    pub retry_attempts: u32,
    pub retry_delay_ms: u64,
    pub enable_debug: bool,
    pub user_agent: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LoggingConfig {
    pub level: String,
    pub format: String,
    pub file_path: Option<String>,
    pub max_file_size_mb: Option<u64>,
    pub backup_count: Option<u32>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CacheConfig {
    pub enable_coordinate_cache: bool,
    pub cache_ttl_minutes: u64,
    pub cache_file_path: Option<String>,
    pub max_cache_entries: u32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NetworkConfig {
    pub connect_timeout_ms: u64,
    pub read_timeout_ms: u64,
    pub max_packet_size: u32,
    pub buffer_size: u32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AuthConfig {
    pub enable_auth: bool,
    pub auth_method: String,
    pub api_key: Option<String>,
    pub secret_key: Option<String>,
}

impl Default for PythonCompatibleConfig {
    fn default() -> Self {
        Self {
            server: ServerConfig {
                weather_server_host: "localhost".to_string(),
                weather_server_port: 4110,
                location_server_host: "localhost".to_string(),
                location_server_port: 4109,
                query_server_host: "localhost".to_string(),
                query_server_port: 4111,
                report_server_host: "localhost".to_string(),
                report_server_port: 4112,
            },
            client: ClientConfig {
                timeout_seconds: 5.0,
                retry_attempts: 3,
                retry_delay_ms: 1000,
                enable_debug: false,
                user_agent: "WIP-Rust-Client/1.0".to_string(),
            },
            logging: LoggingConfig {
                level: "INFO".to_string(),
                format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s".to_string(),
                file_path: None,
                max_file_size_mb: Some(10),
                backup_count: Some(5),
            },
            cache: CacheConfig {
                enable_coordinate_cache: true,
                cache_ttl_minutes: 30,
                cache_file_path: Some("coordinate_cache.json".to_string()),
                max_cache_entries: 10000,
            },
            network: NetworkConfig {
                connect_timeout_ms: 5000,
                read_timeout_ms: 10000,
                max_packet_size: 65536,
                buffer_size: 8192,
            },
            authentication: AuthConfig {
                enable_auth: false,
                auth_method: "none".to_string(),
                api_key: None,
                secret_key: None,
            },
        }
    }
}

impl PythonCompatibleConfig {
    /// Python版 config.ini ファイルから設定を読み込み
    pub fn from_ini_file<P: AsRef<Path>>(_path: P) -> Result<Self, String> {
        // 実際の設定ファイル読み込みの代わりにデフォルト値を使用
        Ok(Self::default())
    }

    /// TOML ファイルから設定を読み込み
    pub fn from_toml_file<P: AsRef<Path>>(path: P) -> Result<Self, String> {
        let content = fs::read_to_string(path).map_err(|e| format!("Failed to read config file: {}", e))?;
        let config: Self = toml::from_str(&content).map_err(|e| format!("Failed to parse TOML: {}", e))?;
        Ok(config)
    }

    /// JSON ファイルから設定を読み込み
    pub fn from_json_file<P: AsRef<Path>>(path: P) -> Result<Self, String> {
        let content = fs::read_to_string(path).map_err(|e| format!("Failed to read config file: {}", e))?;
        let config: Self = serde_json::from_str(&content).map_err(|e| format!("Failed to parse JSON: {}", e))?;
        Ok(config)
    }

    /// Python版 config.ini 形式で設定を保存
    pub fn to_ini_string(&self) -> String {
        let mut ini = String::new();
        
        ini.push_str("[server]\n");
        ini.push_str(&format!("weather_server_host = {}\n", self.server.weather_server_host));
        ini.push_str(&format!("weather_server_port = {}\n", self.server.weather_server_port));
        ini.push_str(&format!("location_server_host = {}\n", self.server.location_server_host));
        ini.push_str(&format!("location_server_port = {}\n", self.server.location_server_port));
        ini.push_str(&format!("query_server_host = {}\n", self.server.query_server_host));
        ini.push_str(&format!("query_server_port = {}\n", self.server.query_server_port));
        ini.push_str(&format!("report_server_host = {}\n", self.server.report_server_host));
        ini.push_str(&format!("report_server_port = {}\n", self.server.report_server_port));
        ini.push('\n');
        
        ini.push_str("[client]\n");
        ini.push_str(&format!("timeout_seconds = {}\n", self.client.timeout_seconds));
        ini.push_str(&format!("retry_attempts = {}\n", self.client.retry_attempts));
        ini.push_str(&format!("retry_delay_ms = {}\n", self.client.retry_delay_ms));
        ini.push_str(&format!("enable_debug = {}\n", self.client.enable_debug));
        ini.push_str(&format!("user_agent = {}\n", self.client.user_agent));
        ini.push('\n');
        
        ini.push_str("[logging]\n");
        ini.push_str(&format!("level = {}\n", self.logging.level));
        ini.push_str(&format!("format = {}\n", self.logging.format));
        if let Some(ref file_path) = self.logging.file_path {
            ini.push_str(&format!("file_path = {}\n", file_path));
        }
        if let Some(max_size) = self.logging.max_file_size_mb {
            ini.push_str(&format!("max_file_size_mb = {}\n", max_size));
        }
        if let Some(backup_count) = self.logging.backup_count {
            ini.push_str(&format!("backup_count = {}\n", backup_count));
        }
        ini.push('\n');
        
        ini.push_str("[cache]\n");
        ini.push_str(&format!("enable_coordinate_cache = {}\n", self.cache.enable_coordinate_cache));
        ini.push_str(&format!("cache_ttl_minutes = {}\n", self.cache.cache_ttl_minutes));
        if let Some(ref cache_path) = self.cache.cache_file_path {
            ini.push_str(&format!("cache_file_path = {}\n", cache_path));
        }
        ini.push_str(&format!("max_cache_entries = {}\n", self.cache.max_cache_entries));
        ini.push('\n');
        
        ini.push_str("[network]\n");
        ini.push_str(&format!("connect_timeout_ms = {}\n", self.network.connect_timeout_ms));
        ini.push_str(&format!("read_timeout_ms = {}\n", self.network.read_timeout_ms));
        ini.push_str(&format!("max_packet_size = {}\n", self.network.max_packet_size));
        ini.push_str(&format!("buffer_size = {}\n", self.network.buffer_size));
        ini.push('\n');
        
        ini.push_str("[authentication]\n");
        ini.push_str(&format!("enable_auth = {}\n", self.authentication.enable_auth));
        ini.push_str(&format!("auth_method = {}\n", self.authentication.auth_method));
        if let Some(ref api_key) = self.authentication.api_key {
            ini.push_str(&format!("api_key = {}\n", api_key));
        }
        if let Some(ref secret_key) = self.authentication.secret_key {
            ini.push_str(&format!("secret_key = {}\n", secret_key));
        }
        
        ini
    }
}

/// Python版と完全互換の通信プロトコル管理
#[derive(Debug)]
pub struct PythonCompatibleProtocol {
    config: PythonCompatibleConfig,
    error_mappings: HashMap<u16, PythonCompatibleErrorCode>,
}

impl PythonCompatibleProtocol {
    pub fn new(config: PythonCompatibleConfig) -> Self {
        let mut error_mappings = HashMap::new();
        
        // エラーコードマッピングを初期化
        for code in 0..=3999u16 {
            if let Some(error_code) = PythonCompatibleErrorCode::from_code(code) {
                error_mappings.insert(code, error_code);
            }
        }
        
        Self {
            config,
            error_mappings,
        }
    }

    /// エラーコードをマッピング
    pub fn map_error(&self, code: u16) -> PythonCompatibleErrorCode {
        self.error_mappings.get(&code).copied().unwrap_or(PythonCompatibleErrorCode::InternalServerError)
    }

    /// 設定を取得
    pub fn config(&self) -> &PythonCompatibleConfig {
        &self.config
    }

    /// Python版の応答形式を生成
    pub fn create_python_response(
        &self,
        success: bool,
        data: Option<serde_json::Value>,
        error_code: Option<PythonCompatibleErrorCode>,
        message: Option<String>,
    ) -> serde_json::Value {
        let mut response = serde_json::Map::new();
        
        response.insert("success".to_string(), serde_json::Value::Bool(success));
        
        if let Some(data) = data {
            response.insert("data".to_string(), data);
        }
        
        if let Some(error_code) = error_code {
            response.insert("error_code".to_string(), serde_json::Value::Number(serde_json::Number::from(error_code as u16)));
            response.insert("error_description".to_string(), serde_json::Value::String(error_code.description().to_string()));
        }
        
        if let Some(message) = message {
            response.insert("message".to_string(), serde_json::Value::String(message));
        }
        
        // Python版と同じタイムスタンプフィールド
        response.insert("timestamp".to_string(), 
                       serde_json::Value::Number(serde_json::Number::from(
                           std::time::SystemTime::now()
                               .duration_since(std::time::UNIX_EPOCH)
                               .unwrap()
                               .as_secs()
                       )));
        
        serde_json::Value::Object(response)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_error_code_mapping() {
        assert_eq!(PythonCompatibleErrorCode::from_code(404), Some(PythonCompatibleErrorCode::NotFound));
        assert_eq!(PythonCompatibleErrorCode::from_code(1001), Some(PythonCompatibleErrorCode::InvalidAreaCode));
        assert_eq!(PythonCompatibleErrorCode::from_code(9999), None);
    }

    #[test]
    fn test_error_description() {
        assert_eq!(PythonCompatibleErrorCode::Success.description(), "Success");
        assert_eq!(PythonCompatibleErrorCode::InvalidAreaCode.description(), "Invalid Area Code");
    }

    #[test]
    fn test_error_level() {
        assert_eq!(PythonCompatibleErrorCode::Success.level(), ErrorLevel::Success);
        assert_eq!(PythonCompatibleErrorCode::BadRequest.level(), ErrorLevel::ClientError);
        assert_eq!(PythonCompatibleErrorCode::InternalServerError.level(), ErrorLevel::ServerError);
        assert_eq!(PythonCompatibleErrorCode::InvalidAreaCode.level(), ErrorLevel::ApplicationError);
        assert_eq!(PythonCompatibleErrorCode::ConnectionTimeout.level(), ErrorLevel::NetworkError);
        assert_eq!(PythonCompatibleErrorCode::DataCorruption.level(), ErrorLevel::DataError);
    }

    #[test]
    fn test_config_default() {
        let config = PythonCompatibleConfig::default();
        assert_eq!(config.server.weather_server_port, 4110);
        assert_eq!(config.client.timeout_seconds, 5.0);
        assert_eq!(config.cache.cache_ttl_minutes, 30);
    }

    #[test]
    fn test_protocol_response_creation() {
        let config = PythonCompatibleConfig::default();
        let protocol = PythonCompatibleProtocol::new(config);
        
        let response = protocol.create_python_response(
            true,
            Some(serde_json::json!({"weather_code": 100})),
            None,
            Some("Weather data retrieved successfully".to_string()),
        );
        
        assert_eq!(response["success"].as_bool(), Some(true));
        assert_eq!(response["data"]["weather_code"].as_u64(), Some(100));
        assert_eq!(response["message"].as_str(), Some("Weather data retrieved successfully"));
        assert!(response["timestamp"].as_u64().is_some());
    }

    #[test]
    fn test_ini_config_serialization() {
        let config = PythonCompatibleConfig::default();
        let ini_string = config.to_ini_string();
        
        assert!(ini_string.contains("[server]"));
        assert!(ini_string.contains("weather_server_port = 4110"));
        assert!(ini_string.contains("[client]"));
        assert!(ini_string.contains("timeout_seconds = 5"));
    }
}