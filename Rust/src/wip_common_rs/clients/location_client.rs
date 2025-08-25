use crate::wip_common_rs::clients::utils::packet_id_generator::PacketIDGenerator12Bit;
use crate::wip_common_rs::packet::types::location_packet::{LocationRequest, LocationResponse, LocationResponseEx};
use crate::wip_common_rs::packet::core::format_base::PacketFormat;
use async_trait::async_trait;
use log::{debug, info};
use std::collections::HashMap;
use std::net::SocketAddr;
use std::sync::Arc;
use std::time::{Duration, Instant};
use tokio::net::UdpSocket;
use tokio::sync::{Mutex, RwLock};
use tokio::time::timeout;

#[derive(Debug, Clone)]
pub struct CoordinateBounds {
    pub min_latitude: f64,
    pub max_latitude: f64,
    pub min_longitude: f64,
    pub max_longitude: f64,
}

impl CoordinateBounds {
    pub fn world() -> Self {
        Self {
            min_latitude: -90.0,
            max_latitude: 90.0,
            min_longitude: -180.0,
            max_longitude: 180.0,
        }
    }
    
    pub fn japan() -> Self {
        Self {
            min_latitude: 24.0,
            max_latitude: 46.0,
            min_longitude: 123.0,
            max_longitude: 146.0,
        }
    }
    
    pub fn contains(&self, latitude: f64, longitude: f64) -> bool {
        latitude >= self.min_latitude 
            && latitude <= self.max_latitude
            && longitude >= self.min_longitude 
            && longitude <= self.max_longitude
    }
}

#[derive(Debug, Clone)]
pub struct LocationClientConfig {
    pub timeout: Duration,
    pub precision_digits: u8,
    pub bounds: CoordinateBounds,
    pub enable_validation: bool,
    pub cache_enabled: bool,
    pub cache_ttl: Duration,
}

impl Default for LocationClientConfig {
    fn default() -> Self {
        Self {
            timeout: Duration::from_secs(5),
            precision_digits: 6,
            bounds: CoordinateBounds::world(),
            enable_validation: true,
            cache_enabled: true,
            cache_ttl: Duration::from_secs(3600),
        }
    }
}

#[derive(Debug, Clone)]
pub struct CachedLocationResult {
    pub area_code: u32,
    pub cached_at: Instant,
    pub precision_level: u8,
}

impl CachedLocationResult {
    pub fn new(area_code: u32, precision_level: u8, _ttl: Duration) -> Self {
        Self {
            area_code,
            cached_at: Instant::now(),
            precision_level,
        }
    }
    
    pub fn is_expired(&self, ttl: Duration) -> bool {
        self.cached_at.elapsed() > ttl
    }
}

#[async_trait]
pub trait LocationClient {
    async fn resolve_coordinates(&self, latitude: f64, longitude: f64) -> Result<u32, Box<dyn std::error::Error + Send + Sync>>;
    async fn resolve_coordinates_with_precision(&self, latitude: f64, longitude: f64, precision: u8) -> Result<u32, Box<dyn std::error::Error + Send + Sync>>;
    async fn batch_resolve(&self, coordinates: Vec<(f64, f64)>) -> Vec<Result<u32, Box<dyn std::error::Error + Send + Sync>>>;
    async fn validate_coordinates(&self, latitude: f64, longitude: f64) -> Result<(), Box<dyn std::error::Error + Send + Sync>>;
    fn clear_cache(&self);
    fn get_cache_stats(&self) -> HashMap<String, usize>;
    
    // Python版との互換性のためのエイリアス
    async fn get_location_data(&self, latitude: f64, longitude: f64) -> Result<u32, Box<dyn std::error::Error + Send + Sync>> {
        self.resolve_coordinates(latitude, longitude).await
    }
    
    async fn get_area_code_simple(&self, latitude: f64, longitude: f64) -> Result<u32, Box<dyn std::error::Error + Send + Sync>> {
        self.resolve_coordinates(latitude, longitude).await
    }
}

#[derive(Debug)]
pub struct LocationClientImpl {
    host: String,
    port: u16,
    addr: SocketAddr,
    config: LocationClientConfig,
    socket: Arc<UdpSocket>,
    pidg: Arc<Mutex<PacketIDGenerator12Bit>>,
    cache: Arc<RwLock<HashMap<String, CachedLocationResult>>>,
    stats: Arc<RwLock<LocationStats>>,
}

#[derive(Debug, Default, Clone)]
pub struct LocationStats {
    pub total_requests: usize,
    pub cache_hits: usize,
    pub cache_misses: usize,
    pub validation_errors: usize,
    pub coordinate_errors: usize,
}

