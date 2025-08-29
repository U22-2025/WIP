use crate::wip_common_rs::clients::utils::packet_id_generator::PacketIDGenerator12Bit;
use crate::wip_common_rs::packet::types::query_packet::{QueryRequest, QueryResponse};
use async_trait::async_trait;
use log::{debug, info, warn};
use std::collections::HashMap;
use std::net::SocketAddr;
use std::sync::Arc;
use std::time::{Duration, Instant};
use tokio::net::{UdpSocket, lookup_host};
use tokio::sync::{Mutex, RwLock, Semaphore};
use tokio::time::{sleep, timeout};

#[derive(Debug, Clone)]
pub struct QueryOptimization {
    pub enable_compression: bool,
    pub enable_batching: bool,
    pub batch_size: usize,
    pub batch_timeout: Duration,
    pub enable_caching: bool,
    pub cache_ttl: Duration,
}

impl Default for QueryOptimization {
    fn default() -> Self {
        Self {
            enable_compression: false,
            enable_batching: true,
            batch_size: 10,
            batch_timeout: Duration::from_millis(100),
            enable_caching: true,
            cache_ttl: Duration::from_secs(60),
        }
    }
}

#[derive(Debug, Clone)]
pub struct QueryClientConfig {
    pub timeout: Duration,
    pub max_concurrent_queries: usize,
    pub retry_attempts: usize,
    pub retry_delay: Duration,
    pub optimization: QueryOptimization,
    pub enable_debug: bool,
}

impl Default for QueryClientConfig {
    fn default() -> Self {
        Self {
            timeout: Duration::from_secs(5),
            max_concurrent_queries: 50,
            retry_attempts: 3,
            retry_delay: Duration::from_millis(200),
            optimization: QueryOptimization::default(),
            enable_debug: false,
        }
    }
}

#[derive(Debug, Clone)]
pub struct QueryCacheEntry {
    pub response: QueryResponse,
    pub created_at: Instant,
    pub access_count: usize,
}

impl QueryCacheEntry {
    pub fn new(response: QueryResponse, _ttl: Duration) -> Self {
        Self {
            response,
            created_at: Instant::now(),
            access_count: 0,
        }
    }
    
    pub fn is_expired(&self, ttl: Duration) -> bool {
        self.created_at.elapsed() > ttl
    }
    
    pub fn access(&mut self) -> QueryResponse {
        self.access_count += 1;
        self.response.clone()
    }
}

#[derive(Debug, Default, Clone)]
pub struct QueryStats {
    pub total_queries: usize,
    pub successful_queries: usize,
    pub failed_queries: usize,
    pub cache_hits: usize,
    pub cache_misses: usize,
    pub retry_attempts: usize,
    pub timeouts: usize,
    pub batched_queries: usize,
    pub optimized_queries: usize,
}

#[async_trait]
pub trait QueryClient {
    async fn execute_query(&self, query: QueryRequest) -> Result<QueryResponse, Box<dyn std::error::Error + Send + Sync>>;
    async fn execute_query_with_optimization(&self, query: QueryRequest) -> Result<QueryResponse, Box<dyn std::error::Error + Send + Sync>>;
    async fn execute_batch_queries(&self, queries: Vec<QueryRequest>) -> Vec<Result<QueryResponse, Box<dyn std::error::Error + Send + Sync>>>;
    async fn execute_optimized_batch(&self, queries: Vec<QueryRequest>) -> Vec<Result<QueryResponse, Box<dyn std::error::Error + Send + Sync>>>;
    fn clear_cache(&self);
    fn get_stats(&self) -> QueryStats;
}

#[derive(Debug)]
pub struct QueryClientImpl {
    host: String,
    port: u16,
    addr: SocketAddr,
    config: QueryClientConfig,
    socket: Arc<UdpSocket>,
    pidg: Arc<Mutex<PacketIDGenerator12Bit>>,
    cache: Arc<RwLock<HashMap<String, QueryCacheEntry>>>,
    semaphore: Arc<Semaphore>,
    stats: Arc<RwLock<QueryStats>>,
}

impl QueryClientImpl {
    pub async fn new(host: &str, port: u16) -> tokio::io::Result<Self> {
        Self::with_config(host, port, QueryClientConfig::default()).await
    }

