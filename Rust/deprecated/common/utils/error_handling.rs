use std::collections::HashMap;
use std::error::Error as StdError;
use std::fmt;
use std::time::{Duration, Instant};
use serde::{Serialize, Deserialize};

// Python版と同等のエラーコード定義
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum WIPErrorCode {
    // Client errors (400-499)
    BadRequest = 400,
    NotFound = 410,
    PayloadTooLarge = 411,
    RequestTimeout = 420,
    TooManyRequests = 421,
    
    // Server errors (500-599)
    InternalServerError = 500,
    NotImplemented = 501,
    ServiceUnavailable = 503,
    GatewayTimeout = 504,
    
    // Network errors (600-699)
    NetworkError = 600,
    ConnectionFailed = 601,
    HostUnreachable = 602,
    DnsResolutionFailed = 603,
    
    // Protocol errors (700-799)
    ProtocolError = 700,
    InvalidPacket = 701,
    ChecksumMismatch = 702,
    UnsupportedVersion = 703,
    
    // System errors (800-899)
    OutOfMemory = 800,
    ResourceExhausted = 801,
    PermissionDenied = 802,
    ConfigurationError = 803,
}

impl WIPErrorCode {
    pub fn as_u16(self) -> u16 {
        self as u16
    }

    pub fn from_u16(code: u16) -> Option<Self> {
        match code {
            400 => Some(Self::BadRequest),
            410 => Some(Self::NotFound),
            411 => Some(Self::PayloadTooLarge),
            420 => Some(Self::RequestTimeout),
            421 => Some(Self::TooManyRequests),
            500 => Some(Self::InternalServerError),
            501 => Some(Self::NotImplemented),
            503 => Some(Self::ServiceUnavailable),
            504 => Some(Self::GatewayTimeout),
            600 => Some(Self::NetworkError),
            601 => Some(Self::ConnectionFailed),
            602 => Some(Self::HostUnreachable),
            603 => Some(Self::DnsResolutionFailed),
            700 => Some(Self::ProtocolError),
            701 => Some(Self::InvalidPacket),
            702 => Some(Self::ChecksumMismatch),
            703 => Some(Self::UnsupportedVersion),
            800 => Some(Self::OutOfMemory),
            801 => Some(Self::ResourceExhausted),
            802 => Some(Self::PermissionDenied),
            803 => Some(Self::ConfigurationError),
            _ => None,
        }
    }

    pub fn is_retryable(self) -> bool {
        match self {
            Self::RequestTimeout | Self::TooManyRequests |
            Self::ServiceUnavailable | Self::GatewayTimeout |
            Self::NetworkError | Self::ConnectionFailed |
            Self::HostUnreachable => true,
            _ => false,
        }
    }

    pub fn is_client_error(self) -> bool {
        let code = self.as_u16();
        code >= 400 && code < 500
    }

    pub fn is_server_error(self) -> bool {
        let code = self.as_u16();
        code >= 500 && code < 600
    }

    pub fn category(self) -> &'static str {
        match self.as_u16() {
            400..=499 => "client_error",
            500..=599 => "server_error",
            600..=699 => "network_error",
            700..=799 => "protocol_error",
            800..=899 => "system_error",
            _ => "unknown_error",
        }
    }

    pub fn description(self) -> &'static str {
        match self {
            Self::BadRequest => "The request was invalid or malformed",
            Self::NotFound => "The requested resource was not found",
            Self::PayloadTooLarge => "The request payload exceeds the maximum allowed size",
            Self::RequestTimeout => "The request timed out",
            Self::TooManyRequests => "Too many requests, rate limit exceeded",
            Self::InternalServerError => "An internal server error occurred",
            Self::NotImplemented => "The requested functionality is not implemented",
            Self::ServiceUnavailable => "The service is temporarily unavailable",
            Self::GatewayTimeout => "Gateway timeout occurred",
            Self::NetworkError => "A network error occurred",
            Self::ConnectionFailed => "Failed to establish connection",
            Self::HostUnreachable => "The target host is unreachable",
            Self::DnsResolutionFailed => "Failed to resolve hostname",
            Self::ProtocolError => "A protocol error occurred",
            Self::InvalidPacket => "Received an invalid packet",
            Self::ChecksumMismatch => "Packet checksum verification failed",
            Self::UnsupportedVersion => "Unsupported protocol version",
            Self::OutOfMemory => "Insufficient memory to complete operation",
            Self::ResourceExhausted => "System resources exhausted",
            Self::PermissionDenied => "Permission denied",
            Self::ConfigurationError => "Configuration error",
        }
    }
}

