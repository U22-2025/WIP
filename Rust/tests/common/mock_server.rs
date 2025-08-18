use std::collections::HashMap;
use std::net::{SocketAddr, UdpSocket};
use std::sync::{Arc, Mutex};
use std::thread;
use std::time::{Duration, Instant};
use wip_rust::wip_common_rs::packet::types::location_packet::{LocationRequest, LocationResponse};
use wip_rust::wip_common_rs::packet::types::query_packet::{QueryRequest, QueryResponse};
use wip_rust::wip_common_rs::packet::types::report_packet::{ReportRequest, ReportResponse};
use wip_rust::wip_common_rs::packet::types::error_response::ErrorResponse;
use wip_rust::wip_common_rs::packet::core::PacketFormat;

/// Comprehensive mock server implementation for testing WIP clients
/// Simulates all WIP server types: Weather, Location, Query, and Report servers

#[derive(Debug, Clone)]
pub struct MockServerConfig {
    pub port: u16,
    pub response_delay: Option<Duration>,
    pub error_rate: f32, // 0.0 to 1.0
    pub max_packet_size: usize,
    pub simulate_packet_loss: bool,
    pub packet_loss_rate: f32, // 0.0 to 1.0
}

impl Default for MockServerConfig {
    fn default() -> Self {
        Self {
            port: 0, // Use random port
            response_delay: None,
            error_rate: 0.0,
            max_packet_size: 1024,
            simulate_packet_loss: false,
            packet_loss_rate: 0.0,
        }
    }
}

#[derive(Debug, Clone)]
pub struct ServerStats {
    pub requests_received: u64,
    pub responses_sent: u64,
    pub errors_sent: u64,
    pub bytes_received: u64,
    pub bytes_sent: u64,
    pub packets_dropped: u64,
    pub uptime: Duration,
    pub start_time: Instant,
}

impl Default for ServerStats {
    fn default() -> Self {
        Self {
            requests_received: 0,
            responses_sent: 0,
            errors_sent: 0,
            bytes_received: 0,
            bytes_sent: 0,
            packets_dropped: 0,
            uptime: Duration::new(0, 0),
            start_time: Instant::now(),
        }
    }
}

pub struct MockWipServer {
    socket: UdpSocket,
    config: MockServerConfig,
    stats: Arc<Mutex<ServerStats>>,
    running: Arc<Mutex<bool>>,
    // Mock data storage
    area_codes: Arc<Mutex<HashMap<String, u32>>>, // lat,lng -> area_code
    weather_data: Arc<Mutex<HashMap<u32, String>>>, // area_code -> weather_json
    report_storage: Arc<Mutex<HashMap<u64, String>>>, // report_id -> report_data
}

impl MockWipServer {
    /// Create a new mock server with the given configuration
    pub fn new(config: MockServerConfig) -> Result<Self, std::io::Error> {
        let socket = if config.port == 0 {
            UdpSocket::bind("127.0.0.1:0")?
        } else {
            UdpSocket::bind(format!("127.0.0.1:{}", config.port))?
        };
        
        socket.set_read_timeout(Some(Duration::from_millis(100)))?;
        
        let mut server = Self {
            socket,
            config,
            stats: Arc::new(Mutex::new(ServerStats::default())),
            running: Arc::new(Mutex::new(false)),
            area_codes: Arc::new(Mutex::new(HashMap::new())),
            weather_data: Arc::new(Mutex::new(HashMap::new())),
            report_storage: Arc::new(Mutex::new(HashMap::new())),
        };
        
        server.initialize_mock_data();
        Ok(server)
    }
    
    /// Get the actual port the server is bound to
    pub fn port(&self) -> u16 {
        self.socket.local_addr().unwrap().port()
    }
    
    /// Get server statistics
    pub fn stats(&self) -> ServerStats {
        let mut stats = self.stats.lock().unwrap().clone();
        stats.uptime = stats.start_time.elapsed();
        stats
    }
    
