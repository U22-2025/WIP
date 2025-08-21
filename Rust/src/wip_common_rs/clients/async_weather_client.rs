use crate::wip_common_rs::clients::utils::packet_id_generator::PacketIDGenerator12Bit;
use crate::wip_common_rs::packet::types::query_packet::{QueryRequest, QueryResponse};
use async_trait::async_trait;
use dashmap::DashMap;
use log::{debug, info, warn};
use std::collections::HashMap;
use std::net::SocketAddr;
use std::sync::Arc;
use std::time::{Duration, Instant};
use tokio::net::UdpSocket;
use tokio::sync::{Mutex, RwLock, Semaphore};
use tokio::time::{sleep, timeout};

#[derive(Debug, Clone)]
pub struct CacheEntry<T> {
    pub data: T,
    pub expires_at: Instant,
    pub hit_count: usize,
}

impl<T> CacheEntry<T> {
    pub fn new(data: T, ttl: Duration) -> Self {
        Self {
            data,
            expires_at: Instant::now() + ttl,
            hit_count: 0,
        }
    }

    pub fn is_expired(&self) -> bool {
        Instant::now() > self.expires_at
    }

    pub fn increment_hit(&mut self) {
        self.hit_count += 1;
    }
}

#[derive(Debug, Clone)]
pub struct RetryConfig {
    pub max_attempts: usize,
    pub initial_delay: Duration,
    pub max_delay: Duration,
    pub backoff_multiplier: f64,
}

impl Default for RetryConfig {
    fn default() -> Self {
        Self {
            max_attempts: 3,
            initial_delay: Duration::from_millis(100),
            max_delay: Duration::from_secs(5),
            backoff_multiplier: 2.0,
        }
    }
}

#[derive(Debug, Clone)]
pub struct ClientConfig {
    pub timeout: Duration,
    pub cache_ttl: Duration,
    pub max_cache_size: usize,
    pub max_concurrent_requests: usize,
    pub retry_config: RetryConfig,
    pub enable_debug_logging: bool,
}

impl Default for ClientConfig {
    fn default() -> Self {
        Self {
            timeout: Duration::from_secs(10),
            cache_ttl: Duration::from_secs(300),
            max_cache_size: 1000,
            max_concurrent_requests: 100,
            retry_config: RetryConfig::default(),
            enable_debug_logging: false,
        }
    }
}

pub struct ConnectionPool {
    sockets: Vec<Arc<UdpSocket>>,
    current_index: Arc<Mutex<usize>>,
}

impl ConnectionPool {
    pub async fn new(pool_size: usize) -> tokio::io::Result<Self> {
        let mut sockets = Vec::with_capacity(pool_size);
        
        for _ in 0..pool_size {
            let socket = UdpSocket::bind("0.0.0.0:0").await?;
            sockets.push(Arc::new(socket));
        }
        
        Ok(Self {
            sockets,
            current_index: Arc::new(Mutex::new(0)),
        })
    }
    
    pub async fn get_socket(&self) -> Arc<UdpSocket> {
        let mut index = self.current_index.lock().await;
        let socket = self.sockets[*index].clone();
        *index = (*index + 1) % self.sockets.len();
        socket
    }
}

#[async_trait]
pub trait AsyncWeatherClient {
    async fn query_async(&self, request: QueryRequest) -> Result<QueryResponse, Box<dyn std::error::Error + Send + Sync>>;
    async fn query_with_cache(&self, request: QueryRequest) -> Result<QueryResponse, Box<dyn std::error::Error + Send + Sync>>;
    async fn query_batch(&self, requests: Vec<QueryRequest>) -> Vec<Result<QueryResponse, Box<dyn std::error::Error + Send + Sync>>>;
    async fn clear_cache(&self);
    fn get_cache_stats(&self) -> HashMap<String, usize>;
}

pub struct WeatherClientAsync {
    host: String,
    port: u16,
    addr: SocketAddr,
    config: ClientConfig,
    pidg: Arc<Mutex<PacketIDGenerator12Bit>>,
    cache: Arc<DashMap<String, CacheEntry<QueryResponse>>>,
    connection_pool: Arc<ConnectionPool>,
    semaphore: Arc<Semaphore>,
    stats: Arc<RwLock<ClientStats>>,
}