impl LocationClientImpl {
    pub async fn new(host: &str, port: u16) -> tokio::io::Result<Self> {
        Self::with_config(host, port, LocationClientConfig::default()).await
    }

    pub async fn with_config(host: &str, port: u16, config: LocationClientConfig) -> tokio::io::Result<Self> {
        // localhostを127.0.0.1に解決
        let resolved_host = if host == "localhost" {
            "127.0.0.1"
        } else {
            host
        };
        
        let addr: SocketAddr = format!("{}:{}", resolved_host, port).parse()
            .map_err(|e| tokio::io::Error::new(tokio::io::ErrorKind::InvalidInput, e))?;

        let socket = Arc::new(UdpSocket::bind("0.0.0.0:0").await?);

        Ok(Self {
            host: host.to_string(),
            port,
            addr,
            config,
            socket,
            pidg: Arc::new(Mutex::new(PacketIDGenerator12Bit::new())),
            cache: Arc::new(RwLock::new(HashMap::new())),
            stats: Arc::new(RwLock::new(LocationStats::default())),
        })
    }

    async fn generate_packet_id(&self) -> u16 {
        let mut pidg = self.pidg.lock().await;
        pidg.next_id()
    }

    fn normalize_coordinates(&self, latitude: f64, longitude: f64) -> (f64, f64) {
        let precision = 10_f64.powi(self.config.precision_digits as i32);
        let normalized_lat = (latitude * precision).round() / precision;
        let normalized_lon = (longitude * precision).round() / precision;
        (normalized_lat, normalized_lon)
    }

    fn cache_key(&self, latitude: f64, longitude: f64, precision: u8) -> String {
        let (norm_lat, norm_lon) = self.normalize_coordinates(latitude, longitude);
        format!("{}:{}:{}", norm_lat, norm_lon, precision)
    }

    async fn get_from_cache(&self, latitude: f64, longitude: f64, precision: u8) -> Option<u32> {
        if !self.config.cache_enabled {
            return None;
        }

        let key = self.cache_key(latitude, longitude, precision);
        let cache = self.cache.read().await;
        
        if let Some(cached) = cache.get(&key) {
            if !cached.is_expired(self.config.cache_ttl) {
                let mut stats = self.stats.write().await;
                stats.cache_hits += 1;
                debug!("Cache hit for coordinates ({}, {})", latitude, longitude);
                return Some(cached.area_code);
            }
        }
        
        let mut stats = self.stats.write().await;
        stats.cache_misses += 1;
        None
    }

    async fn store_in_cache(&self, latitude: f64, longitude: f64, precision: u8, area_code: u32) {
        if !self.config.cache_enabled {
            return;
        }

        let key = self.cache_key(latitude, longitude, precision);
        let cached_result = CachedLocationResult::new(area_code, precision, self.config.cache_ttl);
        
        let mut cache = self.cache.write().await;
        cache.insert(key, cached_result);
        
        self.cleanup_expired_cache(&mut cache).await;
    }

    async fn cleanup_expired_cache(&self, cache: &mut HashMap<String, CachedLocationResult>) {
        let _now = Instant::now();
        cache.retain(|_, cached| !cached.is_expired(self.config.cache_ttl));
    }

    async fn send_location_request(&self, latitude: f64, longitude: f64) -> Result<u32, Box<dyn std::error::Error + Send + Sync>> {
        let packet_id = self.generate_packet_id().await;
        let request = LocationRequest::new(
            packet_id,
            latitude, 
            longitude,
            false, // weather
            false, // temperature  
            false, // precipitation_prob
            false, // alert
            false, // disaster
            0,     // day
        );
        // packet_id is already set in constructor

        let data = request.to_bytes();
        debug!("Sending location request for ({}, {}) with packet ID {}", latitude, longitude, packet_id);
        
        self.socket.send_to(&data, &self.addr).await?;

        let result = timeout(self.config.timeout, async {
            let mut buf = [0u8; 1024];
            loop {
                let (len, _) = self.socket.recv_from(&mut buf).await?;
                let response_data = &buf[..len];
                
                
                if response_data.len() >= 2 {
                    let raw = u16::from_le_bytes([response_data[0], response_data[1]]);
                    let response_packet_id = (raw >> 4) & 0x0FFF; // version(4bit) + packet_id(12bit)
                    if response_packet_id == packet_id {
                        // Try extended response parsing first (more robust for 32-byte responses)
                        if let Some(response_ex) = LocationResponseEx::from_bytes(response_data) {
                            return Ok(response_ex.area_code);
                        } else if let Ok(response) = LocationResponse::from_bytes(response_data) {
                            return Ok(response.get_area_code());
                        } else {
                            return Err("Failed to parse LocationResponse".into());
                        }
                    }
                }
            }
        }).await;

        match result {
            Ok(Ok(area_code)) => {
                info!("Received area code {} for coordinates ({}, {})", area_code, latitude, longitude);
                Ok(area_code)
            }
            Ok(Err(e)) => Err(e),
            Err(_) => Err("Timeout waiting for location response".into())
        }
    }
}

