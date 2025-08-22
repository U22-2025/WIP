use std::net::{SocketAddr, IpAddr, Ipv4Addr, ToSocketAddrs};
use std::time::{Duration, Instant};
use std::collections::HashMap;
use tokio::net::{UdpSocket, TcpSocket};
use tokio::time::timeout;

#[derive(Debug, Clone)]
pub struct NetworkStats {
    pub packets_sent: u64,
    pub packets_received: u64,
    pub bytes_sent: u64,
    pub bytes_received: u64,
    pub connection_attempts: u64,
    pub connection_failures: u64,
    pub avg_response_time: Duration,
    pub last_activity: Option<Instant>,
}

impl NetworkStats {
    pub fn new() -> Self {
        Self {
            packets_sent: 0,
            packets_received: 0,
            bytes_sent: 0,
            bytes_received: 0,
            connection_attempts: 0,
            connection_failures: 0,
            avg_response_time: Duration::ZERO,
            last_activity: None,
        }
    }

    pub fn record_sent(&mut self, bytes: usize) {
        self.packets_sent += 1;
        self.bytes_sent += bytes as u64;
        self.last_activity = Some(Instant::now());
    }

    pub fn record_received(&mut self, bytes: usize) {
        self.packets_received += 1;
        self.bytes_received += bytes as u64;
        self.last_activity = Some(Instant::now());
    }

    pub fn record_connection_attempt(&mut self) {
        self.connection_attempts += 1;
    }

    pub fn record_connection_failure(&mut self) {
        self.connection_failures += 1;
    }

    pub fn update_response_time(&mut self, response_time: Duration) {
        // Simple moving average
        if self.avg_response_time == Duration::ZERO {
            self.avg_response_time = response_time;
        } else {
            let current_millis = self.avg_response_time.as_millis() as u64;
            let new_millis = response_time.as_millis() as u64;
            let avg_millis = (current_millis + new_millis) / 2;
            self.avg_response_time = Duration::from_millis(avg_millis);
        }
    }
}

pub struct NetworkDiagnostics {
    stats: HashMap<String, NetworkStats>,
}

impl NetworkDiagnostics {
    pub fn new() -> Self {
        Self {
            stats: HashMap::new(),
        }
    }

    pub fn get_stats(&self, host: &str) -> Option<&NetworkStats> {
        self.stats.get(host)
    }

    pub fn get_stats_mut(&mut self, host: &str) -> &mut NetworkStats {
        self.stats.entry(host.to_string()).or_insert_with(NetworkStats::new)
    }

    pub async fn ping_host(&mut self, host: &str, port: u16, timeout_duration: Duration) -> Result<Duration, String> {
        let start_time = Instant::now();
        let stats = self.get_stats_mut(host);
        stats.record_connection_attempt();

        let addr = format!("{}:{}", host, port);
        let socket_addr: SocketAddr = addr.parse()
            .map_err(|e| format!("Invalid address {}: {}", addr, e))?;

        let socket = match TcpSocket::new_v4() {
            Ok(socket) => socket,
            Err(e) => {
                stats.record_connection_failure();
                return Err(format!("Failed to create socket: {}", e));
            }
        };

        match timeout(timeout_duration, socket.connect(socket_addr)).await {
            Ok(Ok(_)) => {
                let response_time = start_time.elapsed();
                stats.update_response_time(response_time);
                Ok(response_time)
            }
            Ok(Err(e)) => {
                stats.record_connection_failure();
                Err(format!("Connection failed: {}", e))
            }
            Err(_) => {
                stats.record_connection_failure();
                Err("Connection timeout".to_string())
            }
        }
    }

    pub async fn test_udp_connectivity(&mut self, host: &str, port: u16, test_data: &[u8]) -> Result<Duration, String> {
        let start_time = Instant::now();
        let stats = self.get_stats_mut(host);
        stats.record_connection_attempt();

        let socket = UdpSocket::bind("0.0.0.0:0").await
            .map_err(|e| format!("Failed to bind UDP socket: {}", e))?;

        let addr = format!("{}:{}", host, port);
        let target_addr: SocketAddr = addr.parse()
            .map_err(|e| format!("Invalid address {}: {}", addr, e))?;

        // Send test data
        match socket.send_to(test_data, target_addr).await {
            Ok(bytes_sent) => {
                stats.record_sent(bytes_sent);
                
                // Try to receive response (with timeout)
                let mut buffer = [0u8; 1024];
                match timeout(Duration::from_secs(5), socket.recv_from(&mut buffer)).await {
                    Ok(Ok((bytes_received, _))) => {
                        let response_time = start_time.elapsed();
                        stats.record_received(bytes_received);
                        stats.update_response_time(response_time);
                        Ok(response_time)
                    }
                    Ok(Err(e)) => {
                        stats.record_connection_failure();
                        Err(format!("UDP receive failed: {}", e))
                    }
                    Err(_) => {
                        stats.record_connection_failure();
                        Err("UDP receive timeout".to_string())
                    }
                }
            }
            Err(e) => {
                stats.record_connection_failure();
                Err(format!("UDP send failed: {}", e))
            }
        }
    }

    pub fn get_all_stats(&self) -> &HashMap<String, NetworkStats> {
        &self.stats
    }

    pub fn reset_stats(&mut self, host: Option<&str>) {
        match host {
            Some(h) => {
                self.stats.remove(h);
            }
            None => {
                self.stats.clear();
            }
        }
    }
}