    /// Start the server in a background thread
    pub fn start(&self) -> thread::JoinHandle<()> {
        {
            let mut running = self.running.lock().unwrap();
            *running = true;
        }
        
        let socket_clone = self.socket.try_clone().expect("Failed to clone socket");
        let config = self.config.clone();
        let stats = Arc::clone(&self.stats);
        let running = Arc::clone(&self.running);
        let area_codes = Arc::clone(&self.area_codes);
        let weather_data = Arc::clone(&self.weather_data);
        let report_storage = Arc::clone(&self.report_storage);
        
        thread::spawn(move || {
            let mut buffer = vec![0u8; config.max_packet_size];
            
            while *running.lock().unwrap() {
                match socket_clone.recv_from(&mut buffer) {
                    Ok((size, addr)) => {
                        // Update stats
                        {
                            let mut stats = stats.lock().unwrap();
                            stats.requests_received += 1;
                            stats.bytes_received += size as u64;
                        }
                        
                        // Check for simulated packet loss
                        if config.simulate_packet_loss && 
                           fastrand::f32() < config.packet_loss_rate {
                            let mut stats = stats.lock().unwrap();
                            stats.packets_dropped += 1;
                            continue;
                        }
                        
                        // Process the packet
                        let packet_data = &buffer[..size];
                        let response = Self::process_packet(
                            packet_data,
                            &config,
                            &area_codes,
                            &weather_data,
                            &report_storage,
                        );
                        
                        // Add artificial delay if configured
                        if let Some(delay) = config.response_delay {
                            thread::sleep(delay);
                        }
                        
                        // Send response
                        if let Some(response_data) = response {
                            match socket_clone.send_to(&response_data, addr) {
                                Ok(sent_size) => {
                                    let mut stats = stats.lock().unwrap();
                                    stats.responses_sent += 1;
                                    stats.bytes_sent += sent_size as u64;
                                }
                                Err(_) => {
                                    let mut stats = stats.lock().unwrap();
                                    stats.errors_sent += 1;
                                }
                            }
                        }
                    }
                    Err(_) => {
                        // Timeout or other error, continue if still running
                        continue;
                    }
                }
            }
        })
    }
    
    /// Stop the server
    pub fn stop(&self) {
        let mut running = self.running.lock().unwrap();
        *running = false;
    }
    