#[derive(Debug, Default, Clone)]
pub struct ClientStats {
    pub total_requests: usize,
    pub cache_hits: usize,
    pub cache_misses: usize,
    pub retry_attempts: usize,
    pub timeouts: usize,
    pub errors: usize,
}

impl WeatherClientAsync {
    pub async fn new(host: &str, port: u16) -> tokio::io::Result<Self> {
        Self::with_config(host, port, ClientConfig::default()).await
    }

    pub async fn with_config(host: &str, port: u16, config: ClientConfig) -> tokio::io::Result<Self> {
        // localhostを127.0.0.1に解決
        let resolved_host = if host == "localhost" {
            "127.0.0.1"
        } else {
            host
        };
        
        let addr: SocketAddr = format!("{}:{}", resolved_host, port).parse()
            .map_err(|e| tokio::io::Error::new(tokio::io::ErrorKind::InvalidInput, e))?;

        let connection_pool = Arc::new(ConnectionPool::new(5).await?);
        let semaphore = Arc::new(Semaphore::new(config.max_concurrent_requests));

        if config.enable_debug_logging {
            env_logger::init();
        }

        Ok(Self {
            host: host.to_string(),
            port,
            addr,
            config,
            pidg: Arc::new(Mutex::new(PacketIDGenerator12Bit::new())),
            cache: Arc::new(DashMap::new()),
            connection_pool,
            semaphore,
            stats: Arc::new(RwLock::new(ClientStats::default())),
        })
    }

    async fn generate_packet_id(&self) -> u16 {
        let mut pidg = self.pidg.lock().await;
        pidg.next_id()
    }

    async fn send_with_retry<F, Fut, T>(&self, operation: F) -> Result<T, Box<dyn std::error::Error + Send + Sync>>
    where
        F: Fn() -> Fut,
        Fut: std::future::Future<Output = Result<T, Box<dyn std::error::Error + Send + Sync>>>,
    {
        let mut attempts = 0;
        let mut delay = self.config.retry_config.initial_delay;

        loop {
            attempts += 1;

            match operation().await {
                Ok(result) => {
                    if attempts > 1 {
                        let mut stats = self.stats.write().await;
                        stats.retry_attempts += attempts - 1;
                    }
                    return Ok(result);
                }
                Err(e) => {
                    if attempts >= self.config.retry_config.max_attempts {
                        let mut stats = self.stats.write().await;
                        stats.errors += 1;
                        return Err(e);
                    }

                    warn!("Attempt {} failed, retrying after {:?}: {}", attempts, delay, e);
                    sleep(delay).await;
                    
                    delay = std::cmp::min(
                        Duration::from_millis(
                            (delay.as_millis() as f64 * self.config.retry_config.backoff_multiplier) as u64
                        ),
                        self.config.retry_config.max_delay,
                    );
                }
            }
        }
    }

    async fn receive_with_id(&self, socket: &UdpSocket, expected_id: u16) -> Result<Vec<u8>, Box<dyn std::error::Error + Send + Sync>> {
        let mut buf = [0u8; 1024];
        
        let result = timeout(self.config.timeout, async {
            loop {
                let (len, _) = socket.recv_from(&mut buf).await?;
                let data = &buf[..len];
                
                if data.len() >= 2 {
                    let raw = u16::from_le_bytes([data[0], data[1]]);
                    let packet_id = (raw >> 4) & 0x0FFF; // version(4bit) + packet_id(12bit)
                    if packet_id == expected_id {
                        return Ok(data.to_vec());
                    }
                }
            }
        }).await;

        match result {
            Ok(data) => data,
            Err(_) => {
                let mut stats = self.stats.write().await;
                stats.timeouts += 1;
                Err("Timeout waiting for response".into())
            }
        }
    }

    fn cache_key(&self, request: &QueryRequest) -> String {
        format!("{}:{}:{}", request.get_packet_id(), request.get_packet_type(), 
                std::ptr::addr_of!(*request) as usize)
    }

    async fn cleanup_expired_cache(&self) {
        let _now = Instant::now();
        let mut to_remove = Vec::new();
        
        for entry in self.cache.iter() {
            if entry.value().is_expired() {
                to_remove.push(entry.key().clone());
            }
        }
        
        for key in to_remove {
            self.cache.remove(&key);
        }
        
        if self.cache.len() > self.config.max_cache_size {
            let mut entries: Vec<_> = self.cache.iter()
                .map(|entry| (entry.key().clone(), entry.value().hit_count))
                .collect();
            
            entries.sort_by_key(|(_, hit_count)| *hit_count);
            
            let remove_count = self.cache.len() - self.config.max_cache_size * 3 / 4;
            for (key, _) in entries.into_iter().take(remove_count) {
                self.cache.remove(&key);
            }
        }
    }
}