#[async_trait]
impl LocationClient for LocationClientImpl {
    async fn resolve_coordinates(&self, latitude: f64, longitude: f64) -> Result<u32, Box<dyn std::error::Error + Send + Sync>> {
        self.resolve_coordinates_with_precision(latitude, longitude, self.config.precision_digits).await
    }

    async fn resolve_coordinates_with_precision(&self, latitude: f64, longitude: f64, precision: u8) -> Result<u32, Box<dyn std::error::Error + Send + Sync>> {
        let mut stats = self.stats.write().await;
        stats.total_requests += 1;
        drop(stats);

        if self.config.enable_validation {
            self.validate_coordinates(latitude, longitude).await?;
        }

        if let Some(cached_area_code) = self.get_from_cache(latitude, longitude, precision).await {
            return Ok(cached_area_code);
        }

        let area_code = self.send_location_request(latitude, longitude).await?;
        self.store_in_cache(latitude, longitude, precision, area_code).await;

        Ok(area_code)
    }

    async fn batch_resolve(&self, coordinates: Vec<(f64, f64)>) -> Vec<Result<u32, Box<dyn std::error::Error + Send + Sync>>> {
        let mut handles = Vec::new();
        
        for (lat, lon) in coordinates {
            let client = self.clone();
            let handle = tokio::spawn(async move {
                client.resolve_coordinates(lat, lon).await
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

    async fn validate_coordinates(&self, latitude: f64, longitude: f64) -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
        if !(-90.0..=90.0).contains(&latitude) {
            let mut stats = self.stats.write().await;
            stats.coordinate_errors += 1;
            return Err(format!("Invalid latitude: {} (must be between -90 and 90)", latitude).into());
        }

        if !(-180.0..=180.0).contains(&longitude) {
            let mut stats = self.stats.write().await;
            stats.coordinate_errors += 1;
            return Err(format!("Invalid longitude: {} (must be between -180 and 180)", longitude).into());
        }

        if !self.config.bounds.contains(latitude, longitude) {
            let mut stats = self.stats.write().await;
            stats.validation_errors += 1;
            return Err(format!(
                "Coordinates ({}, {}) are outside allowed bounds ({}, {}) to ({}, {})",
                latitude, longitude,
                self.config.bounds.min_latitude, self.config.bounds.min_longitude,
                self.config.bounds.max_latitude, self.config.bounds.max_longitude
            ).into());
        }

        Ok(())
    }

    fn clear_cache(&self) {
        let cache = self.cache.clone();
        tokio::spawn(async move {
            let mut cache_guard = cache.write().await;
            cache_guard.clear();
            info!("Location cache cleared");
        });
    }

    fn get_cache_stats(&self) -> HashMap<String, usize> {
        tokio::runtime::Handle::current().block_on(async {
            let cache = self.cache.read().await;
            let stats_guard = self.stats.read().await;

            let cache_size = cache.len();
            let expired_entries = cache
                .values()
                .filter(|entry| entry.is_expired(self.config.cache_ttl))
                .count();

            let mut stats = HashMap::new();
            stats.insert("cache_size".to_string(), cache_size);
            stats.insert("expired_entries".to_string(), expired_entries);
            stats.insert("cache_hits".to_string(), stats_guard.cache_hits);
            stats.insert("cache_misses".to_string(), stats_guard.cache_misses);
            stats
        })
    }
}

impl Clone for LocationClientImpl {
    fn clone(&self) -> Self {
        Self {
            host: self.host.clone(),
            port: self.port,
            addr: self.addr,
            config: self.config.clone(),
            socket: self.socket.clone(),
            pidg: self.pidg.clone(),
            cache: self.cache.clone(),
            stats: self.stats.clone(),
        }
    }
}

impl LocationClientImpl {
    pub async fn get_stats(&self) -> LocationStats {
        self.stats.read().await.clone()
    }
    
    pub async fn reset_stats(&self) {
        let mut stats = self.stats.write().await;
        *stats = LocationStats::default();
    }
    
    pub fn set_bounds(&mut self, bounds: CoordinateBounds) {
        self.config.bounds = bounds;
    }
    
    pub fn set_precision(&mut self, precision: u8) {
        self.config.precision_digits = precision;
    }
}