    /// Initialize mock data for testing
    fn initialize_mock_data(&mut self) {
        // Add some sample area codes for common locations
        let mut area_codes = self.area_codes.lock().unwrap();
        area_codes.insert("35.6812,139.7671".to_string(), 130010); // Tokyo
        area_codes.insert("34.6937,135.5023".to_string(), 270000); // Osaka
        area_codes.insert("35.4437,139.6380".to_string(), 140010); // Yokohama
        area_codes.insert("35.0116,135.7681".to_string(), 260010); // Kyoto
        area_codes.insert("43.0642,141.3469".to_string(), 11000);  // Sapporo
        
        // Add sample weather data
        let mut weather_data = self.weather_data.lock().unwrap();
        weather_data.insert(130010, r#"{"weather_code": 100, "temperature": 25, "precipitation_prob": 10, "humidity": 65}"#.to_string());
        weather_data.insert(270000, r#"{"weather_code": 200, "temperature": 23, "precipitation_prob": 30, "humidity": 70}"#.to_string());
        weather_data.insert(140010, r#"{"weather_code": 101, "temperature": 24, "precipitation_prob": 15, "humidity": 68}"#.to_string());
        weather_data.insert(260010, r#"{"weather_code": 300, "temperature": 22, "precipitation_prob": 60, "humidity": 80}"#.to_string());
        weather_data.insert(11000, r#"{"weather_code": 400, "temperature": 15, "precipitation_prob": 5, "humidity": 55}"#.to_string());
    }
    
    /// Process incoming packets and generate appropriate responses
    fn process_packet(
        packet_data: &[u8],
        config: &MockServerConfig,
        area_codes: &Arc<Mutex<HashMap<String, u32>>>,
        weather_data: &Arc<Mutex<HashMap<u32, String>>>,
        report_storage: &Arc<Mutex<HashMap<u64, String>>>,
    ) -> Option<Vec<u8>> {
        // Check for random errors
        if fastrand::f32() < config.error_rate {
            return Some(Self::create_error_response(500, "Simulated server error"));
        }
        
        // Try to determine packet type from the data
        // This is a simplified version - in practice you'd parse the full packet
        if packet_data.len() < 16 {
            return Some(Self::create_error_response(400, "Packet too small"));
        }
        
        // Extract packet type from bits 16-18 (simplified)
        let packet_type = (packet_data[2] >> 5) & 0x07;
        
        match packet_type {
            0 => Self::handle_location_request(packet_data, area_codes),
            2 => Self::handle_query_request(packet_data, weather_data),
            4 => Self::handle_report_request(packet_data, report_storage),
            _ => Some(Self::create_error_response(404, "Unknown packet type")),
        }
    }
    
    /// Handle location resolution requests
    fn handle_location_request(
        _packet_data: &[u8],
        area_codes: &Arc<Mutex<HashMap<String, u32>>>,
    ) -> Option<Vec<u8>> {
        // For mock purposes, return a fixed location response
        // In practice, you'd parse the coordinates from the packet
        
        let area_codes = area_codes.lock().unwrap();
        let default_area_code = 130010; // Tokyo
        
        let mut response = LocationResponse::new();
        response.set_area_code(default_area_code);
        response.set_region_name("Tokyo Metropolitan Area".to_string());
        
        Some(response.to_bytes())
    }
    
    /// Handle weather query requests
    fn handle_query_request(
        _packet_data: &[u8],
        weather_data: &Arc<Mutex<HashMap<u32, String>>>,
    ) -> Option<Vec<u8>> {
        let weather_data = weather_data.lock().unwrap();
        let default_data = r#"{"weather_code": 100, "temperature": 25, "precipitation_prob": 10}"#;
        
        let mut response = QueryResponse::new();
        response.set_result_count(1);
        response.set_data(default_data.to_string());
        
        Some(response.to_bytes())
    }
    
    /// Handle sensor report requests
    fn handle_report_request(
        _packet_data: &[u8],
        report_storage: &Arc<Mutex<HashMap<u64, String>>>,
    ) -> Option<Vec<u8>> {
        let report_id = fastrand::u64(1000..999999);
        
        // Store the report (in practice, you'd parse actual report data)
        {
            let mut storage = report_storage.lock().unwrap();
            storage.insert(report_id, "Mock report data".to_string());
        }
        
        let mut response = ReportResponse::new();
        response.set_report_id(report_id);
        response.set_status("accepted".to_string());
        
        Some(response.to_bytes())
    }
    
    /// Create an error response packet
    fn create_error_response(error_code: u32, error_message: &str) -> Vec<u8> {
        let mut error = ErrorResponse::new();
        error.set_error_code(error_code);
        error.set_error_message(error_message.to_string());
        error.to_bytes()
    }
}

/// Builder for easy mock server configuration
pub struct MockServerBuilder {
    config: MockServerConfig,
}

impl MockServerBuilder {
    pub fn new() -> Self {
        Self {
            config: MockServerConfig::default(),
        }
    }
    
    pub fn port(mut self, port: u16) -> Self {
        self.config.port = port;
        self
    }
    
    pub fn response_delay(mut self, delay: Duration) -> Self {
        self.config.response_delay = Some(delay);
        self
    }
    
    pub fn error_rate(mut self, rate: f32) -> Self {
        self.config.error_rate = rate.clamp(0.0, 1.0);
        self
    }
    
    pub fn packet_loss(mut self, rate: f32) -> Self {
        self.config.simulate_packet_loss = true;
        self.config.packet_loss_rate = rate.clamp(0.0, 1.0);
        self
    }
    
    pub fn max_packet_size(mut self, size: usize) -> Self {
        self.config.max_packet_size = size;
        self
    }
    
    pub fn build(self) -> Result<MockWipServer, std::io::Error> {
        MockWipServer::new(self.config)
    }
}

/// Specialized mock servers for different WIP server types
pub struct MockWeatherServer {
    inner: MockWipServer,
}

impl MockWeatherServer {
    pub fn new() -> Result<Self, std::io::Error> {
        let server = MockServerBuilder::new()
            .port(4110)
            .build()?;
        Ok(Self { inner: server })
    }
    
    pub fn port(&self) -> u16 {
        self.inner.port()
    }
    
    pub fn start(&self) -> thread::JoinHandle<()> {
        self.inner.start()
    }
    
    pub fn stop(&self) {
        self.inner.stop()
    }
    
    pub fn stats(&self) -> ServerStats {
        self.inner.stats()
    }
}

pub struct MockLocationServer {
    inner: MockWipServer,
}

impl MockLocationServer {
    pub fn new() -> Result<Self, std::io::Error> {
        let server = MockServerBuilder::new()
            .port(4109)
            .build()?;
        Ok(Self { inner: server })
    }
    
    pub fn port(&self) -> u16 {
        self.inner.port()
    }
    
    pub fn start(&self) -> thread::JoinHandle<()> {
        self.inner.start()
    }
    
    pub fn stop(&self) {
        self.inner.stop()
    }
    
    pub fn stats(&self) -> ServerStats {
        self.inner.stats()
    }
}

pub struct MockQueryServer {
    inner: MockWipServer,
}

impl MockQueryServer {
    pub fn new() -> Result<Self, std::io::Error> {
        let server = MockServerBuilder::new()
            .port(4111)
            .build()?;
        Ok(Self { inner: server })
    }
    
    pub fn port(&self) -> u16 {
        self.inner.port()
    }
    
    pub fn start(&self) -> thread::JoinHandle<()> {
        self.inner.start()
    }
    
    pub fn stop(&self) {
        self.inner.stop()
    }
    
    pub fn stats(&self) -> ServerStats {
        self.inner.stats()
    }
}

pub struct MockReportServer {
    inner: MockWipServer,
}

impl MockReportServer {
    pub fn new() -> Result<Self, std::io::Error> {
        let server = MockServerBuilder::new()
            .port(4112)
            .build()?;
        Ok(Self { inner: server })
    }
    
    pub fn port(&self) -> u16 {
        self.inner.port()
    }
    
    pub fn start(&self) -> thread::JoinHandle<()> {
        self.inner.start()
    }
    
    pub fn stop(&self) {
        self.inner.stop()
    }
    
    pub fn stats(&self) -> ServerStats {
        self.inner.stats()
    }
}

/// Test utilities
pub struct MockServerCluster {
    pub weather_server: MockWeatherServer,
    pub location_server: MockLocationServer,
    pub query_server: MockQueryServer,
    pub report_server: MockReportServer,
    handles: Vec<thread::JoinHandle<()>>,
}

impl MockServerCluster {
    pub fn new() -> Result<Self, std::io::Error> {
        Ok(Self {
            weather_server: MockWeatherServer::new()?,
            location_server: MockLocationServer::new()?,
            query_server: MockQueryServer::new()?,
            report_server: MockReportServer::new()?,
            handles: Vec::new(),
        })
    }
    
    pub fn start_all(&mut self) {
        self.handles.push(self.weather_server.start());
        self.handles.push(self.location_server.start());
        self.handles.push(self.query_server.start());
        self.handles.push(self.report_server.start());
        
        // Give servers time to start
        thread::sleep(Duration::from_millis(100));
    }
    
    pub fn stop_all(&mut self) {
        self.weather_server.stop();
        self.location_server.stop();
        self.query_server.stop();
        self.report_server.stop();
    }
    
    pub fn ports(&self) -> (u16, u16, u16, u16) {
        (
            self.weather_server.port(),
            self.location_server.port(),
            self.query_server.port(),
            self.report_server.port(),
        )
    }
    
    pub fn total_stats(&self) -> ServerStats {
        let mut total = ServerStats::default();
        
        let stats = [
            self.weather_server.stats(),
            self.location_server.stats(),
            self.query_server.stats(),
            self.report_server.stats(),
        ];
        
        for stat in &stats {
            total.requests_received += stat.requests_received;
            total.responses_sent += stat.responses_sent;
            total.errors_sent += stat.errors_sent;
            total.bytes_received += stat.bytes_received;
            total.bytes_sent += stat.bytes_sent;
            total.packets_dropped += stat.packets_dropped;
        }
        
        total
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn test_mock_server_creation() {
        let server = MockServerBuilder::new().build().unwrap();
        assert!(server.port() > 0);
    }
    
    #[test]
    fn test_mock_server_stats() {
        let server = MockServerBuilder::new().build().unwrap();
        let stats = server.stats();
        assert_eq!(stats.requests_received, 0);
        assert_eq!(stats.responses_sent, 0);
    }
    
    #[test]
    fn test_mock_server_cluster() {
        let cluster = MockServerCluster::new().unwrap();
        let (weather_port, location_port, query_port, report_port) = cluster.ports();
        
        assert!(weather_port > 0);
        assert!(location_port > 0);
        assert!(query_port > 0);
        assert!(report_port > 0);
        
        // All ports should be different
        let ports = vec![weather_port, location_port, query_port, report_port];
        for i in 0..ports.len() {
            for j in (i + 1)..ports.len() {
                assert_ne!(ports[i], ports[j]);
            }
        }
    }
    
    #[test]
    fn test_mock_server_builder() {
        let server = MockServerBuilder::new()
            .error_rate(0.1)
            .response_delay(Duration::from_millis(50))
            .packet_loss(0.05)
            .max_packet_size(2048)
            .build()
            .unwrap();
        
        assert!(server.port() > 0);
        assert_eq!(server.config.error_rate, 0.1);
        assert_eq!(server.config.response_delay, Some(Duration::from_millis(50)));
        assert_eq!(server.config.packet_loss_rate, 0.05);
        assert_eq!(server.config.max_packet_size, 2048);
    }
}