    pub async fn with_config(host: &str, port: u16, config: QueryClientConfig) -> tokio::io::Result<Self> {
        // localhostをwip.ncc.onlに解決
        let resolved_host = if host == "localhost" {
            "wip.ncc.onl"
        } else {
            host
        };
        
        // Resolve FQDN to SocketAddr (accept hostnames like WeatherClient)
        let mut iter = lookup_host((resolved_host, port)).await
            .map_err(|e| tokio::io::Error::new(
                tokio::io::ErrorKind::InvalidInput,
                format!("DNS resolve failed for {}:{}: {}", resolved_host, port, e),
            ))?;
        let addr: SocketAddr = iter.next().ok_or_else(|| tokio::io::Error::new(
            tokio::io::ErrorKind::InvalidInput,
            format!("No address found for {}:{}", resolved_host, port),
        ))?;

        let socket = Arc::new(UdpSocket::bind("0.0.0.0:0").await?);
        let semaphore = Arc::new(Semaphore::new(config.max_concurrent_queries));

        if config.enable_debug {
            env_logger::init();
        }

        Ok(Self {
            host: host.to_string(),
            port,
            addr,
            config,
            socket,
            pidg: Arc::new(Mutex::new(PacketIDGenerator12Bit::new())),
            cache: Arc::new(RwLock::new(HashMap::new())),
            semaphore,
            stats: Arc::new(RwLock::new(QueryStats::default())),
        })
    }

    async fn generate_packet_id(&self) -> u16 {
        let mut pidg = self.pidg.lock().await;
        pidg.next_id()
    }

    fn query_cache_key(&self, query: &QueryRequest) -> String {
        format!("{}:{}:{}", 
            query.get_packet_type(), 
            query.get_packet_id(),
            std::ptr::addr_of!(*query) as usize)
    }

    async fn get_cached_response(&self, query: &QueryRequest) -> Option<QueryResponse> {
        if !self.config.optimization.enable_caching {
            return None;
        }

        let cache_key = self.query_cache_key(query);
        let mut cache = self.cache.write().await;
        
        if let Some(entry) = cache.get_mut(&cache_key) {
            if !entry.is_expired(self.config.optimization.cache_ttl) {
                let mut stats = self.stats.write().await;
                stats.cache_hits += 1;
                debug!("Cache hit for query: {}", cache_key);
                return Some(entry.access());
            } else {
                cache.remove(&cache_key);
            }
        }
        
        let mut stats = self.stats.write().await;
        stats.cache_misses += 1;
        None
    }

    async fn cache_response(&self, query: &QueryRequest, response: &QueryResponse) {
        if !self.config.optimization.enable_caching {
            return;
        }

        let cache_key = self.query_cache_key(query);
        let entry = QueryCacheEntry::new(response.clone(), self.config.optimization.cache_ttl);
        
        let mut cache = self.cache.write().await;
        cache.insert(cache_key, entry);
        
        self.cleanup_expired_cache(&mut cache).await;
    }

    async fn cleanup_expired_cache(&self, cache: &mut HashMap<String, QueryCacheEntry>) {
        let ttl = self.config.optimization.cache_ttl;
        cache.retain(|_, entry| !entry.is_expired(ttl));
    }

    async fn send_query_with_retry(&self, mut query: QueryRequest) -> Result<QueryResponse, Box<dyn std::error::Error + Send + Sync>> {
        let mut attempts = 0;
        let packet_id = self.generate_packet_id().await;
        query.set_packet_id(packet_id);

        loop {
            attempts += 1;
            
            match self.send_single_query(&query).await {
                Ok(response) => {
                    if attempts > 1 {
                        let mut stats = self.stats.write().await;
                        stats.retry_attempts += attempts - 1;
                    }
                    return Ok(response);
                }
                Err(e) => {
                    if attempts >= self.config.retry_attempts {
                        let mut stats = self.stats.write().await;
                        stats.failed_queries += 1;
                        return Err(e);
                    }
                    
                    warn!("Query attempt {} failed, retrying: {}", attempts, e);
                    sleep(self.config.retry_delay).await;
                }
            }
        }
    }

