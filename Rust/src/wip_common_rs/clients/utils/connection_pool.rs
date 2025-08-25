use log::{debug, error, info, warn};
use std::collections::{HashMap, VecDeque};
use std::net::SocketAddr;
use std::sync::Arc;
use std::time::{Duration, Instant};
use tokio::net::UdpSocket;
use tokio::sync::{Mutex, RwLock};
use tokio::time::{interval, Interval};

#[derive(Debug, Clone)]
pub struct PoolConfig {
    pub initial_size: usize,
    pub max_size: usize,
    pub min_idle: usize,
    pub max_idle_time: Duration,
    pub connection_timeout: Duration,
    pub health_check_interval: Duration,
    pub enable_load_balancing: bool,
    pub load_balancing_strategy: LoadBalancingStrategy,
}

impl Default for PoolConfig {
    fn default() -> Self {
        Self {
            initial_size: 5,
            max_size: 20,
            min_idle: 2,
            max_idle_time: Duration::from_secs(300), // 5 minutes
            connection_timeout: Duration::from_secs(5),
            health_check_interval: Duration::from_secs(30),
            enable_load_balancing: true,
            load_balancing_strategy: LoadBalancingStrategy::RoundRobin,
        }
    }
}

#[derive(Debug, Clone)]
pub enum LoadBalancingStrategy {
    RoundRobin,
    LeastConnections,
    Random,
    WeightedRandom,
}

#[derive(Debug, Clone)]
pub struct ConnectionStats {
    pub total_connections: usize,
    pub active_connections: usize,
    pub idle_connections: usize,
    pub failed_connections: usize,
    pub connection_requests: usize,
    pub connection_timeouts: usize,
    pub bytes_sent: usize,
    pub bytes_received: usize,
    pub health_check_failures: usize,
}

impl Default for ConnectionStats {
    fn default() -> Self {
        Self {
            total_connections: 0,
            active_connections: 0,
            idle_connections: 0,
            failed_connections: 0,
            connection_requests: 0,
            connection_timeouts: 0,
            bytes_sent: 0,
            bytes_received: 0,
            health_check_failures: 0,
        }
    }
}

#[derive(Debug)]
pub struct PooledConnection {
    pub id: u64,
    pub socket: Arc<UdpSocket>,
    pub created_at: Instant,
    pub last_used: Instant,
    pub usage_count: usize,
    pub is_healthy: bool,
    pub local_addr: SocketAddr,
}

impl PooledConnection {
    pub async fn new(id: u64, bind_addr: Option<&str>) -> tokio::io::Result<Self> {
        let bind_addr = bind_addr.unwrap_or("0.0.0.0:0");
        let socket = UdpSocket::bind(bind_addr).await?;
        let local_addr = socket.local_addr()?;
        
        Ok(Self {
            id,
            socket: Arc::new(socket),
            created_at: Instant::now(),
            last_used: Instant::now(),
            usage_count: 0,
            is_healthy: true,
            local_addr,
        })
    }

    pub fn use_connection(&mut self) {
        self.last_used = Instant::now();
        self.usage_count += 1;
    }

    pub fn is_idle(&self, max_idle_time: Duration) -> bool {
        self.last_used.elapsed() > max_idle_time
    }

    pub fn age(&self) -> Duration {
        self.created_at.elapsed()
    }

    pub async fn health_check(&mut self) -> bool {
        // Simple health check - try to get socket info
        match self.socket.local_addr() {
            Ok(_) => {
                self.is_healthy = true;
                true
            }
            Err(_) => {
                self.is_healthy = false;
                false
            }
        }
    }
}

pub struct UdpConnectionPool {
    config: PoolConfig,
    connections: Arc<RwLock<HashMap<u64, PooledConnection>>>,
    available_connections: Arc<Mutex<VecDeque<u64>>>,
    next_connection_id: Arc<Mutex<u64>>,
    round_robin_index: Arc<Mutex<usize>>,
    stats: Arc<RwLock<ConnectionStats>>,
    cleanup_interval: Arc<Mutex<Option<Interval>>>,
}