impl fmt::Display for WIPErrorCode {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{} ({}): {}", self.as_u16(), self.category(), self.description())
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ErrorContext {
    pub timestamp: u64,
    pub operation: String,
    pub component: String,
    pub metadata: HashMap<String, String>,
    pub stack_trace: Option<String>,
}

impl ErrorContext {
    pub fn new(operation: &str, component: &str) -> Self {
        Self {
            timestamp: std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap_or_default()
                .as_millis() as u64,
            operation: operation.to_string(),
            component: component.to_string(),
            metadata: HashMap::new(),
            stack_trace: None,
        }
    }

    pub fn with_metadata<K, V>(mut self, key: K, value: V) -> Self 
    where
        K: Into<String>,
        V: Into<String>,
    {
        self.metadata.insert(key.into(), value.into());
        self
    }

    pub fn with_stack_trace(mut self, trace: String) -> Self {
        self.stack_trace = Some(trace);
        self
    }
}

#[derive(Debug)]
pub struct WIPError {
    pub code: WIPErrorCode,
    pub message: String,
    pub context: Option<ErrorContext>,
    pub source: Option<Box<dyn StdError + Send + Sync>>,
    pub chain: Vec<WIPError>,
}

impl Clone for WIPError {
    fn clone(&self) -> Self {
        Self {
            code: self.code,
            message: self.message.clone(),
            context: self.context.clone(),
            source: None, // Cannot clone dyn StdError, so we drop the source
            chain: self.chain.clone(),
        }
    }
}

impl WIPError {
    pub fn new(code: WIPErrorCode, message: &str) -> Self {
        Self {
            code,
            message: message.to_string(),
            context: None,
            source: None,
            chain: Vec::new(),
        }
    }

    pub fn with_context(mut self, context: ErrorContext) -> Self {
        self.context = Some(context);
        self
    }

    pub fn with_source<E>(mut self, source: E) -> Self 
    where
        E: StdError + Send + Sync + 'static,
    {
        self.source = Some(Box::new(source));
        self
    }

    pub fn chain(mut self, error: WIPError) -> Self {
        self.chain.push(error);
        self
    }

    pub fn is_retryable(&self) -> bool {
        self.code.is_retryable()
    }

    pub fn severity(&self) -> ErrorSeverity {
        match self.code {
            WIPErrorCode::BadRequest | WIPErrorCode::NotFound | 
            WIPErrorCode::PayloadTooLarge => ErrorSeverity::Low,
            
            WIPErrorCode::RequestTimeout | WIPErrorCode::TooManyRequests |
            WIPErrorCode::NetworkError | WIPErrorCode::ConnectionFailed => ErrorSeverity::Medium,
            
            WIPErrorCode::InternalServerError | WIPErrorCode::ServiceUnavailable |
            WIPErrorCode::OutOfMemory | WIPErrorCode::ResourceExhausted => ErrorSeverity::High,
            
            WIPErrorCode::PermissionDenied | WIPErrorCode::ConfigurationError => ErrorSeverity::Critical,
            
            _ => ErrorSeverity::Medium,
        }
    }

    pub fn to_json(&self) -> Result<String, serde_json::Error> {
        let error_data = ErrorData {
            code: self.code.as_u16(),
            message: self.message.clone(),
            category: self.code.category().to_string(),
            context: self.context.clone(),
            chain: self.chain.iter().map(|e| ErrorData {
                code: e.code.as_u16(),
                message: e.message.clone(),
                category: e.code.category().to_string(),
                context: e.context.clone(),
                chain: Vec::new(), // Avoid infinite recursion
            }).collect(),
        };
        
        serde_json::to_string(&error_data)
    }