    async fn send_single_query(&self, query: &QueryRequest) -> Result<QueryResponse, Box<dyn std::error::Error + Send + Sync>> {
        let data = query.to_bytes();
        let packet_id = query.get_packet_id();
        
        debug!("Sending query with packet ID {} to {}", packet_id, self.addr);
        self.socket.send_to(&data, &self.addr).await?;

        let result = timeout(self.config.timeout, async {
            let mut buf = [0u8; 2048];
            loop {
                let (len, _) = self.socket.recv_from(&mut buf).await?;
                let response_data = &buf[..len];
                
                if response_data.len() >= 2 {
                    let raw = u16::from_le_bytes([response_data[0], response_data[1]]);
                    let response_packet_id = (raw >> 4) & 0x0FFF; // version(4bit) + packet_id(12bit)
                    if response_packet_id == packet_id {
                        let response = QueryResponse::from_bytes(response_data).ok_or("Failed to parse QueryResponse")?;
                        return Ok(response);
                    }
                }
            }
        }).await;

        match result {
            Ok(response) => {
                info!("Received query response for packet ID {}", packet_id);
                response
            }
            Err(_) => {
                let mut stats = self.stats.write().await;
                stats.timeouts += 1;
                Err("Query timeout".into())
            }
        }
    }

    async fn optimize_queries(&self, queries: Vec<QueryRequest>) -> Vec<QueryRequest> {
        if !self.config.optimization.enable_compression && !self.config.optimization.enable_batching {
            return queries;
        }

        let optimized = queries;
        
        if self.config.optimization.enable_batching && optimized.len() > self.config.optimization.batch_size {
            debug!("Optimizing {} queries with batching", optimized.len());
            let mut stats = self.stats.write().await;
            stats.optimized_queries += optimized.len();
        }

        optimized
    }
}

#[async_trait]
impl QueryClient for QueryClientImpl {
    async fn execute_query(&self, query: QueryRequest) -> Result<QueryResponse, Box<dyn std::error::Error + Send + Sync>> {
        let _permit = self.semaphore.acquire().await?;
        
        let mut stats = self.stats.write().await;
        stats.total_queries += 1;
        drop(stats);

        let response = self.send_query_with_retry(query).await?;
        
        let mut stats = self.stats.write().await;
        stats.successful_queries += 1;
        
        Ok(response)
    }

    async fn execute_query_with_optimization(&self, query: QueryRequest) -> Result<QueryResponse, Box<dyn std::error::Error + Send + Sync>> {
        if let Some(cached_response) = self.get_cached_response(&query).await {
            return Ok(cached_response);
        }

        let response = self.execute_query(query.clone()).await?;
        self.cache_response(&query, &response).await;
        
        Ok(response)
    }

    async fn execute_batch_queries(&self, queries: Vec<QueryRequest>) -> Vec<Result<QueryResponse, Box<dyn std::error::Error + Send + Sync>>> {
        let mut handles = Vec::new();
        
        for query in queries {
            let client = self.clone();
            let handle = tokio::spawn(async move {
                client.execute_query(query).await
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

    async fn execute_optimized_batch(&self, queries: Vec<QueryRequest>) -> Vec<Result<QueryResponse, Box<dyn std::error::Error + Send + Sync>>> {
        let optimized_queries = self.optimize_queries(queries).await;
        
        if self.config.optimization.enable_batching {
            let mut stats = self.stats.write().await;
            stats.batched_queries += optimized_queries.len();
            drop(stats);
        }

        let mut handles = Vec::new();
        
        for query in optimized_queries {
            let client = self.clone();
            let handle = tokio::spawn(async move {
                client.execute_query_with_optimization(query).await
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

    fn clear_cache(&self) {
        let cache = self.cache.clone();
        tokio::spawn(async move {
            let mut cache_guard = cache.write().await;
            cache_guard.clear();
            info!("Query cache cleared");
        });
    }

    fn get_stats(&self) -> QueryStats {
        // Simplified synchronous version - return default for now
        QueryStats::default()
    }
}

impl Clone for QueryClientImpl {
    fn clone(&self) -> Self {
        Self {
            host: self.host.clone(),
            port: self.port,
            addr: self.addr,
            config: self.config.clone(),
            socket: self.socket.clone(),
            pidg: self.pidg.clone(),
            cache: self.cache.clone(),
            semaphore: self.semaphore.clone(),
            stats: self.stats.clone(),
        }
    }
}

impl QueryClientImpl {
    pub async fn get_detailed_stats(&self) -> QueryStats {
        self.stats.read().await.clone()
    }
    
    pub async fn reset_stats(&self) {
        let mut stats = self.stats.write().await;
        *stats = QueryStats::default();
    }
    
    pub async fn set_timeout(&mut self, timeout: Duration) {
        self.config.timeout = timeout;
    }
    
    pub async fn enable_optimization(&mut self, enable: bool) {
        self.config.optimization.enable_caching = enable;
        self.config.optimization.enable_batching = enable;
    }
    
    pub async fn get_cache_size(&self) -> usize {
        self.cache.read().await.len()
    }
}