impl UdpConnectionPool {
    pub async fn new(config: PoolConfig) -> Result<Self, Box<dyn std::error::Error + Send + Sync>> {
        let pool = Self {
            config: config.clone(),
            connections: Arc::new(RwLock::new(HashMap::new())),
            available_connections: Arc::new(Mutex::new(VecDeque::new())),
            next_connection_id: Arc::new(Mutex::new(1)),
            round_robin_index: Arc::new(Mutex::new(0)),
            stats: Arc::new(RwLock::new(ConnectionStats::default())),
            cleanup_interval: Arc::new(Mutex::new(None)),
        };

        // Initialize with minimum connections
        pool.initialize_connections().await?;
        
        // Start cleanup and health check tasks
        pool.start_maintenance_tasks().await;
        
        Ok(pool)
    }

    async fn initialize_connections(&self) -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
        info!("Initializing connection pool with {} connections", self.config.initial_size);
        
        for _ in 0..self.config.initial_size {
            self.create_connection().await?;
        }
        
        Ok(())
    }

    async fn start_maintenance_tasks(&self) {
        let pool_clone = self.clone();
        tokio::spawn(async move {
            let mut interval = interval(pool_clone.config.health_check_interval);
            
            loop {
                interval.tick().await;
                pool_clone.perform_maintenance().await;
            }
        });
    }

    async fn perform_maintenance(&self) {
        debug!("Performing connection pool maintenance");
        
        self.cleanup_idle_connections().await;
        self.perform_health_checks().await;
        self.ensure_minimum_connections().await;
    }

    async fn cleanup_idle_connections(&self) {
        let mut connections = self.connections.write().await;
        let mut available = self.available_connections.lock().await;
        let mut stats = self.stats.write().await;
        
        let mut to_remove = Vec::new();
        
        for (id, connection) in connections.iter() {
            if connection.is_idle(self.config.max_idle_time) && available.len() > self.config.min_idle {
                to_remove.push(*id);
            }
        }
        
        for id in to_remove {
            connections.remove(&id);
            available.retain(|&conn_id| conn_id != id);
            stats.total_connections -= 1;
            debug!("Removed idle connection {}", id);
        }
    }

    async fn perform_health_checks(&self) {
        let mut connections = self.connections.write().await;
        let mut available = self.available_connections.lock().await;
        let mut stats = self.stats.write().await;
        
        let mut unhealthy_connections = Vec::new();
        
        for (id, connection) in connections.iter_mut() {
            if !connection.health_check().await {
                unhealthy_connections.push(*id);
                stats.health_check_failures += 1;
            }
        }
        
        for id in unhealthy_connections {
            connections.remove(&id);
            available.retain(|&conn_id| conn_id != id);
            stats.total_connections -= 1;
            stats.failed_connections += 1;
            warn!("Removed unhealthy connection {}", id);
        }
    }

    async fn ensure_minimum_connections(&self) {
        let available_count = self.available_connections.lock().await.len();
        
        if available_count < self.config.min_idle {
            let needed = self.config.min_idle - available_count;
            debug!("Creating {} connections to maintain minimum", needed);
            
            for _ in 0..needed {
                if let Err(e) = self.create_connection().await {
                    error!("Failed to create connection during maintenance: {}", e);
                    break;
                }
            }
        }
    }

    async fn create_connection(&self) -> Result<u64, Box<dyn std::error::Error + Send + Sync>> {
        let mut next_id = self.next_connection_id.lock().await;
        let id = *next_id;
        *next_id += 1;
        drop(next_id);

        let connection = PooledConnection::new(id, None).await?;
        debug!("Created new connection {} at {}", id, connection.local_addr);

        let mut connections = self.connections.write().await;
        let mut available = self.available_connections.lock().await;
        let mut stats = self.stats.write().await;

        connections.insert(id, connection);
        available.push_back(id);
        stats.total_connections += 1;
        stats.idle_connections += 1;

        Ok(id)
    }

    pub async fn get_connection(&self) -> Result<Arc<UdpSocket>, Box<dyn std::error::Error + Send + Sync>> {
        let mut stats = self.stats.write().await;
        stats.connection_requests += 1;
        drop(stats);

        let connection_id = self.select_connection().await?;
        
        let mut connections = self.connections.write().await;
        if let Some(connection) = connections.get_mut(&connection_id) {
            connection.use_connection();
            
            let mut stats = self.stats.write().await;
            stats.active_connections += 1;
            stats.idle_connections -= 1;
            
            debug!("Allocated connection {}", connection_id);
            Ok(connection.socket.clone())
        } else {
            Err("Connection not found in pool".into())
        }
    }

    async fn select_connection(&self) -> Result<u64, Box<dyn std::error::Error + Send + Sync>> {
        let mut available = self.available_connections.lock().await;
        
        if available.is_empty() {
            // Try to create a new connection if under max limit
            let total_connections = self.connections.read().await.len();
            if total_connections < self.config.max_size {
                drop(available);
                return self.create_connection().await;
            } else {
                return Err("Connection pool exhausted".into());
            }
        }

        let connection_id = match self.config.load_balancing_strategy {
            LoadBalancingStrategy::RoundRobin => {
                available.pop_front().unwrap()
            }
            LoadBalancingStrategy::Random => {
                let index = rand::random::<usize>() % available.len();
                available.remove(index).unwrap()
            }
            LoadBalancingStrategy::LeastConnections => {
                self.select_least_used_connection(&mut available).await
            }
            LoadBalancingStrategy::WeightedRandom => {
                // For now, fallback to random
                let index = rand::random::<usize>() % available.len();
                available.remove(index).unwrap()
            }
        };

        Ok(connection_id)
    }

    async fn select_least_used_connection(&self, available: &mut VecDeque<u64>) -> u64 {
        let connections = self.connections.read().await;
        
        let mut best_id = available[0];
        let mut min_usage = usize::MAX;
        
        for (_i, &conn_id) in available.iter().enumerate() {
            if let Some(connection) = connections.get(&conn_id) {
                if connection.usage_count < min_usage {
                    min_usage = connection.usage_count;
                    best_id = conn_id;
                }
            }
        }
        
        available.retain(|&id| id != best_id);
        best_id
    }

    pub async fn return_connection(&self, socket: Arc<UdpSocket>) -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
        let socket_addr = socket.local_addr()?;
        
        let connections = self.connections.read().await;
        let mut found_id = None;
        
        for (&id, connection) in connections.iter() {
            if connection.local_addr == socket_addr {
                found_id = Some(id);
                break;
            }
        }
        
        if let Some(id) = found_id {
            let mut available = self.available_connections.lock().await;
            let mut stats = self.stats.write().await;
            
            available.push_back(id);
            stats.active_connections -= 1;
            stats.idle_connections += 1;
            
            debug!("Returned connection {} to pool", id);
            Ok(())
        } else {
            Err("Connection not found in pool".into())
        }
    }

    pub async fn get_stats(&self) -> ConnectionStats {
        let mut stats = self.stats.read().await.clone();
        
        let connections = self.connections.read().await;
        let available = self.available_connections.lock().await;
        
        stats.total_connections = connections.len();
        stats.idle_connections = available.len();
        stats.active_connections = stats.total_connections - stats.idle_connections;
        
        stats
    }

    pub async fn shutdown(&self) {
        info!("Shutting down connection pool");
        
        let mut connections = self.connections.write().await;
        let mut available = self.available_connections.lock().await;
        
        connections.clear();
        available.clear();
        
        info!("Connection pool shutdown complete");
    }

    pub fn get_config(&self) -> &PoolConfig {
        &self.config
    }
}

