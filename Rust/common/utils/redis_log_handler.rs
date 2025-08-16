#[cfg(feature = "redis-logging")]
use redis;

use std::collections::HashMap;
use std::sync::{Arc, Mutex};
use std::time::{SystemTime, UNIX_EPOCH};
use serde::{Serialize, Deserialize};
use serde_json;
use crate::common::utils::log_config::{LogEntry, LogLevel};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RedisLogEntry {
    pub timestamp: u64,
    pub level: String,
    pub module: String,
    pub message: String,
    pub hostname: String,
    pub service: String,
    pub metadata: HashMap<String, serde_json::Value>,
}

impl RedisLogEntry {
    pub fn from_log_entry(entry: &LogEntry, service: &str) -> Self {
        Self {
            timestamp: SystemTime::now()
                .duration_since(UNIX_EPOCH)
                .unwrap_or_default()
                .as_millis() as u64,
            level: entry.level.as_str().to_string(),
            module: entry.module.clone(),
            message: entry.message.clone(),
            hostname: gethostname::gethostname()
                .to_string_lossy()
                .to_string(),
            service: service.to_string(),
            metadata: HashMap::new(),
        }
    }

    pub fn with_metadata(mut self, key: &str, value: serde_json::Value) -> Self {
        self.metadata.insert(key.to_string(), value);
        self
    }
}

#[cfg(feature = "redis-logging")]
pub struct RedisLogHandler {
    client: Option<redis::Client>,
    connection: Arc<Mutex<Option<redis::Connection>>>,
    service_name: String,
    log_key: String,
    max_logs: usize,
    buffer: Arc<Mutex<Vec<RedisLogEntry>>>,
    buffer_size: usize,
    enabled: bool,
}

#[cfg(feature = "redis-logging")]
impl RedisLogHandler {
    pub fn new(redis_url: &str, service_name: &str) -> Result<Self, String> {
        let client = redis::Client::open(redis_url)
            .map_err(|e| format!("Failed to create Redis client: {}", e))?;
        
        Ok(Self {
            client: Some(client),
            connection: Arc::new(Mutex::new(None)),
            service_name: service_name.to_string(),
            log_key: format!("logs:{}", service_name),
            max_logs: 10000,
            buffer: Arc::new(Mutex::new(Vec::new())),
            buffer_size: 100,
            enabled: true,
        })
    }

    pub fn with_max_logs(mut self, max_logs: usize) -> Self {
        self.max_logs = max_logs;
        self
    }

    pub fn with_buffer_size(mut self, buffer_size: usize) -> Self {
        self.buffer_size = buffer_size;
        self
    }

    pub fn with_log_key(mut self, key: &str) -> Self {
        self.log_key = key.to_string();
        self
    }

    pub fn set_enabled(&mut self, enabled: bool) {
        self.enabled = enabled;
        if !enabled {
            // Flush any remaining buffered logs
            if let Err(e) = self.flush_buffer() {
                eprintln!("Failed to flush buffer when disabling Redis logging: {}", e);
            }
        }
    }

    pub fn log(&self, entry: &LogEntry) -> Result<(), String> {
        if !self.enabled {
            return Ok(());
        }

        let redis_entry = RedisLogEntry::from_log_entry(entry, &self.service_name);
        
        // Add to buffer
        if let Ok(mut buffer) = self.buffer.lock() {
            buffer.push(redis_entry);
            
            // Flush if buffer is full
            if buffer.len() >= self.buffer_size {
                drop(buffer); // Release the lock before flushing
                self.flush_buffer()?;
            }
        }

        Ok(())
    }

    pub fn log_with_metadata(&self, entry: &LogEntry, metadata: HashMap<String, serde_json::Value>) -> Result<(), String> {
        if !self.enabled {
            return Ok(());
        }

        let mut redis_entry = RedisLogEntry::from_log_entry(entry, &self.service_name);
        redis_entry.metadata = metadata;
        
        if let Ok(mut buffer) = self.buffer.lock() {
            buffer.push(redis_entry);
            
            if buffer.len() >= self.buffer_size {
                drop(buffer);
                self.flush_buffer()?;
            }
        }

        Ok(())
    }