pub async fn resolve_ipv4(hostname: &str) -> Result<Ipv4Addr, String> {
    let addresses: Vec<SocketAddr> = format!("{}:80", hostname)
        .to_socket_addrs()
        .map_err(|e| format!("Failed to resolve hostname {}: {}", hostname, e))?
        .collect();

    for addr in addresses {
        if let IpAddr::V4(ipv4) = addr.ip() {
            return Ok(ipv4);
        }
    }

    Err(format!("No IPv4 address found for hostname: {}", hostname))
}

pub async fn check_network_connectivity(hosts: &[(&str, u16)]) -> HashMap<String, bool> {
    let mut results = HashMap::new();
    let mut diagnostics = NetworkDiagnostics::new();

    for &(host, port) in hosts {
        let is_reachable = diagnostics
            .ping_host(host, port, Duration::from_secs(5))
            .await
            .is_ok();
        
        results.insert(format!("{}:{}", host, port), is_reachable);
    }

    results
}

pub fn get_local_ip() -> Result<Ipv4Addr, String> {
    use std::net::UdpSocket;
    
    let socket = UdpSocket::bind("0.0.0.0:0")
        .map_err(|e| format!("Failed to bind socket: {}", e))?;
    
    socket.connect("8.8.8.8:80")
        .map_err(|e| format!("Failed to connect to test address: {}", e))?;
    
    let local_addr = socket.local_addr()
        .map_err(|e| format!("Failed to get local address: {}", e))?;
    
    match local_addr.ip() {
        IpAddr::V4(ipv4) => Ok(ipv4),
        IpAddr::V6(_) => Err("Got IPv6 address instead of IPv4".to_string()),
    }
}

pub fn validate_ipv4(ip_str: &str) -> bool {
    ip_str.parse::<Ipv4Addr>().is_ok()
}

pub fn validate_port(port: u16) -> bool {
    port > 0 && port <= 65535
}

pub fn parse_host_port(addr_str: &str) -> Result<(String, u16), String> {
    let parts: Vec<&str> = addr_str.split(':').collect();
    
    if parts.len() != 2 {
        return Err("Address must be in format 'host:port'".to_string());
    }
    
    let host = parts[0].to_string();
    let port = parts[1].parse::<u16>()
        .map_err(|_| "Invalid port number".to_string())?;
    
    if !validate_port(port) {
        return Err("Port must be between 1 and 65535".to_string());
    }
    
    Ok((host, port))
}

#[derive(Debug, Clone)]
pub struct NetworkConfig {
    pub connect_timeout: Duration,
    pub read_timeout: Duration,
    pub write_timeout: Duration,
    pub max_retries: u32,
    pub retry_delay: Duration,
    pub buffer_size: usize,
}

impl Default for NetworkConfig {
    fn default() -> Self {
        Self {
            connect_timeout: Duration::from_secs(10),
            read_timeout: Duration::from_secs(30),
            write_timeout: Duration::from_secs(30),
            max_retries: 3,
            retry_delay: Duration::from_millis(500),
            buffer_size: 8192,
        }
    }
}

impl NetworkConfig {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn with_timeouts(mut self, connect: Duration, read: Duration, write: Duration) -> Self {
        self.connect_timeout = connect;
        self.read_timeout = read;
        self.write_timeout = write;
        self
    }

    pub fn with_retries(mut self, max_retries: u32, delay: Duration) -> Self {
        self.max_retries = max_retries;
        self.retry_delay = delay;
        self
    }

    pub fn with_buffer_size(mut self, size: usize) -> Self {
        self.buffer_size = size;
        self
    }
}

pub struct ConnectionPool {
    connections: HashMap<String, Vec<UdpSocket>>,
    max_connections_per_host: usize,
    connection_timeout: Duration,
}

impl ConnectionPool {
    pub fn new(max_connections_per_host: usize) -> Self {
        Self {
            connections: HashMap::new(),
            max_connections_per_host,
            connection_timeout: Duration::from_secs(300), // 5 minutes
        }
    }

    pub async fn get_connection(&mut self, host: &str, port: u16) -> Result<UdpSocket, String> {
        let key = format!("{}:{}", host, port);
        
        // Try to reuse existing connection
        if let Some(connections) = self.connections.get_mut(&key) {
            if let Some(socket) = connections.pop() {
                return Ok(socket);
            }
        }

        // Create new connection
        let socket = UdpSocket::bind("0.0.0.0:0").await
            .map_err(|e| format!("Failed to create UDP socket: {}", e))?;
        
        let addr: SocketAddr = format!("{}:{}", host, port).parse()
            .map_err(|e| format!("Invalid address: {}", e))?;
        
        socket.connect(addr).await
            .map_err(|e| format!("Failed to connect socket: {}", e))?;

        Ok(socket)
    }

    pub fn return_connection(&mut self, host: &str, port: u16, socket: UdpSocket) {
        let key = format!("{}:{}", host, port);
        let connections = self.connections.entry(key).or_insert_with(Vec::new);
        
        if connections.len() < self.max_connections_per_host {
            connections.push(socket);
        }
        // If pool is full, socket is dropped
    }

    pub fn cleanup_expired(&mut self) {
        // In a real implementation, you'd track connection creation times
        // and remove expired connections. For simplicity, we'll just clear
        // connections that haven't been used recently.
        self.connections.clear();
    }

    pub fn get_pool_stats(&self) -> HashMap<String, usize> {
        self.connections.iter()
            .map(|(key, connections)| (key.clone(), connections.len()))
            .collect()
    }
}