impl Clone for UdpConnectionPool {
    fn clone(&self) -> Self {
        Self {
            config: self.config.clone(),
            connections: self.connections.clone(),
            available_connections: self.available_connections.clone(),
            next_connection_id: self.next_connection_id.clone(),
            round_robin_index: self.round_robin_index.clone(),
            stats: self.stats.clone(),
            cleanup_interval: self.cleanup_interval.clone(),
        }
    }
}

pub struct PooledUdpSocket {
    socket: Arc<UdpSocket>,
    pool: Arc<UdpConnectionPool>,
}

impl PooledUdpSocket {
    pub async fn from_pool(pool: Arc<UdpConnectionPool>) -> Result<Self, Box<dyn std::error::Error + Send + Sync>> {
        let socket = pool.get_connection().await?;
        Ok(Self { socket, pool })
    }

    pub async fn send_to(&self, buf: &[u8], target: SocketAddr) -> tokio::io::Result<usize> {
        let result = self.socket.send_to(buf, target).await;
        
        if let Ok(bytes) = result {
            let mut stats = self.pool.stats.write().await;
            stats.bytes_sent += bytes;
        }
        
        result
    }

    pub async fn recv_from(&self, buf: &mut [u8]) -> tokio::io::Result<(usize, SocketAddr)> {
        let result = self.socket.recv_from(buf).await;
        
        if let Ok((bytes, _)) = result {
            let mut stats = self.pool.stats.write().await;
            stats.bytes_received += bytes;
        }
        
        result
    }

