#[cfg(feature = "redis-logging")]
use redis;
use std::collections::HashMap;
use std::sync::{Arc, Mutex};
use std::time::{SystemTime, UNIX_EPOCH};
use serde::{Serialize, Deserialize};
use crate::wip_common_rs::utils::log_config::{LogEntry, LogLevel};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RedisLogEntry { pub timestamp: u64, pub level: String, pub module: String, pub message: String, pub hostname: String, pub service: String, pub metadata: HashMap<String, serde_json::Value> }
impl RedisLogEntry { pub fn from_log_entry(entry:&LogEntry, service:&str)->Self{ Self{ timestamp: SystemTime::now().duration_since(UNIX_EPOCH).unwrap_or_default().as_millis() as u64, level: entry.level.as_str().to_string(), module: entry.module.clone(), message: entry.message.clone(), hostname: gethostname::gethostname().to_string_lossy().to_string(), service: service.to_string(), metadata: HashMap::new() } } }

pub struct RedisLogHandler {
    #[cfg(feature = "redis-logging")] client: Option<redis::Client>,
    #[cfg(feature = "redis-logging")]
    connection: Arc<Mutex<Option<redis::Connection>>>,
    #[cfg(not(feature = "redis-logging"))]
    connection: Arc<Mutex<Option<()>>>,
    service_name: String,
    log_key: String,
    max_logs: usize,
    buffer: Arc<Mutex<Vec<RedisLogEntry>>>,
}
impl RedisLogHandler {
    pub fn new(redis_url: Option<&str>, service_name:&str)->Self{
        #[cfg(feature = "redis-logging")]
        let client = if let Some(url) = redis_url { 
            redis::Client::open(url).ok() 
        } else { 
            None 
        };
        #[cfg(not(feature = "redis-logging"))]
        let client: Option<()> = None;
        Self{ #[cfg(feature="redis-logging")] client, connection: Arc::new(Mutex::new(None)), service_name: service_name.to_string(), log_key: format!("wip:logs:{}", service_name), max_logs: 10000, buffer: Arc::new(Mutex::new(Vec::new())) }
    }
    pub fn log(&self, entry:&LogEntry)->Result<(),String>{ let redis_entry=RedisLogEntry::from_log_entry(entry, &self.service_name); if self.connection.lock().unwrap().is_none(){ if let Err(e)=self.flush_to_buffer(redis_entry){ return Err(e); } return Ok(()); } self.push_to_redis(redis_entry) }
    fn flush_to_buffer(&self, entry: RedisLogEntry)->Result<(),String>{ let mut buf=self.buffer.lock().unwrap(); buf.push(entry); if buf.len()>self.max_logs { buf.remove(0); } Ok(()) }
    fn push_to_redis(&self, entry: RedisLogEntry)->Result<(),String>{ let mut conn_guard=self.connection.lock().unwrap(); if let Some(conn) = conn_guard.as_mut(){ let json = serde_json::to_string(&entry).map_err(|e| format!("Failed to serialize log entry: {}", e))?; #[cfg(feature="redis-logging")] { let _: () = redis::cmd("LPUSH").arg(&self.log_key).arg(json).query(conn).map_err(|e| format!("Failed to push log to Redis: {}", e))?; let _: () = redis::cmd("LTRIM").arg(&self.log_key).arg(0).arg(self.max_logs as isize - 1).query(conn).map_err(|e| format!("Failed to trim Redis logs: {}", e))?; } Ok(()) } else { Err("No Redis connection available".into()) } }
    pub fn flush_buffer(&self)->Result<(),String>{ let mut buf=self.buffer.lock().unwrap(); while let Some(entry)=buf.pop(){ let _ = self.push_to_redis(entry); } Ok(()) }
    pub fn get_recent_logs(&self, count: usize)->Result<Vec<RedisLogEntry>,String>{ let mut conn_guard=self.connection.lock().unwrap(); if let Some(conn) = conn_guard.as_mut(){ #[cfg(feature="redis-logging")] { let logs:Vec<String> = redis::cmd("LRANGE").arg(&self.log_key).arg(0).arg((count as isize)-1).query(conn).map_err(|e| format!("Failed to read logs from Redis: {}", e))?; let mut out=Vec::new(); for json in logs { if let Ok(le)=serde_json::from_str::<RedisLogEntry>(&json){ out.push(le); } } return Ok(out); } Ok(Vec::new()) } else { Err("No Redis connection available".into()) } }
    pub fn get_logs_by_level(&self, level:LogLevel, count:usize)->Result<Vec<RedisLogEntry>,String>{ let all=self.get_recent_logs(self.max_logs)?; let ls=level.as_str(); Ok(all.into_iter().filter(|l| l.level==ls).take(count).collect()) }
    pub fn get_logs_by_module(&self, module:&str, count:usize)->Result<Vec<RedisLogEntry>,String>{ let all=self.get_recent_logs(self.max_logs)?; Ok(all.into_iter().filter(|l| l.module==module).take(count).collect()) }
    pub fn search_logs(&self, query:&str, count:usize)->Result<Vec<RedisLogEntry>,String>{ let all=self.get_recent_logs(self.max_logs)?; let q=query.to_lowercase(); Ok(all.into_iter().filter(|l| l.message.to_lowercase().contains(&q)||l.module.to_lowercase().contains(&q)).take(count).collect()) }
    pub fn clear_logs(&self)->Result<(),String>{ self.ensure_connected()?; let mut conn_guard=self.connection.lock().unwrap(); if let Some(conn)=conn_guard.as_mut(){ #[cfg(feature="redis-logging")] { let _: () = redis::cmd("DEL").arg(&self.log_key).query(conn).map_err(|e| format!("Failed to clear Redis logs: {}", e))?; } } Ok(()) }
    pub fn get_log_stats(&self)->Result<RedisLogStats,String>{ let all=self.get_recent_logs(self.max_logs)?; let mut stats=RedisLogStats::new(); for l in &all { stats.total_logs+=1; *stats.level_counts.entry(l.level.clone()).or_insert(0)+=1; *stats.module_counts.entry(l.module.clone()).or_insert(0)+=1; } if let Some(first)=all.first(){ stats.latest_timestamp=Some(first.timestamp);} if let Some(last)=all.last(){ stats.earliest_timestamp=Some(last.timestamp);} Ok(stats) }
    fn ensure_connected(&self)->Result<(),String>{ let mut conn_guard=self.connection.lock().unwrap(); if conn_guard.is_none(){ #[cfg(feature="redis-logging")] { if let Some(client)=&self.client { let conn = client.get_connection().map_err(|e| format!("Failed to connect to Redis: {}", e))?; *conn_guard = Some(conn); } else { return Err("No Redis client available".into()); } } } Ok(()) }
    pub fn test_connection(&self)->Result<(),String>{ self.ensure_connected()?; let mut conn_guard=self.connection.lock().unwrap(); if let Some(conn)=conn_guard.as_mut(){ #[cfg(feature="redis-logging")] { let _: String = redis::cmd("PING").query(conn).map_err(|e| format!("Redis connection test failed: {}", e))?; } Ok(()) } else { Err("No Redis connection available".into()) } }
}

#[derive(Debug, Clone)]
pub struct RedisLogStats { pub total_logs: usize, pub level_counts: HashMap<String, usize>, pub module_counts: HashMap<String, usize>, pub latest_timestamp: Option<u64>, pub earliest_timestamp: Option<u64> }
impl RedisLogStats { pub fn new()->Self{ Self{ total_logs:0, level_counts:HashMap::new(), module_counts:HashMap::new(), latest_timestamp:None, earliest_timestamp:None } } }

pub struct MockRedisLogHandler { logs: Arc<Mutex<Vec<RedisLogEntry>>>, service_name: String, max_logs: usize }
impl MockRedisLogHandler { pub fn new(service_name:&str)->Self{ Self{ logs:Arc::new(Mutex::new(Vec::new())), service_name:service_name.into(), max_logs:10000 } } pub fn log(&self, entry:&LogEntry)->Result<(),String>{ let entry=RedisLogEntry::from_log_entry(entry, &self.service_name); if let Ok(mut logs)=self.logs.lock(){ logs.insert(0, entry); if logs.len()>self.max_logs { logs.truncate(self.max_logs); } } Ok(()) } pub fn get_recent_logs(&self, count:usize)->Result<Vec<RedisLogEntry>,String>{ if let Ok(logs)=self.logs.lock(){ Ok(logs.iter().take(count).cloned().collect()) } else { Err("Failed to lock logs".into()) } } pub fn clear_logs(&self)->Result<(),String>{ if let Ok(mut logs)=self.logs.lock(){ logs.clear(); Ok(()) } else { Err("Failed to lock logs".into()) } } }

