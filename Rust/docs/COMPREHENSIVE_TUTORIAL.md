# WIP Rust Implementation - Comprehensive Tutorial

This comprehensive tutorial will guide you through using the WIP (Weather Transfer Protocol) Rust implementation from basic setup to advanced features.

## Table of Contents

1. [Prerequisites and Setup](#prerequisites-and-setup)
2. [Understanding WIP](#understanding-wip)
3. [Basic Weather Requests](#basic-weather-requests)
4. [Location Resolution](#location-resolution)
5. [Disaster Reporting](#disaster-reporting)
6. [Error Handling](#error-handling)
7. [Asynchronous Operations](#asynchronous-operations)
8. [Testing with Mock Servers](#testing-with-mock-servers)
9. [Production Best Practices](#production-best-practices)
10. [Performance Optimization](#performance-optimization)

## Prerequisites and Setup

### System Requirements

- Rust 1.70 or later
- 64-bit operating system (Windows, Linux, macOS)
- Network access for server communication
- Basic understanding of Rust programming

### Creating Your Project

Start by creating a new Rust project:

```bash
cargo new wip_weather_app
cd wip_weather_app
```

Add dependencies to your `Cargo.toml`:

```toml
[dependencies]
wip_rust = { path = "../path/to/wip_rust" }
tokio = { version = "1.0", features = ["full"] }
env_logger = "0.11"
log = "0.4"
serde_json = "1.0"
```

### Project Structure

Organize your project like this:

```
wip_weather_app/
├── src/
│   ├── main.rs
│   ├── weather.rs      # Weather-related functions
│   ├── location.rs     # Location handling
│   ├── reporting.rs    # Disaster reporting
│   └── config.rs       # Configuration management
├── examples/
│   ├── basic_weather.rs
│   ├── async_example.rs
│   └── disaster_report.rs
└── Cargo.toml
```

## Understanding WIP

### Protocol Overview

WIP (Weather Transfer Protocol) is designed for:
- **Lightweight communication**: 16-byte minimum packets
- **IoT compatibility**: Efficient for resource-constrained devices
- **Real-time data**: Fast weather and disaster information
- **Distributed architecture**: Multiple specialized servers

### Server Types

1. **Weather Server (Port 4110)**: Main proxy server
2. **Location Server (Port 4109)**: Coordinate to area code resolution
3. **Query Server (Port 4111)**: Direct weather data queries
4. **Report Server (Port 4112)**: Sensor and disaster reports

### Data Flow

```
Client Request → Weather Server → Location/Query/Report Server → Response
```

## Basic Weather Requests

### Your First Weather Request

Let's start with a simple example (`src/main.rs`):

```rust
use wip_rust::wip_common_rs::clients::weather_client::WeatherClient;
use std::error::Error;

fn main() -> Result<(), Box<dyn Error>> {
    // Initialize logging
    env_logger::init();
    
    // Create weather client
    let client = WeatherClient::new("127.0.0.1:4110");
    
    // Request weather for Tokyo
    let weather = client.get_weather_by_coordinates(
        35.6812,  // Latitude
        139.7671, // Longitude
        true,     // Weather data
        true,     // Temperature
        true,     // Precipitation probability
        false,    // Alerts (skip for now)
        false,    // Disaster info (skip for now)
        0         // Day offset (0=today, 1=tomorrow)
    )?;
    
    // Display results
    println!("🌤️  Weather for Tokyo:");
    println!("   Area Code: {}", weather.get("area_code").unwrap_or(&0));
    println!("   Weather Code: {}", weather.get("weather_code").unwrap_or(&0));
    println!("   Temperature: {}°C", weather.get("temperature").unwrap_or(&0));
    println!("   Precipitation: {}%", weather.get("precipitation_prob").unwrap_or(&0));
    
    Ok(())
}
```

### Working with Multiple Cities

Create `src/weather.rs`:

```rust
use wip_rust::wip_common_rs::clients::weather_client::WeatherClient;
use std::collections::HashMap;
use std::error::Error;
use log::{info, warn};

pub struct WeatherService {
    client: WeatherClient,
}

impl WeatherService {
    pub fn new(server_address: &str) -> Self {
        let client = WeatherClient::new(server_address);
        Self { client }
    }
    
    pub fn get_weather_for_cities(&self, cities: Vec<(f64, f64, &str)>) -> HashMap<String, WeatherData> {
        let mut results = HashMap::new();
        
        for (lat, lng, city_name) in cities {
            info!("Requesting weather for {}", city_name);
            
            match self.client.get_weather_by_coordinates(lat, lng, true, true, true, false, false, 0) {
                Ok(weather) => {
                    let weather_data = WeatherData {
                        city: city_name.to_string(),
                        area_code: weather.get("area_code").copied().unwrap_or(0),
                        weather_code: weather.get("weather_code").copied().unwrap_or(0),
                        temperature: weather.get("temperature").copied().unwrap_or(0) as i32,
                        precipitation_prob: weather.get("precipitation_prob").copied().unwrap_or(0) as u32,
                    };
                    results.insert(city_name.to_string(), weather_data);
                },
                Err(e) => {
                    warn!("Failed to get weather for {}: {}", city_name, e);
                }
            }
            
            // Rate limiting - be nice to the server
            std::thread::sleep(std::time::Duration::from_millis(100));
        }
        
        results
    }
}

#[derive(Debug, Clone)]
pub struct WeatherData {
    pub city: String,
    pub area_code: u128,
    pub weather_code: u128,
    pub temperature: i32,
    pub precipitation_prob: u32,
}

impl WeatherData {
    pub fn weather_description(&self) -> &'static str {
        match self.weather_code {
            100..=199 => "Clear/Sunny ☀️",
            200..=299 => "Cloudy ☁️",
            300..=399 => "Rainy 🌧️",
            400..=499 => "Snowy ❄️",
            _ => "Unknown 🤔",
        }
    }
    
    pub fn display(&self) {
        println!("🏙️  {}:", self.city);
        println!("   Weather: {}", self.weather_description());
        println!("   Temperature: {}°C", self.temperature);
        println!("   Precipitation: {}%", self.precipitation_prob);
        println!("   Area Code: {}", self.area_code);
    }
}

// Usage example
pub fn demo_multi_city_weather() -> Result<(), Box<dyn Error>> {
    let weather_service = WeatherService::new("127.0.0.1:4110");
    
    let cities = vec![
        (35.6812, 139.7671, "Tokyo"),
        (34.6937, 135.5023, "Osaka"),
        (43.0642, 141.3469, "Sapporo"),
        (33.5904, 130.4017, "Fukuoka"),
        (35.0116, 135.7681, "Kyoto"),
    ];
    
    println!("🌏 Weather Report for Major Japanese Cities");
    println!("==========================================");
    
    let weather_data = weather_service.get_weather_for_cities(cities);
    
    for (city, data) in weather_data {
        data.display();
        println!();
    }
    
    Ok(())
}
```

## Location Resolution

Create `src/location.rs`:

```rust
use wip_rust::wip_common_rs::clients::location_client::LocationClient;
use std::collections::HashMap;
use std::error::Error;
use log::{info, error};

pub struct LocationService {
    client: LocationClient,
    cache: HashMap<(i32, i32), u32>, // Simple coordinate cache
}

impl LocationService {
    pub fn new(server_address: &str) -> Self {
        let client = LocationClient::new(server_address);
        Self {
            client,
            cache: HashMap::new(),
        }
    }
    
    pub fn resolve_coordinates(&mut self, lat: f64, lng: f64) -> Result<u32, Box<dyn Error>> {
        // Create cache key (rounded to avoid floating point issues)
        let cache_key = ((lat * 10000.0) as i32, (lng * 10000.0) as i32);
        
        // Check cache first
        if let Some(&area_code) = self.cache.get(&cache_key) {
            info!("Cache hit for coordinates ({:.4}, {:.4})", lat, lng);
            return Ok(area_code);
        }
        
        // Query server
        info!("Resolving coordinates ({:.4}, {:.4})", lat, lng);
        match self.client.resolve_coordinates(lat, lng) {
            Ok(area_code) => {
                // Cache the result
                self.cache.insert(cache_key, area_code);
                Ok(area_code)
            },
            Err(e) => {
                error!("Failed to resolve coordinates: {}", e);
                Err(e)
            }
        }
    }
    
    pub fn validate_area_code(&self, area_code: u32) -> bool {
        // JMA area codes are 6-digit numbers
        area_code >= 100000 && area_code <= 999999
    }
    
    pub fn batch_resolve(&mut self, coordinates: Vec<(f64, f64)>) -> HashMap<(f64, f64), u32> {
        let mut results = HashMap::new();
        
        for (lat, lng) in coordinates {
            match self.resolve_coordinates(lat, lng) {
                Ok(area_code) => {
                    results.insert((lat, lng), area_code);
                },
                Err(e) => {
                    error!("Failed to resolve ({:.4}, {:.4}): {}", lat, lng, e);
                }
            }
            
            // Rate limiting
            std::thread::sleep(std::time::Duration::from_millis(50));
        }
        
        results
    }
}

// Common Japanese locations for testing
pub fn get_major_japanese_locations() -> Vec<(f64, f64, &'static str)> {
    vec![
        (35.6812, 139.7671, "Tokyo Station"),
        (34.6937, 135.5023, "Osaka Castle"),
        (43.0642, 141.3469, "Sapporo Snow Festival"),
        (33.5904, 130.4017, "Fukuoka Tower"),
        (35.0116, 135.7681, "Kyoto Imperial Palace"),
        (35.1815, 136.9066, "Nagoya Castle"),
        (34.3853, 132.4553, "Hiroshima Peace Memorial"),
        (26.2123, 127.6792, "Naha, Okinawa"),
    ]
}

pub fn demo_location_resolution() -> Result<(), Box<dyn Error>> {
    let mut location_service = LocationService::new("127.0.0.1:4109");
    
    println!("📍 Location Resolution Demo");
    println!("===========================");
    
    let locations = get_major_japanese_locations();
    
    for (lat, lng, name) in locations {
        match location_service.resolve_coordinates(lat, lng) {
            Ok(area_code) => {
                let status = if location_service.validate_area_code(area_code) {
                    "✅ Valid"
                } else {
                    "⚠️  Unusual"
                };
                
                println!("🏛️  {}: ({:.4}, {:.4})", name, lat, lng);
                println!("   Area Code: {} ({})", area_code, status);
            },
            Err(e) => {
                println!("❌ {}: Resolution failed - {}", name, e);
            }
        }
        println!();
    }
    
    Ok(())
}
```

## Disaster Reporting

Create `src/reporting.rs`:

```rust
use wip_rust::wip_common_rs::clients::report_client::ReportClient;
use std::error::Error;
use log::{info, error};
use serde_json::json;

pub struct DisasterReportingService {
    client: ReportClient,
}

impl DisasterReportingService {
    pub fn new(server_address: &str) -> Self {
        let client = ReportClient::new(server_address);
        Self { client }
    }
    
    pub fn report_earthquake(&self, severity: u8, location: Option<(f64, f64)>, details: &str) -> Result<u64, Box<dyn Error>> {
        info!("Reporting earthquake with severity {}", severity);
        
        let description = format!("Earthquake Detection: Severity {}/10. {}", severity, details);
        
        self.client.send_sensor_report(
            "earthquake",
            severity,
            &description,
            location.map(|(lat, _)| lat),
            location.map(|(_, lng)| lng)
        )
    }
    
    pub fn report_weather_sensor(&self, sensor_type: &str, value: f64, location: (f64, f64)) -> Result<u64, Box<dyn Error>> {
        let severity = match sensor_type {
            "temperature" => if value > 35.0 || value < -10.0 { 3 } else { 1 },
            "humidity" => if value > 80.0 { 2 } else { 1 },
            "wind_speed" => if value > 50.0 { 4 } else if value > 30.0 { 2 } else { 1 },
            "pressure" => 1, // Normal severity for pressure readings
            _ => 1,
        };
        
        let description = format!("{} reading: {:.2} at location ({:.4}, {:.4})", 
            sensor_type, value, location.0, location.1);
        
        self.client.send_sensor_report(
            sensor_type,
            severity,
            &description,
            Some(location.0),
            Some(location.1)
        )
    }
    
    pub fn emergency_report(&self, disaster_type: &str, severity: u8, location: (f64, f64), description: &str) -> Result<u64, Box<dyn Error>> {
        info!("EMERGENCY: {} at ({:.4}, {:.4})", disaster_type, location.0, location.1);
        
        let emergency_description = format!("🚨 EMERGENCY: {} (Severity: {}/10)\nLocation: ({:.4}, {:.4})\nDetails: {}", 
            disaster_type, severity, location.0, location.1, description);
        
        self.client.send_sensor_report(
            disaster_type,
            severity,
            &emergency_description,
            Some(location.0),
            Some(location.1)
        )
    }
}

pub struct SensorNetwork {
    reporting_service: DisasterReportingService,
    sensors: Vec<SensorData>,
}

#[derive(Debug, Clone)]
pub struct SensorData {
    pub id: String,
    pub location: (f64, f64),
    pub sensor_type: String,
    pub value: f64,
    pub timestamp: std::time::SystemTime,
}

impl SensorNetwork {
    pub fn new(server_address: &str) -> Self {
        Self {
            reporting_service: DisasterReportingService::new(server_address),
            sensors: Vec::new(),
        }
    }
    
    pub fn add_sensor(&mut self, id: String, location: (f64, f64), sensor_type: String) {
        let sensor = SensorData {
            id,
            location,
            sensor_type,
            value: 0.0,
            timestamp: std::time::SystemTime::now(),
        };
        self.sensors.push(sensor);
    }
    
    pub fn simulate_sensor_readings(&mut self) -> Result<Vec<u64>, Box<dyn Error>> {
        let mut report_ids = Vec::new();
        
        for sensor in &mut self.sensors {
            // Simulate sensor reading
            sensor.value = match sensor.sensor_type.as_str() {
                "temperature" => 15.0 + fastrand::f64() * 20.0, // 15-35°C
                "humidity" => 30.0 + fastrand::f64() * 50.0,    // 30-80%
                "wind_speed" => fastrand::f64() * 40.0,         // 0-40 km/h
                "pressure" => 1000.0 + fastrand::f64() * 50.0,  // 1000-1050 hPa
                _ => fastrand::f64() * 100.0,
            };
            sensor.timestamp = std::time::SystemTime::now();
            
            // Report reading
            match self.reporting_service.report_weather_sensor(&sensor.sensor_type, sensor.value, sensor.location) {
                Ok(report_id) => {
                    info!("Sensor {} reported: {} = {:.2}", sensor.id, sensor.sensor_type, sensor.value);
                    report_ids.push(report_id);
                },
                Err(e) => {
                    error!("Sensor {} failed to report: {}", sensor.id, e);
                }
            }
            
            // Stagger sensor reports
            std::thread::sleep(std::time::Duration::from_millis(100));
        }
        
        Ok(report_ids)
    }
}

pub fn demo_disaster_reporting() -> Result<(), Box<dyn Error>> {
    let reporting_service = DisasterReportingService::new("127.0.0.1:4112");
    
    println!("🚨 Disaster Reporting Demo");
    println!("==========================");
    
    // Example 1: Earthquake report
    println!("📱 Reporting earthquake...");
    let earthquake_id = reporting_service.report_earthquake(
        7, 
        Some((35.6812, 139.7671)), 
        "Strong shaking detected by seismograph network"
    )?;
    println!("   Report ID: {}", earthquake_id);
    
    // Example 2: Sensor network simulation
    println!("\n🌡️  Simulating sensor network...");
    let mut sensor_network = SensorNetwork::new("127.0.0.1:4112");
    
    // Add sensors across Tokyo
    sensor_network.add_sensor("TEMP_001".to_string(), (35.6812, 139.7671), "temperature".to_string());
    sensor_network.add_sensor("HUM_001".to_string(), (35.6812, 139.7671), "humidity".to_string());
    sensor_network.add_sensor("WIND_001".to_string(), (35.6950, 139.7514), "wind_speed".to_string());
    sensor_network.add_sensor("PRES_001".to_string(), (35.6586, 139.7454), "pressure".to_string());
    
    let report_ids = sensor_network.simulate_sensor_readings()?;
    println!("   Generated {} sensor reports", report_ids.len());
    
    // Example 3: Emergency situation
    println!("\n🔥 Emergency situation report...");
    let emergency_id = reporting_service.emergency_report(
        "fire",
        8,
        (35.6681, 139.7506),
        "Large fire detected in commercial district. Multiple buildings affected."
    )?;
    println!("   Emergency Report ID: {}", emergency_id);
    
    Ok(())
}
```

## Error Handling

Create comprehensive error handling patterns:

```rust
use wip_rust::wip_common_rs::clients::weather_client::WeatherClient;
use wip_rust::wip_common_rs::packet::core::WipPacketError;
use std::error::Error;
use std::time::Duration;
use log::{info, warn, error};

pub struct RobustWeatherClient {
    client: WeatherClient,
    max_retries: u32,
    base_delay: Duration,
}

impl RobustWeatherClient {
    pub fn new(server_address: &str) -> Self {
        let client = WeatherClient::new(server_address);
        client.set_timeout(Duration::from_secs(10));
        
        Self {
            client,
            max_retries: 3,
            base_delay: Duration::from_millis(100),
        }
    }
    
    pub fn get_weather_with_retry(&self, lat: f64, lng: f64) -> Result<std::collections::HashMap<String, u128>, Box<dyn Error>> {
        let mut last_error = None;
        
        for attempt in 1..=self.max_retries {
            info!("Weather request attempt {} of {}", attempt, self.max_retries);
            
            match self.client.get_weather_by_coordinates(lat, lng, true, true, true, false, false, 0) {
                Ok(weather) => {
                    info!("Weather request successful on attempt {}", attempt);
                    return Ok(weather);
                },
                Err(e) => {
                    last_error = Some(e);
                    warn!("Attempt {} failed: {}", attempt, last_error.as_ref().unwrap());
                    
                    if attempt < self.max_retries {
                        let delay = self.base_delay * (attempt * 2); // Exponential backoff
                        info!("Waiting {:?} before retry...", delay);
                        std::thread::sleep(delay);
                    }
                }
            }
        }
        
        Err(format!("All {} attempts failed. Last error: {}", 
            self.max_retries, 
            last_error.unwrap()).into())
    }
    
    pub fn categorize_error(&self, error: &dyn Error) -> ErrorCategory {
        if let Some(wip_error) = error.downcast_ref::<WipPacketError>() {
            match wip_error {
                WipPacketError::NetworkError(_) => ErrorCategory::Network,
                WipPacketError::TimeoutError => ErrorCategory::Timeout,
                WipPacketError::ChecksumError => ErrorCategory::DataCorruption,
                WipPacketError::InvalidResponse(_) => ErrorCategory::ServerError,
                _ => ErrorCategory::Unknown,
            }
        } else {
            ErrorCategory::Unknown
        }
    }
    
    pub fn handle_error_appropriately(&self, error: &dyn Error) -> ErrorAction {
        match self.categorize_error(error) {
            ErrorCategory::Network => ErrorAction::Retry,
            ErrorCategory::Timeout => ErrorAction::RetryWithLongerTimeout,
            ErrorCategory::DataCorruption => ErrorAction::Retry,
            ErrorCategory::ServerError => ErrorAction::ReportAndFail,
            ErrorCategory::Unknown => ErrorAction::Fail,
        }
    }
}

#[derive(Debug, PartialEq)]
pub enum ErrorCategory {
    Network,
    Timeout,
    DataCorruption,
    ServerError,
    Unknown,
}

#[derive(Debug, PartialEq)]
pub enum ErrorAction {
    Retry,
    RetryWithLongerTimeout,
    ReportAndFail,
    Fail,
}

pub fn demo_error_handling() -> Result<(), Box<dyn Error>> {
    println!("🔧 Error Handling Demo");
    println!("======================");
    
    let robust_client = RobustWeatherClient::new("127.0.0.1:4110");
    
    // Test with valid coordinates
    println!("Testing with valid coordinates...");
    match robust_client.get_weather_with_retry(35.6812, 139.7671) {
        Ok(weather) => {
            println!("✅ Success: Weather data received");
            if let Some(temp) = weather.get("temperature") {
                println!("   Temperature: {}°C", temp);
            }
        },
        Err(e) => {
            println!("❌ Failed after all retries: {}", e);
            let category = robust_client.categorize_error(e.as_ref());
            let action = robust_client.handle_error_appropriately(e.as_ref());
            println!("   Error category: {:?}", category);
            println!("   Recommended action: {:?}", action);
        }
    }
    
    // Test with invalid server (will fail)
    println!("\nTesting with unreachable server...");
    let failing_client = RobustWeatherClient::new("127.0.0.1:9999"); // Non-existent server
    
    match failing_client.get_weather_with_retry(35.6812, 139.7671) {
        Ok(_) => {
            println!("✅ Unexpected success");
        },
        Err(e) => {
            println!("❌ Expected failure: {}", e);
            let category = failing_client.categorize_error(e.as_ref());
            println!("   Error category: {:?}", category);
        }
    }
    
    Ok(())
}
```

## Asynchronous Operations

Create `examples/async_example.rs`:

```rust
use wip_rust::wip_common_rs::clients::async_weather_client::AsyncWeatherClient;
use tokio;
use std::error::Error;
use std::time::Instant;

#[tokio::main]
async fn main() -> Result<(), Box<dyn Error>> {
    env_logger::init();
    
    demo_concurrent_requests().await?;
    demo_async_error_handling().await?;
    demo_batch_processing().await?;
    
    Ok(())
}

async fn demo_concurrent_requests() -> Result<(), Box<dyn Error>> {
    println!("🚀 Concurrent Requests Demo");
    println!("============================");
    
    let client = AsyncWeatherClient::new("127.0.0.1:4110").await?;
    
    // Define cities to query
    let cities = vec![
        (35.6812, 139.7671, "Tokyo"),
        (34.6937, 135.5023, "Osaka"),
        (43.0642, 141.3469, "Sapporo"),
        (33.5904, 130.4017, "Fukuoka"),
        (35.0116, 135.7681, "Kyoto"),
        (35.1815, 136.9066, "Nagoya"),
    ];
    
    let start = Instant::now();
    
    // Create concurrent tasks
    let tasks: Vec<_> = cities
        .into_iter()
        .map(|(lat, lng, city)| {
            let client = client.clone();
            tokio::spawn(async move {
                let result = client.get_weather_by_coordinates_async(
                    lat, lng, true, true, false, false, false, 0
                ).await;
                (city, result)
            })
        })
        .collect();
    
    // Wait for all tasks to complete
    for task in tasks {
        let (city, result) = task.await?;
        match result {
            Ok(weather) => {
                println!("✅ {}: Weather data received", city);
                if let Some(temp) = weather.get("temperature") {
                    println!("   Temperature: {}°C", temp);
                }
            },
            Err(e) => {
                println!("❌ {}: Request failed - {}", city, e);
            }
        }
    }
    
    let elapsed = start.elapsed();
    println!("⏱️  Total time: {:?}", elapsed);
    
    Ok(())
}

async fn demo_async_error_handling() -> Result<(), Box<dyn Error>> {
    println!("\n🔧 Async Error Handling Demo");
    println!("=============================");
    
    // This will likely fail if no server is running
    let client = AsyncWeatherClient::new("127.0.0.1:4110").await?;
    
    // Use timeout for unreliable connections
    let weather_request = client.get_weather_by_coordinates_async(
        35.6812, 139.7671, true, true, false, false, false, 0
    );
    
    match tokio::time::timeout(std::time::Duration::from_secs(5), weather_request).await {
        Ok(Ok(weather)) => {
            println!("✅ Weather request completed successfully");
        },
        Ok(Err(e)) => {
            println!("❌ Weather request failed: {}", e);
        },
        Err(_) => {
            println!("⏰ Weather request timed out");
        }
    }
    
    Ok(())
}

async fn demo_batch_processing() -> Result<(), Box<dyn Error>> {
    println!("\n📦 Batch Processing Demo");
    println!("=========================");
    
    let client = AsyncWeatherClient::new("127.0.0.1:4110").await?;
    
    // Generate many coordinates
    let coordinates: Vec<(f64, f64)> = (0..20)
        .map(|i| {
            let lat = 35.0 + (i as f64 * 0.05);
            let lng = 139.0 + (i as f64 * 0.05);
            (lat, lng)
        })
        .collect();
    
    let batch_size = 5;
    let mut all_results = Vec::new();
    
    // Process in batches to avoid overwhelming the server
    for batch in coordinates.chunks(batch_size) {
        println!("Processing batch of {} coordinates...", batch.len());
        
        let batch_tasks: Vec<_> = batch
            .iter()
            .map(|&(lat, lng)| {
                let client = client.clone();
                tokio::spawn(async move {
                    client.get_weather_by_coordinates_async(
                        lat, lng, true, false, false, false, false, 0
                    ).await
                })
            })
            .collect();
        
        // Wait for batch to complete
        for task in batch_tasks {
            match task.await? {
                Ok(weather) => all_results.push(weather),
                Err(e) => println!("   Batch item failed: {}", e),
            }
        }
        
        // Brief pause between batches
        tokio::time::sleep(std::time::Duration::from_millis(200)).await;
    }
    
    println!("✅ Batch processing completed: {}/{} successful", 
        all_results.len(), coordinates.len());
    
    Ok(())
}
```

## Testing with Mock Servers

Create comprehensive testing examples:

```rust
#[cfg(test)]
mod tests {
    use super::*;
    use wip_rust::tests::common::mock_server::{MockServerCluster, MockServerBuilder};
    use wip_rust::wip_common_rs::clients::weather_client::WeatherClient;
    use std::time::Duration;
    
    #[test]
    fn test_with_mock_server_cluster() {
        let mut cluster = MockServerCluster::new().unwrap();
        cluster.start_all();
        
        let (weather_port, location_port, query_port, report_port) = cluster.ports();
        
        // Give servers time to start
        std::thread::sleep(Duration::from_millis(100));
        
        // Test weather client
        let weather_client = WeatherClient::new(&format!("127.0.0.1:{}", weather_port));
        let weather_result = weather_client.get_weather_by_coordinates(
            35.6812, 139.7671, true, true, false, false, false, 0
        );
        assert!(weather_result.is_ok());
        
        // Test location client
        let location_client = LocationClient::new(&format!("127.0.0.1:{}", location_port));
        let location_result = location_client.resolve_coordinates(35.6812, 139.7671);
        assert!(location_result.is_ok());
        
        cluster.stop_all();
    }
    
    #[test]
    fn test_error_simulation() {
        // Create a server that always returns errors
        let server = MockServerBuilder::new()
            .error_rate(1.0) // 100% error rate
            .build()
            .unwrap();
        
        let port = server.port();
        let handle = server.start();
        
        std::thread::sleep(Duration::from_millis(100));
        
        let client = WeatherClient::new(&format!("127.0.0.1:{}", port));
        let result = client.get_weather_by_coordinates(
            35.6812, 139.7671, true, false, false, false, false, 0
        );
        
        // Should receive an error
        assert!(result.is_err());
        
        server.stop();
    }
    
    #[test]
    fn test_performance_with_mock() {
        let server = MockServerBuilder::new()
            .response_delay(Duration::from_millis(10))
            .build()
            .unwrap();
        
        let port = server.port();
        let handle = server.start();
        
        std::thread::sleep(Duration::from_millis(100));
        
        let client = WeatherClient::new(&format!("127.0.0.1:{}", port));
        let start = std::time::Instant::now();
        
        let mut successful_requests = 0;
        for i in 0..10 {
            let lat = 35.0 + (i as f64 * 0.01);
            let lng = 139.0 + (i as f64 * 0.01);
            
            if client.get_weather_by_coordinates(lat, lng, true, false, false, false, false, 0).is_ok() {
                successful_requests += 1;
            }
        }
        
        let elapsed = start.elapsed();
        println!("Completed {} requests in {:?}", successful_requests, elapsed);
        
        assert!(successful_requests >= 8); // At least 80% success rate
        assert!(elapsed < Duration::from_secs(5)); // Should complete quickly
        
        server.stop();
    }
}
```

## Production Best Practices

### Configuration Management

Create `src/config.rs`:

```rust
use std::env;
use std::time::Duration;

#[derive(Debug, Clone)]
pub struct WipConfig {
    pub weather_server_url: String,
    pub location_server_url: String,
    pub query_server_url: String,
    pub report_server_url: String,
    pub timeout: Duration,
    pub retry_count: u32,
    pub connection_pool_size: usize,
    pub debug_mode: bool,
}

impl WipConfig {
    pub fn from_env() -> Self {
        Self {
            weather_server_url: env::var("WIP_WEATHER_SERVER")
                .unwrap_or_else(|_| "127.0.0.1:4110".to_string()),
            location_server_url: env::var("WIP_LOCATION_SERVER")
                .unwrap_or_else(|_| "127.0.0.1:4109".to_string()),
            query_server_url: env::var("WIP_QUERY_SERVER")
                .unwrap_or_else(|_| "127.0.0.1:4111".to_string()),
            report_server_url: env::var("WIP_REPORT_SERVER")
                .unwrap_or_else(|_| "127.0.0.1:4112".to_string()),
            timeout: Duration::from_secs(
                env::var("WIP_TIMEOUT_SECONDS")
                    .unwrap_or_else(|_| "30".to_string())
                    .parse()
                    .unwrap_or(30)
            ),
            retry_count: env::var("WIP_RETRY_COUNT")
                .unwrap_or_else(|_| "3".to_string())
                .parse()
                .unwrap_or(3),
            connection_pool_size: env::var("WIP_POOL_SIZE")
                .unwrap_or_else(|_| "10".to_string())
                .parse()
                .unwrap_or(10),
            debug_mode: env::var("WIP_DEBUG").is_ok(),
        }
    }
    
    pub fn production() -> Self {
        Self {
            weather_server_url: "production-weather-server:4110".to_string(),
            location_server_url: "production-location-server:4109".to_string(),
            query_server_url: "production-query-server:4111".to_string(),
            report_server_url: "production-report-server:4112".to_string(),
            timeout: Duration::from_secs(30),
            retry_count: 5,
            connection_pool_size: 50,
            debug_mode: false,
        }
    }
}
```

### Health Monitoring

```rust
use std::sync::atomic::{AtomicU64, Ordering};
use std::sync::Arc;
use std::time::{Duration, Instant};

pub struct HealthMonitor {
    total_requests: AtomicU64,
    successful_requests: AtomicU64,
    failed_requests: AtomicU64,
    last_request_time: Arc<std::sync::Mutex<Option<Instant>>>,
}

impl HealthMonitor {
    pub fn new() -> Self {
        Self {
            total_requests: AtomicU64::new(0),
            successful_requests: AtomicU64::new(0),
            failed_requests: AtomicU64::new(0),
            last_request_time: Arc::new(std::sync::Mutex::new(None)),
        }
    }
    
    pub fn record_request(&self, success: bool) {
        self.total_requests.fetch_add(1, Ordering::Relaxed);
        
        if success {
            self.successful_requests.fetch_add(1, Ordering::Relaxed);
        } else {
            self.failed_requests.fetch_add(1, Ordering::Relaxed);
        }
        
        *self.last_request_time.lock().unwrap() = Some(Instant::now());
    }
    
    pub fn get_stats(&self) -> HealthStats {
        let total = self.total_requests.load(Ordering::Relaxed);
        let successful = self.successful_requests.load(Ordering::Relaxed);
        let failed = self.failed_requests.load(Ordering::Relaxed);
        
        HealthStats {
            total_requests: total,
            successful_requests: successful,
            failed_requests: failed,
            success_rate: if total > 0 { successful as f64 / total as f64 } else { 0.0 },
            last_request_time: *self.last_request_time.lock().unwrap(),
        }
    }
    
    pub fn is_healthy(&self) -> bool {
        let stats = self.get_stats();
        
        // Consider healthy if:
        // 1. Success rate > 90%
        // 2. Recent activity (within last 5 minutes)
        stats.success_rate > 0.9 && 
        stats.last_request_time
            .map(|time| time.elapsed() < Duration::from_secs(300))
            .unwrap_or(false)
    }
}

#[derive(Debug)]
pub struct HealthStats {
    pub total_requests: u64,
    pub successful_requests: u64,
    pub failed_requests: u64,
    pub success_rate: f64,
    pub last_request_time: Option<Instant>,
}
```

## Performance Optimization

### Connection Pooling

```rust
pub struct OptimizedWeatherService {
    client: WeatherClient,
    health_monitor: HealthMonitor,
}

impl OptimizedWeatherService {
    pub fn new(config: &WipConfig) -> Self {
        let client = WeatherClient::new(&config.weather_server_url);
        
        // Apply optimizations
        client.set_timeout(config.timeout);
        client.set_connection_pool_size(config.connection_pool_size);
        client.set_retry_count(config.retry_count);
        
        if config.debug_mode {
            client.set_debug_mode(true);
        }
        
        Self {
            client,
            health_monitor: HealthMonitor::new(),
        }
    }
    
    pub fn get_weather_optimized(&self, lat: f64, lng: f64) -> Result<WeatherData, Box<dyn Error>> {
        let start = Instant::now();
        
        let result = self.client.get_weather_by_coordinates(
            lat, lng, true, true, true, false, false, 0
        );
        
        match &result {
            Ok(_) => {
                self.health_monitor.record_request(true);
                log::info!("Weather request completed in {:?}", start.elapsed());
            },
            Err(e) => {
                self.health_monitor.record_request(false);
                log::error!("Weather request failed after {:?}: {}", start.elapsed(), e);
            }
        }
        
        result.map(|weather| WeatherData {
            // Convert to your data structure
            // ... 
        })
    }
    
    pub fn get_health_stats(&self) -> HealthStats {
        self.health_monitor.get_stats()
    }
}
```

This comprehensive tutorial provides a solid foundation for using the WIP Rust implementation in production applications. Each section builds upon the previous ones, giving you both basic usage patterns and advanced techniques for robust, high-performance weather data applications.