    pub fn flush_buffer(&self) -> Result<(), String> {
        let entries_to_flush = if let Ok(mut buffer) = self.buffer.lock() {
            let entries = buffer.clone();
            buffer.clear();
            entries
        } else {
            return Err("Failed to lock buffer".to_string());
        };

        if entries_to_flush.is_empty() {
            return Ok(());
        }

        // Ensure we have a connection
        self.ensure_connected()?;

        let mut conn_guard = self.connection.lock().unwrap();
        if let Some(conn) = conn_guard.as_mut() {
            // Convert entries to JSON strings
            let json_entries: Vec<String> = entries_to_flush.iter()
                .map(|entry| serde_json::to_string(entry).unwrap_or_default())
                .collect();

            // Push to Redis list
            for json_entry in json_entries {
                let _: () = redis::cmd("LPUSH")
                    .arg(&self.log_key)
                    .arg(&json_entry)
                    .query(conn)
                    .map_err(|e| format!("Failed to push log to Redis: {}", e))?;
            }

            // Trim the list to max_logs
            let _: () = redis::cmd("LTRIM")
                .arg(&self.log_key)
                .arg(0)
                .arg(self.max_logs as isize - 1)
                .query(conn)
                .map_err(|e| format!("Failed to trim Redis log list: {}", e))?;
        }

        Ok(())
    }

    pub fn get_recent_logs(&self, count: usize) -> Result<Vec<RedisLogEntry>, String> {
        self.ensure_connected()?;

        let mut conn_guard = self.connection.lock().unwrap();
        if let Some(conn) = conn_guard.as_mut() {
            let json_logs: Vec<String> = redis::cmd("LRANGE")
                .arg(&self.log_key)
                .arg(0)
                .arg(count as isize - 1)
                .query(conn)
                .map_err(|e| format!("Failed to get logs from Redis: {}", e))?;

            let mut logs = Vec::new();
            for json_log in json_logs {
                if let Ok(log_entry) = serde_json::from_str::<RedisLogEntry>(&json_log) {
                    logs.push(log_entry);
                }
            }

            Ok(logs)
        } else {
            Err("No Redis connection available".to_string())
        }
    }

    pub fn get_logs_by_level(&self, level: LogLevel, count: usize) -> Result<Vec<RedisLogEntry>, String> {
        let all_logs = self.get_recent_logs(self.max_logs)?;
        let level_str = level.as_str();
        
        let filtered_logs: Vec<RedisLogEntry> = all_logs.into_iter()
            .filter(|log| log.level == level_str)
            .take(count)
            .collect();

        Ok(filtered_logs)
    }

    pub fn get_logs_by_module(&self, module: &str, count: usize) -> Result<Vec<RedisLogEntry>, String> {
        let all_logs = self.get_recent_logs(self.max_logs)?;
        
        let filtered_logs: Vec<RedisLogEntry> = all_logs.into_iter()
            .filter(|log| log.module == module)
            .take(count)
            .collect();

        Ok(filtered_logs)
    }

    pub fn search_logs(&self, query: &str, count: usize) -> Result<Vec<RedisLogEntry>, String> {
        let all_logs = self.get_recent_logs(self.max_logs)?;
        let query_lower = query.to_lowercase();
        
        let filtered_logs: Vec<RedisLogEntry> = all_logs.into_iter()
            .filter(|log| {
                log.message.to_lowercase().contains(&query_lower) ||
                log.module.to_lowercase().contains(&query_lower)
            })
            .take(count)
            .collect();

        Ok(filtered_logs)
    }

    pub fn clear_logs(&self) -> Result<(), String> {
        self.ensure_connected()?;

        let mut conn_guard = self.connection.lock().unwrap();
        if let Some(conn) = conn_guard.as_mut() {
            let _: () = redis::cmd("DEL")
                .arg(&self.log_key)
                .query(conn)
                .map_err(|e| format!("Failed to clear Redis logs: {}", e))?;
        }

        Ok(())
    }

