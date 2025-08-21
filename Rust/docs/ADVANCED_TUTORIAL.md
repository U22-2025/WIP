# WIP Rust Implementation - Advanced Tutorial

This advanced tutorial covers sophisticated features of the WIP Rust library, including async operations, performance optimization, custom packet handling, and production deployment patterns.

## Table of Contents

1. [Async Programming with WIP](#async-programming-with-wip)
2. [Connection Pooling and Performance](#connection-pooling-and-performance)
3. [Custom Packet Manipulation](#custom-packet-manipulation)
4. [Advanced Error Recovery](#advanced-error-recovery)
5. [Monitoring and Metrics](#monitoring-and-metrics)
6. [Authentication and Security](#authentication-and-security)
7. [Production Deployment](#production-deployment)
8. [Integration Patterns](#integration-patterns)

## Async Programming with WIP

### Basic Async Client Usage

```rust
use wip_rust::prelude::*;
use tokio;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let client = AsyncWeatherClient::new("127.0.0.1:4110");
    
    let weather_data = client.get_weather_by_coordinates_async(
        35.6812, 139.7671,
        true, true, false, false, false, 0
    ).await?;
    
    println!("Async weather data: {:?}", weather_data);
    Ok(())
}
```

### Concurrent Operations with Multiple Cities

```rust
use wip_rust::prelude::*;
use tokio;
use futures::future::join_all;
use std::time::Instant;

#[tokio::main]
async fn concurrent_weather_monitoring() -> Result<(), Box<dyn std::error::Error>> {
    let client = AsyncWeatherClient::new("127.0.0.1:4110");
    
    // Define cities to monitor
    let cities = vec![
        (35.6812, 139.7671, "Tokyo"),
        (34.6937, 135.5023, "Osaka"),
        (35.0116, 135.7681, "Kyoto"),
        (43.0642, 141.3469, "Sapporo"),
        (33.5904, 130.4017, "Fukuoka"),
        (26.2124, 127.6792, "Naha"),
    ];
    
    let start_time = Instant::now();
    
    // Create concurrent requests
    let futures = cities.into_iter().map(|(lat, lng, name)| {
        let client = client.clone();
        async move {
            let request_start = Instant::now();
            let result = client.get_weather_by_coordinates_async(
                lat, lng, true, true, true, true, false, 0
            ).await;
            let request_time = request_start.elapsed();
            
            (name, result, request_time)
        }
    });
    
    // Wait for all requests to complete
    let results = join_all(futures).await;
    
    let total_time = start_time.elapsed();
    let mut successful_requests = 0;
    let mut total_request_time = std::time::Duration::new(0, 0);
    
    // Process results
    for (city, result, request_time) in results {
        match result {
            Ok(weather_data) => {
                successful_requests += 1;
                total_request_time += request_time;
                
                println!("✅ {}: Success in {:?}", city, request_time);
                
                // Process weather data
                if let Some(temp) = weather_data.get("temperature") {
                    println!("   Temperature: {}°C", temp);
                }
                if let Some(weather_code) = weather_data.get("weather_code") {
                    println!("   Weather code: {}", weather_code);
                }
            },
            Err(e) => {
                println!("❌ {}: Failed in {:?} - {}", city, request_time, e);
            }
        }
    }
    
    // Performance summary
    println!("\n📊 Performance Summary:");
    println!("Total time: {:?}", total_time);
    println!("Successful requests: {}", successful_requests);
    if successful_requests > 0 {
        let avg_request_time = total_request_time / successful_requests;
        println!("Average request time: {:?}", avg_request_time);
        println!("Concurrent speedup: {:.2}x", 
                (total_request_time.as_secs_f64() / total_time.as_secs_f64()));
    }
    
    Ok(())
}
```

### Stream Processing for Real-time Weather

```rust
use wip_rust::prelude::*;
use tokio;
use tokio_stream::{wrappers::IntervalStream, StreamExt};
use std::time::Duration;

#[tokio::main]
async fn real_time_weather_stream() -> Result<(), Box<dyn std::error::Error>> {
    let client = AsyncWeatherClient::new("127.0.0.1:4110");
    
    // Create a stream that fetches weather data every 30 seconds
    let interval = tokio::time::interval(Duration::from_secs(30));
    let mut stream = IntervalStream::new(interval);
    
    let tokyo_coords = (35.6812, 139.7671);
    
    println!("🔄 Starting real-time weather monitoring for Tokyo...");
    println!("Press Ctrl+C to stop\n");
    
    while let Some(_) = stream.next().await {
        let timestamp = chrono::Utc::now();
        println!("[{}] Fetching weather data...", timestamp.format("%H:%M:%S"));
        
        match client.get_weather_by_coordinates_async(
            tokyo_coords.0, tokyo_coords.1,
            true, true, true, false, false, 0
        ).await {
            Ok(weather_data) => {
                println!("✅ Weather update received:");
                
                for (key, value) in &weather_data {
                    match key.as_str() {
                        "temperature" => println!("   🌡️  {}°C", value),
                        "weather_code" => {
                            let emoji = match *value as u32 {
                                100..=199 => "☀️",
                                200..=299 => "☁️", 
                                300..=399 => "🌧️",
                                400..=499 => "❄️",
                                _ => "❓",
                            };
                            println!("   {} Weather code: {}", emoji, value);
                        },
                        "precipitation" => {
                            if *value > 0 {
                                println!("   💧 {}mm", value);
                            }
                        },
                        _ => {}
                    }
                }
                println!();
            },
            Err(e) => {
                println!("❌ Failed to fetch weather: {}\n", e);
            }
        }
    }
    
    Ok(())
}
```

## Connection Pooling and Performance

### Advanced Connection Pool Implementation

```rust
use wip_rust::prelude::*;
use std::sync::{Arc, Mutex};
use std::collections::VecDeque;
use tokio;
use std::time::{Duration, Instant};

struct WeatherClientPool {
    clients: Arc<Mutex<VecDeque<WeatherClient>>>,
    max_size: usize,
    server_address: String,
}

impl WeatherClientPool {
    fn new(server_address: &str, pool_size: usize) -> Self {
        let mut clients = VecDeque::new();
        for _ in 0..pool_size {
            clients.push_back(WeatherClient::new(server_address));
        }
        
        Self {
            clients: Arc::new(Mutex::new(clients)),
            max_size: pool_size,
            server_address: server_address.to_string(),
        }
    }
    
    fn get_client(&self) -> WeatherClient {
        let mut clients = self.clients.lock().unwrap();
        
        if let Some(client) = clients.pop_front() {
            client
        } else {
            // Pool exhausted, create new client
            WeatherClient::new(&self.server_address)
        }
    }
    
    fn return_client(&self, client: WeatherClient) {
        let mut clients = self.clients.lock().unwrap();
        if clients.len() < self.max_size {
            clients.push_back(client);
        }
        // If pool is full, client will be dropped
    }
    
    async fn get_weather_pooled(
        &self,
        lat: f64,
        lng: f64,
    ) -> Result<std::collections::HashMap<String, u128>, Box<dyn std::error::Error + Send + Sync>> {
        let client = self.get_client();
        
        let result = tokio::task::spawn_blocking(move || {
            client.get_weather_by_coordinates(lat, lng, true, true, false, false, false, 0)
        }).await?;
        
        // Note: In a real implementation, we'd return the client to the pool
        // For simplicity, we're letting it drop here
        
        Ok(result?)
    }
}

#[tokio::main]
async fn pool_performance_test() -> Result<(), Box<dyn std::error::Error>> {
    let pool = Arc::new(WeatherClientPool::new("127.0.0.1:4110", 10));
    
    let coordinates = vec![
        (35.6812, 139.7671),  // Tokyo
        (34.6937, 135.5023),  // Osaka
        (35.0116, 135.7681),  // Kyoto
        (43.0642, 141.3469),  // Sapporo
        (33.5904, 130.4017),  // Fukuoka
    ];
    
    println!("🚀 Starting pool performance test with {} concurrent requests...", 
             coordinates.len() * 4);
    
    let start_time = Instant::now();
    
    // Create multiple requests per coordinate to test pool efficiency
    let mut handles = Vec::new();
    
    for (lat, lng) in coordinates {
        for i in 0..4 {
            let pool_clone = Arc::clone(&pool);
            let handle = tokio::spawn(async move {
                let request_start = Instant::now();
                let result = pool_clone.get_weather_pooled(lat, lng).await;
                let request_time = request_start.elapsed();
                
                (format!("{:.4},{:.4}#{}", lat, lng, i), result, request_time)
            });
            handles.push(handle);
        }
    }
    
    // Wait for all requests
    let results = futures::future::join_all(handles).await;
    
    let total_time = start_time.elapsed();
    let mut successful = 0;
    let mut total_request_time = Duration::new(0, 0);
    
    for result in results {
        if let Ok((request_id, weather_result, request_time)) = result {
            total_request_time += request_time;
            match weather_result {
                Ok(_) => {
                    successful += 1;
                    println!("✅ {}: {:?}", request_id, request_time);
                },
                Err(e) => {
                    println!("❌ {}: {} ({:?})", request_id, e, request_time);
                }
            }
        }
    }
    
    println!("\n📊 Pool Performance Results:");
    println!("Total requests: {}", results.len());
    println!("Successful: {}", successful);
    println!("Total time: {:?}", total_time);
    println!("Average request time: {:?}", total_request_time / results.len() as u32);
    println!("Throughput: {:.2} requests/second", 
             results.len() as f64 / total_time.as_secs_f64());
    
    Ok(())
}
```

### Load Balancing Across Multiple Servers

```rust
use wip_rust::prelude::*;
use std::sync::atomic::{AtomicUsize, Ordering};
use std::sync::Arc;
use tokio;

struct LoadBalancedWeatherClient {
    clients: Vec<WeatherClient>,
    current: AtomicUsize,
}

impl LoadBalancedWeatherClient {
    fn new(server_addresses: Vec<&str>) -> Self {
        let clients = server_addresses
            .into_iter()
            .map(|addr| WeatherClient::new(addr))
            .collect();
        
        Self {
            clients,
            current: AtomicUsize::new(0),
        }
    }
    
    fn next_client(&self) -> &WeatherClient {
        let index = self.current.fetch_add(1, Ordering::Relaxed) % self.clients.len();
        &self.clients[index]
    }
    
    async fn get_weather_balanced(
        &self,
        lat: f64,
        lng: f64,
    ) -> Result<std::collections::HashMap<String, u128>, Box<dyn std::error::Error + Send + Sync>> {
        let client = self.next_client();
        
        // Try the selected client
        let result = tokio::task::spawn_blocking({
            let client = WeatherClient::new(&format!("127.0.0.1:4110")); // Clone for move
            move || client.get_weather_by_coordinates(lat, lng, true, true, false, false, false, 0)
        }).await?;
        
        match result {
            Ok(data) => Ok(data),
            Err(e) => {
                // If first client fails, try with another client
                println!("Primary client failed, trying fallback: {}", e);
                
                let fallback_client = self.next_client();
                let fallback_result = tokio::task::spawn_blocking({
                    let client = WeatherClient::new(&format!("127.0.0.1:4110")); // Clone for move
                    move || client.get_weather_by_coordinates(lat, lng, true, true, false, false, false, 0)
                }).await?;
                
                Ok(fallback_result?)
            }
        }
    }
}

#[tokio::main]
async fn load_balanced_requests() -> Result<(), Box<dyn std::error::Error>> {
    // In a real scenario, you'd have multiple server addresses
    let server_addresses = vec![
        "127.0.0.1:4110",
        "127.0.0.1:4110", // Same server for demo, but would be different IPs
        "127.0.0.1:4110",
    ];
    
    let load_balancer = Arc::new(LoadBalancedWeatherClient::new(server_addresses));
    
    let coordinates = vec![
        (35.6812, 139.7671, "Tokyo"),
        (34.6937, 135.5023, "Osaka"),
        (35.0116, 135.7681, "Kyoto"),
    ];
    
    println!("⚖️  Testing load-balanced requests...");
    
    let futures = coordinates.into_iter().enumerate().map(|(i, (lat, lng, city))| {
        let load_balancer = Arc::clone(&load_balancer);
        async move {
            println!("🔄 Request {} for {}", i + 1, city);
            
            match load_balancer.get_weather_balanced(lat, lng).await {
                Ok(weather_data) => {
                    println!("✅ {} - Success", city);
                    Some(weather_data)
                },
                Err(e) => {
                    println!("❌ {} - Failed: {}", city, e);
                    None
                }
            }
        }
    });
    
    let results = futures::future::join_all(futures).await;
    let successful_count = results.iter().filter(|r| r.is_some()).count();
    
    println!("\n📊 Load Balancing Results:");
    println!("Successful requests: {}/{}", successful_count, results.len());
    
    Ok(())
}
```

## Custom Packet Manipulation

### Creating Custom Packet Types

```rust
use wip_rust::prelude::*;
use wip_rust::wip_common_rs::packet::core::bit_utils::{extract_bits, set_bits};
use wip_rust::wip_common_rs::packet::core::checksum::{embed_checksum12_le, verify_checksum12};

struct CustomWeatherPacket {
    raw_data: Vec<u8>,
}

impl CustomWeatherPacket {
    fn new() -> Self {
        let mut packet = Self {
            raw_data: vec![0u8; 32], // 32-byte custom packet
        };
        
        // Set default values
        packet.set_version(1);
        packet.set_packet_type(99); // Custom type
        packet.set_timestamp(std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .as_secs());
        
        packet
    }
    
    fn set_version(&mut self, version: u8) {
        self.raw_data[0] = (self.raw_data[0] & 0xF0) | (version & 0x0F);
    }
    
    fn get_version(&self) -> u8 {
        self.raw_data[0] & 0x0F
    }
    
    fn set_packet_type(&mut self, packet_type: u8) {
        self.raw_data[1] = packet_type;
    }
    
    fn get_packet_type(&self) -> u8 {
        self.raw_data[1]
    }
    
    fn set_timestamp(&mut self, timestamp: u64) {
        let timestamp_bytes = timestamp.to_le_bytes();
        self.raw_data[2..10].copy_from_slice(&timestamp_bytes);
    }
    
    fn get_timestamp(&self) -> u64 {
        let mut bytes = [0u8; 8];
        bytes.copy_from_slice(&self.raw_data[2..10]);
        u64::from_le_bytes(bytes)
    }
    
    fn set_custom_data(&mut self, data: &[u8]) {
        let max_len = self.raw_data.len() - 12; // Reserve space for header and checksum
        let copy_len = std::cmp::min(data.len(), max_len);
        self.raw_data[10..10 + copy_len].copy_from_slice(&data[..copy_len]);
    }
    
    fn get_custom_data(&self) -> &[u8] {
        &self.raw_data[10..self.raw_data.len() - 2]
    }
    
    fn finalize(&mut self) -> Result<(), Box<dyn std::error::Error>> {
        // Embed checksum
        embed_checksum12_le(&mut self.raw_data);
        Ok(())
    }
    
    fn verify(&self) -> Result<(), Box<dyn std::error::Error>> {
        verify_checksum12(&self.raw_data)?;
        Ok(())
    }
    
    fn to_bytes(&self) -> Vec<u8> {
        self.raw_data.clone()
    }
}

fn custom_packet_example() -> Result<(), Box<dyn std::error::Error>> {
    println!("🔧 Creating custom weather packet...");
    
    let mut packet = CustomWeatherPacket::new();
    
    // Set custom weather data
    let custom_weather_data = b"CUSTOM_WEATHER_DATA_TOKYO_25C_SUNNY";
    packet.set_custom_data(custom_weather_data);
    
    // Finalize packet (adds checksum)
    packet.finalize()?;
    
    println!("✅ Packet created:");
    println!("  Version: {}", packet.get_version());
    println!("  Type: {}", packet.get_packet_type());
    println!("  Timestamp: {}", packet.get_timestamp());
    println!("  Custom data: {:?}", std::str::from_utf8(packet.get_custom_data())?);
    println!("  Total size: {} bytes", packet.to_bytes().len());
    
    // Verify packet integrity
    packet.verify()?;
    println!("✅ Packet integrity verified");
    
    // Simulate packet transmission (convert to bytes and back)
    let transmitted_bytes = packet.to_bytes();
    println!("📡 Transmitted {} bytes", transmitted_bytes.len());
    
    // Verify received packet
    verify_checksum12(&transmitted_bytes)?;
    println!("✅ Received packet integrity verified");
    
    Ok(())
}
```

### Packet Analysis and Debugging

```rust
use wip_rust::prelude::*;
use wip_rust::wip_common_rs::packet::core::bit_utils::{extract_bits, bytes_to_u128_le};
use wip_rust::wip_common_rs::packet::core::checksum::{verify_checksum12, get_checksum_from_packet};

struct PacketAnalyzer;

impl PacketAnalyzer {
    fn analyze_packet(packet_bytes: &[u8]) -> Result<(), Box<dyn std::error::Error>> {
        println!("🔍 Analyzing packet ({} bytes):", packet_bytes.len());
        println!("Raw data: {:02X?}", &packet_bytes[..std::cmp::min(16, packet_bytes.len())]);
        
        if packet_bytes.len() < 2 {
            println!("❌ Packet too short for analysis");
            return Ok(());
        }
        
        // Analyze header
        let header_u16 = u16::from_le_bytes([packet_bytes[0], packet_bytes[1]]);
        let version = extract_bits(header_u16 as u128, 0, 4);
        let packet_id = extract_bits(header_u16 as u128, 4, 12);
        
        println!("📋 Header Analysis:");
        println!("  Version: {}", version);
        println!("  Packet ID: {}", packet_id);
        
        // Analyze timestamp if available
        if packet_bytes.len() >= 10 {
            let timestamp_bytes = &packet_bytes[2..10];
            let timestamp = u64::from_le_bytes(timestamp_bytes.try_into().unwrap());
            let datetime = chrono::DateTime::from_timestamp(timestamp as i64, 0);
            
            println!("⏰ Timestamp Analysis:");
            println!("  Raw timestamp: {}", timestamp);
            if let Some(dt) = datetime {
                println!("  Date/Time: {}", dt.format("%Y-%m-%d %H:%M:%S UTC"));
                
                let now = chrono::Utc::now().timestamp() as u64;
                let age = now.saturating_sub(timestamp);
                println!("  Age: {} seconds", age);
                
                if age > 300 {
                    println!("  ⚠️  Warning: Packet is older than 5 minutes");
                }
            }
        }
        
        // Checksum analysis
        if packet_bytes.len() >= 2 {
            match verify_checksum12(packet_bytes) {
                Ok(_) => {
                    println!("✅ Checksum: Valid");
                    if let Ok(checksum) = get_checksum_from_packet(packet_bytes) {
                        println!("  Checksum value: 0x{:03X}", checksum);
                    }
                },
                Err(e) => {
                    println!("❌ Checksum: Invalid - {}", e);
                    if let Ok(embedded_checksum) = get_checksum_from_packet(packet_bytes) {
                        println!("  Embedded checksum: 0x{:03X}", embedded_checksum);
                        
                        // Calculate expected checksum
                        use wip_rust::wip_common_rs::packet::core::checksum::calc_checksum12;
                        let data_for_checksum = &packet_bytes[..packet_bytes.len() - 2];
                        let expected_checksum = calc_checksum12(data_for_checksum);
                        println!("  Expected checksum: 0x{:03X}", expected_checksum);
                    }
                }
            }
        }
        
        // Data section analysis
        if packet_bytes.len() > 12 {
            let data_section = &packet_bytes[10..packet_bytes.len() - 2];
            println!("📊 Data Section:");
            println!("  Size: {} bytes", data_section.len());
            
            // Try to interpret as string
            if let Ok(text) = std::str::from_utf8(data_section) {
                if text.is_ascii() && !text.chars().any(|c| c.is_control()) {
                    println!("  As text: \"{}\"", text);
                }
            }
            
            // Show hex dump
            println!("  Hex dump: {:02X?}", &data_section[..std::cmp::min(32, data_section.len())]);
            if data_section.len() > 32 {
                println!("  ... (truncated, {} more bytes)", data_section.len() - 32);
            }
        }
        
        Ok(())
    }
    
    fn compare_packets(packet1: &[u8], packet2: &[u8]) {
        println!("🔍 Comparing two packets:");
        println!("Packet 1: {} bytes", packet1.len());
        println!("Packet 2: {} bytes", packet2.len());
        
        let min_len = std::cmp::min(packet1.len(), packet2.len());
        let max_len = std::cmp::max(packet1.len(), packet2.len());
        
        let mut differences = 0;
        let mut first_difference: Option<usize> = None;
        
        for i in 0..min_len {
            if packet1[i] != packet2[i] {
                differences += 1;
                if first_difference.is_none() {
                    first_difference = Some(i);
                }
                
                if differences <= 10 { // Show first 10 differences
                    println!("  Byte {}: 0x{:02X} vs 0x{:02X}", i, packet1[i], packet2[i]);
                }
            }
        }
        
        if packet1.len() != packet2.len() {
            println!("  Size difference: {} bytes", max_len - min_len);
        }
        
        if differences == 0 && packet1.len() == packet2.len() {
            println!("✅ Packets are identical");
        } else {
            println!("❌ Packets differ in {} bytes", differences);
            if let Some(first_diff) = first_difference {
                println!("  First difference at byte {}", first_diff);
            }
        }
    }
}

fn packet_analysis_example() -> Result<(), Box<dyn std::error::Error>> {
    println!("🧪 Packet Analysis Example");
    
    // Create a sample packet
    let mut location_request = LocationRequest::new();
    location_request.set_latitude(35.6812);
    location_request.set_longitude(139.7671);
    location_request.set_weather_flag(true);
    location_request.set_temperature_flag(true);
    
    let packet_bytes = location_request.to_bytes();
    
    // Analyze the packet
    PacketAnalyzer::analyze_packet(&packet_bytes)?;
    
    // Create a second packet for comparison
    let mut modified_request = LocationRequest::new();
    modified_request.set_latitude(34.6937); // Different coordinates
    modified_request.set_longitude(135.5023);
    modified_request.set_weather_flag(true);
    modified_request.set_temperature_flag(false); // Different flag
    
    let modified_bytes = modified_request.to_bytes();
    
    println!("\n" + "=".repeat(50).as_str());
    
    // Compare packets
    PacketAnalyzer::compare_packets(&packet_bytes, &modified_bytes);
    
    Ok(())
}
```

## Advanced Error Recovery

### Circuit Breaker Implementation

```rust
use std::sync::{Arc, Mutex};
use std::time::{Duration, Instant};
use wip_rust::prelude::*;

#[derive(Debug, Clone, PartialEq)]
enum CircuitState {
    Closed,   // Normal operation
    Open,     // Failing, reject requests
    HalfOpen, // Test if service recovered
}

struct CircuitBreaker {
    failure_count: Arc<Mutex<u32>>,
    last_failure_time: Arc<Mutex<Option<Instant>>>,
    failure_threshold: u32,
    recovery_timeout: Duration,
    state: Arc<Mutex<CircuitState>>,
}

impl CircuitBreaker {
    fn new(failure_threshold: u32, recovery_timeout: Duration) -> Self {
        Self {
            failure_count: Arc::new(Mutex::new(0)),
            last_failure_time: Arc::new(Mutex::new(None)),
            failure_threshold,
            recovery_timeout,
            state: Arc::new(Mutex::new(CircuitState::Closed)),
        }
    }
    
    fn call<F, T, E>(&self, operation: F) -> Result<T, CircuitBreakerError<E>>
    where
        F: FnOnce() -> Result<T, E>,
        E: std::fmt::Debug,
    {
        // Check circuit state
        {
            let mut state = self.state.lock().unwrap();
            match *state {
                CircuitState::Open => {
                    let last_failure = self.last_failure_time.lock().unwrap();
                    if let Some(failure_time) = *last_failure {
                        if failure_time.elapsed() > self.recovery_timeout {
                            *state = CircuitState::HalfOpen;
                        } else {
                            return Err(CircuitBreakerError::CircuitOpen);
                        }
                    }
                },
                CircuitState::HalfOpen => {
                    // Allow one test request through
                },
                CircuitState::Closed => {
                    // Normal operation
                }
            }
        }
        
        // Execute the operation
        match operation() {
            Ok(result) => {
                // Success: reset failure count and close circuit
                *self.failure_count.lock().unwrap() = 0;
                *self.state.lock().unwrap() = CircuitState::Closed;
                Ok(result)
            },
            Err(error) => {
                // Failure: increment counter and potentially open circuit
                let mut count = self.failure_count.lock().unwrap();
                *count += 1;
                *self.last_failure_time.lock().unwrap() = Some(Instant::now());
                
                if *count >= self.failure_threshold {
                    *self.state.lock().unwrap() = CircuitState::Open;
                }
                
                Err(CircuitBreakerError::OperationFailed(error))
            }
        }
    }
    
    fn get_state(&self) -> CircuitState {
        self.state.lock().unwrap().clone()
    }
    
    fn get_failure_count(&self) -> u32 {
        *self.failure_count.lock().unwrap()
    }
}

#[derive(Debug)]
enum CircuitBreakerError<E> {
    CircuitOpen,
    OperationFailed(E),
}

impl<E: std::fmt::Display> std::fmt::Display for CircuitBreakerError<E> {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            CircuitBreakerError::CircuitOpen => write!(f, "Circuit breaker is open"),
            CircuitBreakerError::OperationFailed(err) => write!(f, "Operation failed: {}", err),
        }
    }
}

impl<E: std::error::Error + 'static> std::error::Error for CircuitBreakerError<E> {
    fn source(&self) -> Option<&(dyn std::error::Error + 'static)> {
        match self {
            CircuitBreakerError::CircuitOpen => None,
            CircuitBreakerError::OperationFailed(err) => Some(err),
        }
    }
}

struct ResilientWeatherClient {
    client: WeatherClient,
    circuit_breaker: CircuitBreaker,
}

impl ResilientWeatherClient {
    fn new(server_address: &str) -> Self {
        Self {
            client: WeatherClient::new(server_address),
            circuit_breaker: CircuitBreaker::new(
                3, // Fail after 3 consecutive errors
                Duration::from_secs(30), // Try again after 30 seconds
            ),
        }
    }
    
    fn get_weather_with_circuit_breaker(
        &self,
        lat: f64,
        lng: f64,
    ) -> Result<std::collections::HashMap<String, u128>, CircuitBreakerError<Box<dyn std::error::Error>>> {
        self.circuit_breaker.call(|| {
            self.client.get_weather_by_coordinates(
                lat, lng, true, true, false, false, false, 0
            ).map_err(|e| e as Box<dyn std::error::Error>)
        })
    }
}

fn circuit_breaker_example() -> Result<(), Box<dyn std::error::Error>> {
    let resilient_client = ResilientWeatherClient::new("127.0.0.1:4110");
    
    println!("🔄 Testing circuit breaker pattern...");
    
    // Simulate multiple requests, some of which may fail
    let test_coordinates = vec![
        (35.6812, 139.7671, "Tokyo"),
        (34.6937, 135.5023, "Osaka"),
        (35.0116, 135.7681, "Kyoto"),
        // Add some invalid coordinates to trigger failures
        (999.0, 999.0, "Invalid1"),
        (888.0, 888.0, "Invalid2"),
        (777.0, 777.0, "Invalid3"),
        (35.6812, 139.7671, "Tokyo Again"), // This should be circuit-broken
    ];
    
    for (lat, lng, location) in test_coordinates {
        println!("\n🌍 Testing {}", location);
        println!("Circuit state: {:?}", resilient_client.circuit_breaker.get_state());
        println!("Failure count: {}", resilient_client.circuit_breaker.get_failure_count());
        
        match resilient_client.get_weather_with_circuit_breaker(lat, lng) {
            Ok(weather_data) => {
                println!("✅ Success: {:?}", weather_data.get("area_code"));
            },
            Err(CircuitBreakerError::CircuitOpen) => {
                println!("🚫 Circuit breaker is open - request blocked");
            },
            Err(CircuitBreakerError::OperationFailed(e)) => {
                println!("❌ Operation failed: {}", e);
            }
        }
        
        // Small delay between requests
        std::thread::sleep(Duration::from_millis(500));
    }
    
    // Wait for recovery timeout and test again
    println!("\n⏳ Waiting for circuit breaker recovery...");
    std::thread::sleep(Duration::from_secs(31)); // Wait longer than recovery timeout
    
    println!("🔄 Testing after recovery timeout...");
    match resilient_client.get_weather_with_circuit_breaker(35.6812, 139.7671) {
        Ok(weather_data) => {
            println!("✅ Circuit recovered! Weather data: {:?}", weather_data.get("area_code"));
        },
        Err(e) => {
            println!("❌ Still failing: {}", e);
        }
    }
    
    Ok(())
}
```

### Retry with Exponential Backoff

```rust
use wip_rust::prelude::*;
use std::time::Duration;
use tokio::time::sleep;

struct RetryConfig {
    max_attempts: u32,
    initial_delay: Duration,
    max_delay: Duration,
    backoff_multiplier: f64,
}

impl Default for RetryConfig {
    fn default() -> Self {
        Self {
            max_attempts: 5,
            initial_delay: Duration::from_millis(100),
            max_delay: Duration::from_secs(10),
            backoff_multiplier: 2.0,
        }
    }
}

struct RetryableWeatherClient {
    client: AsyncWeatherClient,
    retry_config: RetryConfig,
}

impl RetryableWeatherClient {
    fn new(server_address: &str, retry_config: Option<RetryConfig>) -> Self {
        Self {
            client: AsyncWeatherClient::new(server_address),
            retry_config: retry_config.unwrap_or_default(),
        }
    }
    
    async fn get_weather_with_retry(
        &self,
        lat: f64,
        lng: f64,
    ) -> Result<std::collections::HashMap<String, u128>, Box<dyn std::error::Error + Send + Sync>> {
        let mut attempt = 1;
        let mut delay = self.retry_config.initial_delay;
        
        loop {
            println!("🔄 Attempt {} of {}", attempt, self.retry_config.max_attempts);
            
            match self.client.get_weather_by_coordinates_async(
                lat, lng, true, true, false, false, false, 0
            ).await {
                Ok(data) => {
                    println!("✅ Success on attempt {}", attempt);
                    return Ok(data);
                },
                Err(e) => {
                    if attempt >= self.retry_config.max_attempts {
                        println!("❌ All {} attempts failed", self.retry_config.max_attempts);
                        return Err(e);
                    }
                    
                    println!("⚠️  Attempt {} failed: {}", attempt, e);
                    println!("⏳ Waiting {:?} before retry...", delay);
                    
                    sleep(delay).await;
                    
                    // Exponential backoff
                    delay = std::cmp::min(
                        Duration::from_millis(
                            (delay.as_millis() as f64 * self.retry_config.backoff_multiplier) as u64
                        ),
                        self.retry_config.max_delay,
                    );
                    
                    attempt += 1;
                }
            }
        }
    }
}

#[tokio::main]
async fn retry_example() -> Result<(), Box<dyn std::error::Error>> {
    let retry_config = RetryConfig {
        max_attempts: 4,
        initial_delay: Duration::from_millis(500),
        max_delay: Duration::from_secs(5),
        backoff_multiplier: 1.5,
    };
    
    let retryable_client = RetryableWeatherClient::new("127.0.0.1:4110", Some(retry_config));
    
    println!("🔄 Testing retry with exponential backoff...");
    
    // Test with valid coordinates
    match retryable_client.get_weather_with_retry(35.6812, 139.7671).await {
        Ok(weather_data) => {
            println!("🌤️  Weather data retrieved: {:?}", weather_data.get("area_code"));
        },
        Err(e) => {
            println!("❌ Final failure: {}", e);
        }
    }
    
    Ok(())
}
```

## Monitoring and Metrics

### Comprehensive Metrics Collection

```rust
use wip_rust::prelude::*;
use std::sync::atomic::{AtomicU64, Ordering};
use std::sync::Arc;
use std::time::{Duration, Instant};
use std::collections::HashMap;
use tokio::time::interval;
use tokio_stream::{wrappers::IntervalStream, StreamExt};

#[derive(Default)]
struct WeatherClientMetrics {
    requests_total: AtomicU64,
    requests_successful: AtomicU64,
    requests_failed: AtomicU64,
    response_time_total_ms: AtomicU64,
    errors_by_type: parking_lot::Mutex<HashMap<String, u64>>,
    start_time: std::sync::OnceLock<Instant>,
}

impl WeatherClientMetrics {
    fn new() -> Self {
        let metrics = Self::default();
        let _ = metrics.start_time.set(Instant::now());
        metrics
    }
    
    fn record_request(&self, success: bool, response_time: Duration, error_type: Option<&str>) {
        self.requests_total.fetch_add(1, Ordering::Relaxed);
        self.response_time_total_ms.fetch_add(response_time.as_millis() as u64, Ordering::Relaxed);
        
        if success {
            self.requests_successful.fetch_add(1, Ordering::Relaxed);
        } else {
            self.requests_failed.fetch_add(1, Ordering::Relaxed);
            
            if let Some(error_type) = error_type {
                let mut errors = self.errors_by_type.lock();
                *errors.entry(error_type.to_string()).or_insert(0) += 1;
            }
        }
    }
    
    fn get_success_rate(&self) -> f64 {
        let total = self.requests_total.load(Ordering::Relaxed);
        if total == 0 {
            return 0.0;
        }
        
        let successful = self.requests_successful.load(Ordering::Relaxed);
        successful as f64 / total as f64
    }
    
    fn get_average_response_time(&self) -> Duration {
        let total_requests = self.requests_total.load(Ordering::Relaxed);
        if total_requests == 0 {
            return Duration::from_millis(0);
        }
        
        let total_time_ms = self.response_time_total_ms.load(Ordering::Relaxed);
        Duration::from_millis(total_time_ms / total_requests)
    }
    
    fn get_requests_per_second(&self) -> f64 {
        if let Some(start_time) = self.start_time.get() {
            let elapsed = start_time.elapsed().as_secs_f64();
            if elapsed > 0.0 {
                let total_requests = self.requests_total.load(Ordering::Relaxed);
                return total_requests as f64 / elapsed;
            }
        }
        0.0
    }
    
    fn get_health_report(&self) -> String {
        let total = self.requests_total.load(Ordering::Relaxed);
        let successful = self.requests_successful.load(Ordering::Relaxed);
        let failed = self.requests_failed.load(Ordering::Relaxed);
        let success_rate = self.get_success_rate() * 100.0;
        let avg_response_time = self.get_average_response_time();
        let rps = self.get_requests_per_second();
        
        let mut report = format!(
            "📊 Weather Client Health Report\n\
             ================================\n\
             Total Requests: {}\n\
             Successful: {} ({:.2}%)\n\
             Failed: {} ({:.2}%)\n\
             Average Response Time: {:?}\n\
             Requests per Second: {:.2}\n",
            total,
            successful, success_rate,
            failed, 100.0 - success_rate,
            avg_response_time,
            rps
        );
        
        // Add error breakdown
        let errors = self.errors_by_type.lock();
        if !errors.is_empty() {
            report.push_str("\nError Breakdown:\n");
            for (error_type, count) in errors.iter() {
                let percentage = *count as f64 / failed as f64 * 100.0;
                report.push_str(&format!("  {}: {} ({:.1}%)\n", error_type, count, percentage));
            }
        }
        
        // Health status
        report.push_str(&format!("\nHealth Status: {}\n", 
            if success_rate >= 95.0 { "🟢 HEALTHY" }
            else if success_rate >= 80.0 { "🟡 DEGRADED" }
            else { "🔴 UNHEALTHY" }
        ));
        
        report
    }
}

struct MonitoredWeatherClient {
    client: AsyncWeatherClient,
    metrics: Arc<WeatherClientMetrics>,
}

impl MonitoredWeatherClient {
    fn new(server_address: &str) -> Self {
        Self {
            client: AsyncWeatherClient::new(server_address),
            metrics: Arc::new(WeatherClientMetrics::new()),
        }
    }
    
    async fn get_weather_monitored(
        &self,
        lat: f64,
        lng: f64,
    ) -> Result<std::collections::HashMap<String, u128>, Box<dyn std::error::Error + Send + Sync>> {
        let start_time = Instant::now();
        
        let result = self.client.get_weather_by_coordinates_async(
            lat, lng, true, true, false, false, false, 0
        ).await;
        
        let response_time = start_time.elapsed();
        
        match &result {
            Ok(_) => {
                self.metrics.record_request(true, response_time, None);
            },
            Err(e) => {
                let error_type = if e.to_string().contains("timeout") {
                    "timeout"
                } else if e.to_string().contains("connection") {
                    "connection"
                } else if e.to_string().contains("checksum") {
                    "checksum"
                } else {
                    "other"
                };
                
                self.metrics.record_request(false, response_time, Some(error_type));
            }
        }
        
        result
    }
    
    fn get_metrics(&self) -> Arc<WeatherClientMetrics> {
        Arc::clone(&self.metrics)
    }
}

#[tokio::main]
async fn monitoring_example() -> Result<(), Box<dyn std::error::Error>> {
    let monitored_client = MonitoredWeatherClient::new("127.0.0.1:4110");
    let metrics = monitored_client.get_metrics();
    
    // Start metrics reporting task
    let metrics_clone = Arc::clone(&metrics);
    let metrics_task = tokio::spawn(async move {
        let mut interval = interval(Duration::from_secs(10));
        loop {
            interval.tick().await;
            println!("\n{}", metrics_clone.get_health_report());
        }
    });
    
    // Simulate various weather requests
    println!("🚀 Starting monitored weather requests...");
    
    let test_locations = vec![
        (35.6812, 139.7671, "Tokyo"),
        (34.6937, 135.5023, "Osaka"),
        (35.0116, 135.7681, "Kyoto"),
        (43.0642, 141.3469, "Sapporo"),
        (33.5904, 130.4017, "Fukuoka"),
    ];
    
    // Generate load with varying success rates
    for round in 1..=3 {
        println!("\n🔄 Round {}", round);
        
        for (lat, lng, city) in &test_locations {
            // Make multiple concurrent requests per city
            let futures = (0..3).map(|i| {
                let client = &monitored_client;
                async move {
                    let result = client.get_weather_monitored(*lat, *lng).await;
                    (format!("{}-{}", city, i), result)
                }
            });
            
            let results = futures::future::join_all(futures).await;
            
            for (request_id, result) in results {
                match result {
                    Ok(_) => println!("✅ {}: Success", request_id),
                    Err(e) => println!("❌ {}: {}", request_id, e),
                }
            }
            
            // Small delay between cities
            tokio::time::sleep(Duration::from_millis(200)).await;
        }
        
        // Pause between rounds
        tokio::time::sleep(Duration::from_secs(2)).await;
    }
    
    // Final metrics report
    tokio::time::sleep(Duration::from_secs(1)).await;
    println!("\n{}", metrics.get_health_report());
    
    // Stop the metrics task
    metrics_task.abort();
    
    Ok(())
}
```

## Authentication and Security

### JWT Token-based Authentication

```rust
use wip_rust::prelude::*;
use serde::{Deserialize, Serialize};
use std::time::{SystemTime, UNIX_EPOCH};
use std::collections::HashMap;

#[derive(Debug, Serialize, Deserialize)]
struct WIPClaims {
    sub: String,        // Subject (user ID)
    exp: u64,          // Expiration time
    iat: u64,          // Issued at time
    permissions: Vec<String>, // WIP permissions
    area_codes: Vec<u32>, // Allowed area codes
}

impl WIPClaims {
    fn new(user_id: &str, ttl_seconds: u64) -> Self {
        let now = SystemTime::now().duration_since(UNIX_EPOCH).unwrap().as_secs();
        
        Self {
            sub: user_id.to_string(),
            exp: now + ttl_seconds,
            iat: now,
            permissions: vec![
                "weather:read".to_string(),
                "location:resolve".to_string(),
            ],
            area_codes: vec![130010, 140010, 270000], // Tokyo, Kanagawa, Osaka
        }
    }
    
    fn is_expired(&self) -> bool {
        let now = SystemTime::now().duration_since(UNIX_EPOCH).unwrap().as_secs();
        now > self.exp
    }
    
    fn can_access_area(&self, area_code: u32) -> bool {
        self.area_codes.is_empty() || self.area_codes.contains(&area_code)
    }
    
    fn has_permission(&self, permission: &str) -> bool {
        self.permissions.contains(&permission.to_string())
    }
}

struct SecureWeatherClient {
    client: WeatherClient,
    auth_token: Option<String>,
    claims: Option<WIPClaims>,
}

impl SecureWeatherClient {
    fn new(server_address: &str) -> Self {
        Self {
            client: WeatherClient::new(server_address),
            auth_token: None,
            claims: None,
        }
    }
    
    fn authenticate(&mut self, username: &str, password: &str) -> Result<(), Box<dyn std::error::Error>> {
        // In a real implementation, this would call an authentication service
        println!("🔐 Authenticating user: {}", username);
        
        // Simulate authentication
        if username == "weather_user" && password == "secure_password_123" {
            let claims = WIPClaims::new(username, 3600); // 1 hour TTL
            
            // In a real implementation, this would be a proper JWT token
            let token = format!("wip_token_{}_{}", username, claims.iat);
            
            self.auth_token = Some(token);
            self.claims = Some(claims);
            
            println!("✅ Authentication successful");
            println!("   Permissions: {:?}", self.claims.as_ref().unwrap().permissions);
            println!("   Area codes: {:?}", self.claims.as_ref().unwrap().area_codes);
            
            Ok(())
        } else {
            Err("Invalid credentials".into())
        }
    }
    
    fn get_weather_secure(
        &self,
        lat: f64,
        lng: f64,
    ) -> Result<std::collections::HashMap<String, u128>, Box<dyn std::error::Error>> {
        // Check authentication
        let claims = self.claims.as_ref().ok_or("Not authenticated")?;
        
        // Check token expiration
        if claims.is_expired() {
            return Err("Token expired".into());
        }
        
        // Check permissions
        if !claims.has_permission("weather:read") {
            return Err("Insufficient permissions".into());
        }
        
        // For demo purposes, resolve coordinates to area code manually
        // In a real implementation, this would use the location service
        let area_code = if lat >= 35.0 && lat <= 36.0 && lng >= 139.0 && lng <= 140.0 {
            130010 // Tokyo
        } else if lat >= 34.0 && lat <= 35.0 && lng >= 135.0 && lng <= 136.0 {
            270000 // Osaka
        } else {
            999999 // Unknown area
        };
        
        // Check area code access
        if !claims.can_access_area(area_code) {
            return Err(format!("Access denied for area code {}", area_code).into());
        }
        
        println!("🔒 Authorized request for area code: {}", area_code);
        
        // Make the actual request
        self.client.get_weather_by_coordinates(
            lat, lng, true, true, false, false, false, 0
        )
    }
    
    fn refresh_token(&mut self) -> Result<(), Box<dyn std::error::Error>> {
        let claims = self.claims.as_ref().ok_or("Not authenticated")?;
        
        if claims.is_expired() {
            return Err("Cannot refresh expired token".into());
        }
        
        // Create new claims with extended expiration
        let new_claims = WIPClaims::new(&claims.sub, 3600);
        let new_token = format!("wip_token_{}_{}", claims.sub, new_claims.iat);
        
        self.auth_token = Some(new_token);
        self.claims = Some(new_claims);
        
        println!("🔄 Token refreshed successfully");
        Ok(())
    }
    
    fn get_token_info(&self) -> Option<String> {
        if let Some(claims) = &self.claims {
            let remaining = claims.exp.saturating_sub(
                SystemTime::now().duration_since(UNIX_EPOCH).unwrap().as_secs()
            );
            Some(format!(
                "User: {}, Remaining: {}s, Permissions: {:?}",
                claims.sub, remaining, claims.permissions
            ))
        } else {
            None
        }
    }
}

fn security_example() -> Result<(), Box<dyn std::error::Error>> {
    let mut secure_client = SecureWeatherClient::new("127.0.0.1:4110");
    
    println!("🔒 Testing secure weather client...");
    
    // Try to make request without authentication
    println!("\n1. Testing unauthenticated request:");
    match secure_client.get_weather_secure(35.6812, 139.7671) {
        Ok(_) => println!("❌ This shouldn't happen - request succeeded without auth"),
        Err(e) => println!("✅ Correctly rejected: {}", e),
    }
    
    // Authenticate with wrong credentials
    println!("\n2. Testing authentication with wrong credentials:");
    match secure_client.authenticate("wrong_user", "wrong_password") {
        Ok(_) => println!("❌ This shouldn't happen - auth succeeded with wrong creds"),
        Err(e) => println!("✅ Correctly rejected: {}", e),
    }
    
    // Authenticate with correct credentials
    println!("\n3. Testing authentication with correct credentials:");
    secure_client.authenticate("weather_user", "secure_password_123")?;
    
    if let Some(token_info) = secure_client.get_token_info() {
        println!("Token info: {}", token_info);
    }
    
    // Make authorized requests
    println!("\n4. Testing authorized requests:");
    
    let test_locations = vec![
        (35.6812, 139.7671, "Tokyo (authorized)"),
        (34.6937, 135.5023, "Osaka (authorized)"), 
        (43.0642, 141.3469, "Sapporo (unauthorized area)"),
    ];
    
    for (lat, lng, description) in test_locations {
        println!("\nTesting {}", description);
        match secure_client.get_weather_secure(lat, lng) {
            Ok(weather_data) => {
                println!("✅ Success: {:?}", weather_data.get("area_code"));
            },
            Err(e) => {
                println!("❌ Rejected: {}", e);
            }
        }
    }
    
    // Test token refresh
    println!("\n5. Testing token refresh:");
    secure_client.refresh_token()?;
    if let Some(token_info) = secure_client.get_token_info() {
        println!("Refreshed token info: {}", token_info);
    }
    
    Ok(())
}
```

---

This advanced tutorial demonstrates sophisticated patterns for building production-ready applications with the WIP Rust library. These examples show how to handle complex scenarios involving async programming, performance optimization, security, and monitoring - all essential for enterprise-grade weather data applications.