#[async_trait]
impl AsyncWeatherClient for WeatherClientAsync {
    async fn query_async(&self, mut request: QueryRequest) -> Result<QueryResponse, Box<dyn std::error::Error + Send + Sync>> {
        let _permit = self.semaphore.acquire().await?;
        
        let mut stats = self.stats.write().await;
        stats.total_requests += 1;
        drop(stats);

        let packet_id = self.generate_packet_id().await;
        request.set_packet_id(packet_id);
        
        let operation = || async {
            let socket = self.connection_pool.get_socket().await;
            let data = request.to_bytes();
            
            debug!("Sending {} bytes to {}", data.len(), self.addr);
            socket.send_to(&data, &self.addr).await?;
            
            let response_data = self.receive_with_id(&socket, packet_id).await?;
            let response = QueryResponse::from_bytes(&response_data).ok_or("Failed to parse QueryResponse")?;
            
            info!("Received response for packet ID {}", packet_id);
            Ok(response)
        };

        self.send_with_retry(operation).await
    }

    async fn query_with_cache(&self, request: QueryRequest) -> Result<QueryResponse, Box<dyn std::error::Error + Send + Sync>> {
        let cache_key = self.cache_key(&request);
        
        if let Some(mut entry) = self.cache.get_mut(&cache_key) {
            if !entry.is_expired() {
                entry.increment_hit();
                let mut stats = self.stats.write().await;
                stats.cache_hits += 1;
                debug!("Cache hit for key: {}", cache_key);
                return Ok(entry.data.clone());
            }
        }
        
        let mut stats = self.stats.write().await;
        stats.cache_misses += 1;
        drop(stats);
        
        debug!("Cache miss for key: {}", cache_key);
        
        let response = self.query_async(request).await?;
        
        self.cache.insert(
            cache_key,
            CacheEntry::new(response.clone(), self.config.cache_ttl),
        );
        
        self.cleanup_expired_cache().await;
        
        Ok(response)
    }

    async fn query_batch(&self, requests: Vec<QueryRequest>) -> Vec<Result<QueryResponse, Box<dyn std::error::Error + Send + Sync>>> {
        let mut handles = Vec::new();
        
        for request in requests {
            let client = self.clone();
            let handle = tokio::spawn(async move {
                client.query_with_cache(request).await
            });
            handles.push(handle);
        }
        
        let mut results = Vec::new();
        for handle in handles {
            match handle.await {
                Ok(result) => results.push(result),
                Err(e) => results.push(Err(e.into())),
            }
        }
        
        results
    }

    async fn clear_cache(&self) {
        self.cache.clear();
        info!("Cache cleared");
    }

    fn get_cache_stats(&self) -> HashMap<String, usize> {
        let mut stats = HashMap::new();
        stats.insert("cache_size".to_string(), self.cache.len());
        
        let mut total_hits = 0;
        for entry in self.cache.iter() {
            total_hits += entry.value().hit_count;
        }
        stats.insert("total_cache_hits".to_string(), total_hits);
        
        stats
    }
}

impl Clone for WeatherClientAsync {
    fn clone(&self) -> Self {
        Self {
            host: self.host.clone(),
            port: self.port,
            addr: self.addr,
            config: self.config.clone(),
            pidg: self.pidg.clone(),
            cache: self.cache.clone(),
            connection_pool: self.connection_pool.clone(),
            semaphore: self.semaphore.clone(),
            stats: self.stats.clone(),
        }
    }
}

impl WeatherClientAsync {
    pub async fn get_stats(&self) -> ClientStats {
        self.stats.read().await.clone()
    }
    
    pub async fn reset_stats(&self) {
        let mut stats = self.stats.write().await;
        *stats = ClientStats::default();
    }
    
    pub async fn set_timeout(&mut self, timeout: Duration) {
        self.config.timeout = timeout;
    }
    
    pub async fn set_cache_ttl(&mut self, ttl: Duration) {
        self.config.cache_ttl = ttl;
    }
}
