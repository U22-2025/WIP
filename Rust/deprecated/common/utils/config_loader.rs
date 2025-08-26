use std::collections::HashMap;
use std::env;
use std::fs;
use std::path::{Path, PathBuf};
use serde::{Deserialize, Serialize};
use serde_json;
use toml;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ServerConfig {
    pub host: String,
    pub port: u16,
    pub timeout: u64,
    pub retries: u32,
}

impl Default for ServerConfig {
    fn default() -> Self {
        Self {
            host: "localhost".to_string(),
            port: 8080,
            timeout: 30,
            retries: 3,
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WIPConfig {
    pub server: ServerConfig,
    pub auth: AuthConfig,
    pub cache: CacheConfig,
    pub logging: LogConfig,
    pub custom: HashMap<String, serde_json::Value>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AuthConfig {
    pub enabled: bool,
    pub session_timeout: u64,
    pub max_sessions: usize,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CacheConfig {
    pub enabled: bool,
    pub max_size: usize,
    pub ttl: u64,
    pub file_cache_path: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LogConfig {
    pub level: String,
    pub file: Option<String>,
    pub max_size: u64,
    pub rotation: bool,
}

impl Default for WIPConfig {
    fn default() -> Self {
        Self {
            server: ServerConfig::default(),
            auth: AuthConfig {
                enabled: true,
                session_timeout: 3600,
                max_sessions: 10,
            },
            cache: CacheConfig {
                enabled: true,
                max_size: 1000,
                ttl: 300,
                file_cache_path: None,
            },
            logging: LogConfig {
                level: "info".to_string(),
                file: None,
                max_size: 10 * 1024 * 1024, // 10MB
                rotation: true,
            },
            custom: HashMap::new(),
        }
    }
}

pub struct ConfigLoader {
    config_paths: Vec<PathBuf>,
    env_prefix: String,
}

impl ConfigLoader {
    pub fn new() -> Self {
        Self {
            config_paths: vec![
                PathBuf::from("config.json"),
                PathBuf::from("config.toml"),
                PathBuf::from("wip.config.json"),
                PathBuf::from("wip.config.toml"),
            ],
            env_prefix: "WIP_".to_string(),
        }
    }

    pub fn with_paths(paths: Vec<PathBuf>) -> Self {
        Self {
            config_paths: paths,
            env_prefix: "WIP_".to_string(),
        }
    }

    pub fn with_env_prefix(mut self, prefix: String) -> Self {
        self.env_prefix = prefix;
        self
    }

    pub fn load(&self) -> Result<WIPConfig, String> {
        let mut config = WIPConfig::default();

        // Try to load from files
        for path in &self.config_paths {
            if path.exists() {
                match self.load_from_file(path) {
                    Ok(file_config) => {
                        config = self.merge_config(config, file_config)?;
                        break;
                    }
                    Err(e) => {
                        eprintln!("Warning: Failed to load config from {:?}: {}", path, e);
                    }
                }
            }
        }

        // Override with environment variables
        config = self.apply_env_overrides(config)?;

        // Validate configuration
        self.validate_config(&config)?;

        Ok(config)
    }

    fn load_from_file(&self, path: &Path) -> Result<WIPConfig, String> {
        let content = fs::read_to_string(path)
            .map_err(|e| format!("Failed to read config file: {}", e))?;

        match path.extension().and_then(|s| s.to_str()) {
            Some("json") => {
                serde_json::from_str(&content)
                    .map_err(|e| format!("Failed to parse JSON config: {}", e))
            }
            Some("toml") => {
                toml::from_str(&content)
                    .map_err(|e| format!("Failed to parse TOML config: {}", e))
            }
            _ => Err("Unsupported config file format".to_string()),
        }
    }

    fn merge_config(&self, mut base: WIPConfig, override_config: WIPConfig) -> Result<WIPConfig, String> {
        // Merge server config
        if override_config.server.host != ServerConfig::default().host {
            base.server.host = override_config.server.host;
        }
        if override_config.server.port != ServerConfig::default().port {
            base.server.port = override_config.server.port;
        }
        if override_config.server.timeout != ServerConfig::default().timeout {
            base.server.timeout = override_config.server.timeout;
        }
        if override_config.server.retries != ServerConfig::default().retries {
            base.server.retries = override_config.server.retries;
        }

        // Merge other configs (simplified for brevity)
        base.auth = override_config.auth;
        base.cache = override_config.cache;
        base.logging = override_config.logging;

        // Merge custom fields
        for (key, value) in override_config.custom {
            base.custom.insert(key, value);
        }

        Ok(base)
    }

    fn apply_env_overrides(&self, mut config: WIPConfig) -> Result<WIPConfig, String> {
        // Server overrides
        if let Ok(host) = env::var(format!("{}SERVER_HOST", self.env_prefix)) {
            config.server.host = host;
        }
        if let Ok(port_str) = env::var(format!("{}SERVER_PORT", self.env_prefix)) {
            config.server.port = port_str.parse()
                .map_err(|_| "Invalid port number in environment variable")?;
        }
        if let Ok(timeout_str) = env::var(format!("{}SERVER_TIMEOUT", self.env_prefix)) {
            config.server.timeout = timeout_str.parse()
                .map_err(|_| "Invalid timeout in environment variable")?;
        }

        // Auth overrides
        if let Ok(enabled_str) = env::var(format!("{}AUTH_ENABLED", self.env_prefix)) {
            config.auth.enabled = enabled_str.parse()
                .map_err(|_| "Invalid auth enabled flag in environment variable")?;
        }

        // Cache overrides
        if let Ok(enabled_str) = env::var(format!("{}CACHE_ENABLED", self.env_prefix)) {
            config.cache.enabled = enabled_str.parse()
                .map_err(|_| "Invalid cache enabled flag in environment variable")?;
        }
        if let Ok(ttl_str) = env::var(format!("{}CACHE_TTL", self.env_prefix)) {
            config.cache.ttl = ttl_str.parse()
                .map_err(|_| "Invalid cache TTL in environment variable")?;
        }

        // Logging overrides
        if let Ok(level) = env::var(format!("{}LOG_LEVEL", self.env_prefix)) {
            config.logging.level = level;
        }
        if let Ok(file) = env::var(format!("{}LOG_FILE", self.env_prefix)) {
            config.logging.file = Some(file);
        }

        Ok(config)
    }

    fn validate_config(&self, config: &WIPConfig) -> Result<(), String> {
        // Validate server config
        if config.server.host.is_empty() {
            return Err("Server host cannot be empty".to_string());
        }
        if config.server.port == 0 {
            return Err("Server port must be greater than 0".to_string());
        }

        // Validate log level
        match config.logging.level.to_lowercase().as_str() {
            "trace" | "debug" | "info" | "warn" | "error" => {}
            _ => return Err("Invalid log level. Must be one of: trace, debug, info, warn, error".to_string()),
        }

        // Validate cache config
        if config.cache.enabled && config.cache.max_size == 0 {
            return Err("Cache max size must be greater than 0 when cache is enabled".to_string());
        }

        Ok(())
    }

    pub fn save_config(&self, config: &WIPConfig, path: &Path) -> Result<(), String> {
        let content = match path.extension().and_then(|s| s.to_str()) {
            Some("json") => {
                serde_json::to_string_pretty(config)
                    .map_err(|e| format!("Failed to serialize config to JSON: {}", e))?
            }
            Some("toml") => {
                toml::to_string_pretty(config)
                    .map_err(|e| format!("Failed to serialize config to TOML: {}", e))?
            }
            _ => return Err("Unsupported config file format for saving".to_string()),
        };

        fs::write(path, content)
            .map_err(|e| format!("Failed to write config file: {}", e))?;

        Ok(())
    }
}