    pub fn local_addr(&self) -> tokio::io::Result<SocketAddr> {
        self.socket.local_addr()
    }
}

impl Drop for PooledUdpSocket {
    fn drop(&mut self) {
        let socket = self.socket.clone();
        let pool = self.pool.clone();
        
        tokio::spawn(async move {
            if let Err(e) = pool.return_connection(socket).await {
                error!("Failed to return connection to pool: {}", e);
            }
        });
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[tokio::test]
    async fn test_connection_pool_creation() {
        let config = PoolConfig {
            initial_size: 3,
            max_size: 10,
            min_idle: 1,
            ..Default::default()
        };
        
        let pool = UdpConnectionPool::new(config).await.unwrap();
        let stats = pool.get_stats().await;
        
        assert_eq!(stats.total_connections, 3);
        assert_eq!(stats.idle_connections, 3);
        assert_eq!(stats.active_connections, 0);
    }
    
    #[tokio::test]
    async fn test_connection_allocation_and_return() {
        let config = PoolConfig {
            initial_size: 2,
            max_size: 5,
            min_idle: 1,
            ..Default::default()
        };
        
        let pool = Arc::new(UdpConnectionPool::new(config).await.unwrap());
        
        // Get a connection
        let socket = pool.get_connection().await.unwrap();
        let stats = pool.get_stats().await;
        assert_eq!(stats.active_connections, 1);
        assert_eq!(stats.idle_connections, 1);
        
        // Return the connection
        pool.return_connection(socket).await.unwrap();
        let stats = pool.get_stats().await;
        assert_eq!(stats.active_connections, 0);
        assert_eq!(stats.idle_connections, 2);
    }
    
    #[tokio::test]
    async fn test_pooled_udp_socket() {
        let config = PoolConfig {
            initial_size: 1,
            max_size: 3,
            min_idle: 1,
            ..Default::default()
        };
        
        let pool = Arc::new(UdpConnectionPool::new(config).await.unwrap());
        let pooled_socket = PooledUdpSocket::from_pool(pool.clone()).await.unwrap();
        
        // Test that we can get the local address
        let _local_addr = pooled_socket.local_addr().unwrap();
        
        // When dropped, the socket should be returned to the pool
        drop(pooled_socket);
        
        // Give some time for the async drop to complete
        tokio::time::sleep(Duration::from_millis(10)).await;
        
        let stats = pool.get_stats().await;
        assert_eq!(stats.idle_connections, 1);
    }
}