    // Python版のように詳細なデバッグ情報を生成
    pub fn debug_info(&self) -> String {
        let mut info = Vec::new();
        
        info.push(format!("Error: {} - {}", self.code, self.message));
        info.push(format!("Category: {}", self.code.category()));
        info.push(format!("Severity: {:?}", self.severity()));
        info.push(format!("Retryable: {}", self.is_retryable()));
        
        if let Some(context) = &self.context {
            info.push(format!("Operation: {}", context.operation));
            info.push(format!("Component: {}", context.component));
            info.push(format!("Timestamp: {}", context.timestamp));
            
            if !context.metadata.is_empty() {
                info.push("Metadata:".to_string());
                for (key, value) in &context.metadata {
                    info.push(format!("  {}: {}", key, value));
                }
            }
            
            if let Some(trace) = &context.stack_trace {
                info.push(format!("Stack trace:\n{}", trace));
            }
        }
        
        if !self.chain.is_empty() {
            info.push("Error chain:".to_string());
            for (i, chained_error) in self.chain.iter().enumerate() {
                info.push(format!("  {}: {} - {}", i + 1, chained_error.code, chained_error.message));
            }
        }
        
        info.join("\n")
    }
}

impl fmt::Display for WIPError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{}: {}", self.code, self.message)
    }
}