    pub fn get_log_stats(&self) -> Result<RedisLogStats, String> {
        let all_logs = self.get_recent_logs(self.max_logs)?;
        let mut stats = RedisLogStats::new();
        
        for log in &all_logs {
            stats.total_logs += 1;
            *stats.level_counts.entry(log.level.clone()).or_insert(0) += 1;
            *stats.module_counts.entry(log.module.clone()).or_insert(0) += 1;
        }

        if let Some(first_log) = all_logs.first() {
            stats.latest_timestamp = Some(first_log.timestamp);
        }
        if let Some(last_log) = all_logs.last() {
            stats.earliest_timestamp = Some(last_log.timestamp);
        }

        Ok(stats)
    }

    fn ensure_connected(&self) -> Result<(), String> {
        let mut conn_guard = self.connection.lock().unwrap();
        
        if conn_guard.is_none() {
            if let Some(client) = &self.client {
                let conn = client.get_connection()
                    .map_err(|e| format!("Failed to connect to Redis: {}", e))?;
                *conn_guard = Some(conn);
            } else {
                return Err("No Redis client available".to_string());
            }
        }

        Ok(())
    }

    pub fn test_connection(&self) -> Result<(), String> {
        self.ensure_connected()?;
        
        let mut conn_guard = self.connection.lock().unwrap();
        if let Some(conn) = conn_guard.as_mut() {
            let _: String = redis::cmd("PING")
                .query(conn)
                .map_err(|e| format!("Redis connection test failed: {}", e))?;
            Ok(())
        } else {
            Err("No Redis connection available".to_string())
        }
    }
}

#[cfg(feature = "redis-logging")]
impl Drop for RedisLogHandler {
    fn drop(&mut self) {
        // Flush any remaining logs when dropping
        if let Err(e) = self.flush_buffer() {
            eprintln!("Failed to flush Redis log buffer on drop: {}", e);
        }
    }
}

#[derive(Debug, Clone)]
pub struct RedisLogStats {
    pub total_logs: usize,
    pub level_counts: HashMap<String, usize>,
    pub module_counts: HashMap<String, usize>,
    pub latest_timestamp: Option<u64>,
    pub earliest_timestamp: Option<u64>,
}

impl RedisLogStats {
    pub fn new() -> Self {
        Self {
            total_logs: 0,
            level_counts: HashMap::new(),
            module_counts: HashMap::new(),
            latest_timestamp: None,
            earliest_timestamp: None,
        }
    }
}

// Mock Redis implementation for testing when Redis is not available
pub struct MockRedisLogHandler {
    logs: Arc<Mutex<Vec<RedisLogEntry>>>,
    service_name: String,
    max_logs: usize,
}

impl MockRedisLogHandler {
    pub fn new(service_name: &str) -> Self {
        Self {
            logs: Arc::new(Mutex::new(Vec::new())),
            service_name: service_name.to_string(),
            max_logs: 10000,
        }
    }

    pub fn log(&self, entry: &LogEntry) -> Result<(), String> {
        let redis_entry = RedisLogEntry::from_log_entry(entry, &self.service_name);
        
        if let Ok(mut logs) = self.logs.lock() {
            logs.insert(0, redis_entry); // Insert at beginning for LIFO behavior like Redis
            
            // Trim to max_logs
            if logs.len() > self.max_logs {
                logs.truncate(self.max_logs);
            }
        }

        Ok(())
    }

    pub fn get_recent_logs(&self, count: usize) -> Result<Vec<RedisLogEntry>, String> {
        if let Ok(logs) = self.logs.lock() {
            Ok(logs.iter().take(count).cloned().collect())
        } else {
            Err("Failed to lock logs".to_string())
        }
    }

    pub fn clear_logs(&self) -> Result<(), String> {
        if let Ok(mut logs) = self.logs.lock() {
            logs.clear();
            Ok(())
        } else {
            Err("Failed to lock logs".to_string())
        }
    }
}