impl StdError for WIPError {
    fn source(&self) -> Option<&(dyn StdError + 'static)> {
        self.source.as_ref().map(|e| e.as_ref() as &(dyn StdError + 'static))
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum ErrorSeverity {
    Low,
    Medium,
    High,
    Critical,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
struct ErrorData {
    code: u16,
    message: String,
    category: String,
    context: Option<ErrorContext>,
    chain: Vec<ErrorData>,
}

// エラー統計の収集
#[derive(Debug, Clone)]
pub struct ErrorStats {
    pub error_counts: HashMap<WIPErrorCode, usize>,
    pub severity_counts: HashMap<ErrorSeverity, usize>,
    pub category_counts: HashMap<String, usize>,
    pub total_errors: usize,
    pub last_error_time: Option<Instant>,
    pub error_rate: f64, // errors per minute
}

impl ErrorStats {
    pub fn new() -> Self {
        Self {
            error_counts: HashMap::new(),
            severity_counts: HashMap::new(),
            category_counts: HashMap::new(),
            total_errors: 0,
            last_error_time: None,
            error_rate: 0.0,
        }
    }

    pub fn record_error(&mut self, error: &WIPError) {
        *self.error_counts.entry(error.code).or_insert(0) += 1;
        *self.severity_counts.entry(error.severity()).or_insert(0) += 1;
        *self.category_counts.entry(error.code.category().to_string()).or_insert(0) += 1;
        
        self.total_errors += 1;
        self.last_error_time = Some(Instant::now());
        
        // Update error rate (simplified calculation)
        // In practice, you'd use a sliding window
        if self.total_errors > 1 {
            self.error_rate = self.total_errors as f64 / 60.0; // Rough approximation
        }
    }

    pub fn most_common_error(&self) -> Option<(WIPErrorCode, usize)> {
        self.error_counts.iter()
            .max_by_key(|(_, &count)| count)
            .map(|(&code, &count)| (code, count))
    }

    pub fn error_rate_for_code(&self, code: WIPErrorCode) -> f64 {
        let count = self.error_counts.get(&code).unwrap_or(&0);
        if self.total_errors > 0 {
            *count as f64 / self.total_errors as f64
        } else {
            0.0
        }
    }
}

// エラーハンドリングマネージャー
pub struct ErrorHandler {
    stats: std::sync::Mutex<ErrorStats>,
    handlers: HashMap<WIPErrorCode, Box<dyn Fn(&WIPError) + Send + Sync>>,
}

impl ErrorHandler {
    pub fn new() -> Self {
        Self {
            stats: std::sync::Mutex::new(ErrorStats::new()),
            handlers: HashMap::new(),
        }
    }

    pub fn handle_error(&self, error: &WIPError) {
        // Record statistics
        if let Ok(mut stats) = self.stats.lock() {
            stats.record_error(error);
        }

        // Run custom handlers
        if let Some(handler) = self.handlers.get(&error.code) {
            handler(error);
        }

        // Default handling based on severity
        match error.severity() {
            ErrorSeverity::Critical => {
                eprintln!("CRITICAL ERROR: {}", error.debug_info());
                // In production, might trigger alerts
            }
            ErrorSeverity::High => {
                eprintln!("HIGH SEVERITY ERROR: {}", error);
            }
            ErrorSeverity::Medium => {
                eprintln!("ERROR: {}", error);
            }
            ErrorSeverity::Low => {
                // Log at debug level
                if cfg!(debug_assertions) {
                    println!("Warning: {}", error);
                }
            }
        }
    }

    pub fn register_handler<F>(&mut self, code: WIPErrorCode, handler: F)
    where
        F: Fn(&WIPError) + Send + Sync + 'static,
    {
        self.handlers.insert(code, Box::new(handler));
    }

    pub fn get_stats(&self) -> ErrorStats {
        self.stats.lock().unwrap().clone()
    }

    pub fn clear_stats(&self) {
        if let Ok(mut stats) = self.stats.lock() {
            *stats = ErrorStats::new();
        }
    }
}

// 便利なマクロとヘルパー関数
#[macro_export]
macro_rules! wip_error {
    ($code:expr, $msg:expr) => {
        WIPError::new($code, $msg)
    };
    ($code:expr, $msg:expr, $($key:expr => $value:expr),*) => {
        {
            let mut context = ErrorContext::new("", "");
            $(
                context = context.with_metadata($key, $value);
            )*
            WIPError::new($code, $msg).with_context(context)
        }
    };
}

#[macro_export]
macro_rules! wip_bail {
    ($code:expr, $msg:expr) => {
        return Err(wip_error!($code, $msg))
    };
    ($code:expr, $msg:expr, $($key:expr => $value:expr),*) => {
        return Err(wip_error!($code, $msg, $($key => $value),*))
    };
}

// Result type alias for convenience
pub type WIPResult<T> = Result<T, WIPError>;

// Python版のようなコンテキストマネージャーパターンをRustで実現
pub struct ErrorScope {
    operation: String,
    component: String,
    start_time: Instant,
}

impl ErrorScope {
    pub fn new(operation: &str, component: &str) -> Self {
        Self {
            operation: operation.to_string(),
            component: component.to_string(),
            start_time: Instant::now(),
        }
    }

    pub fn wrap_error(&self, error: WIPError) -> WIPError {
        let duration = self.start_time.elapsed();
        let context = ErrorContext::new(&self.operation, &self.component)
            .with_metadata("duration_ms", duration.as_millis().to_string());
        
        error.with_context(context)
    }

    pub fn create_error(&self, code: WIPErrorCode, message: &str) -> WIPError {
        let duration = self.start_time.elapsed();
        let context = ErrorContext::new(&self.operation, &self.component)
            .with_metadata("duration_ms", duration.as_millis().to_string());
        
        WIPError::new(code, message).with_context(context)
    }
}

// From implementations for common error types
impl From<std::io::Error> for WIPError {
    fn from(err: std::io::Error) -> Self {
        let code = match err.kind() {
            std::io::ErrorKind::NotFound => WIPErrorCode::NotFound,
            std::io::ErrorKind::PermissionDenied => WIPErrorCode::PermissionDenied,
            std::io::ErrorKind::ConnectionRefused => WIPErrorCode::ConnectionFailed,
            std::io::ErrorKind::TimedOut => WIPErrorCode::RequestTimeout,
            _ => WIPErrorCode::NetworkError,
        };
        
        WIPError::new(code, &err.to_string()).with_source(err)
    }
}

impl From<serde_json::Error> for WIPError {
    fn from(err: serde_json::Error) -> Self {
        WIPError::new(WIPErrorCode::InvalidPacket, &err.to_string()).with_source(err)
    }
}

impl From<std::num::ParseIntError> for WIPError {
    fn from(err: std::num::ParseIntError) -> Self {
        WIPError::new(WIPErrorCode::BadRequest, &err.to_string()).with_source(err)
    }
}