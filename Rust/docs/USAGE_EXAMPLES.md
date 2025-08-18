# WIP Rust Implementation - Usage Examples

This document provides comprehensive usage examples for the WIP (Weather Transfer Protocol) Rust implementation.

## Table of Contents

1. [Basic Client Usage](#basic-client-usage)
2. [Weather Data Retrieval](#weather-data-retrieval)
3. [Location Resolution](#location-resolution)
4. [Disaster Reporting](#disaster-reporting)
5. [Advanced Features](#advanced-features)
6. [Error Handling](#error-handling)
7. [Performance Optimization](#performance-optimization)
8. [Testing Examples](#testing-examples)

## Basic Client Usage

### Creating a Weather Client

```rust
use wip_rust::wip_common_rs::clients::weather_client::WeatherClient;

// Create a client connected to localhost
let client = WeatherClient::new("127.0.0.1:4110");

// Set custom timeout
client.set_timeout(Duration::from_secs(10));

// Set retry configuration
client.set_retry_count(3);
```

### Simple Weather Request

```rust
use wip_rust::wip_common_rs::clients::weather_client::WeatherClient;

fn get_tokyo_weather() -> Result<(), Box<dyn std::error::Error>> {
    let client = WeatherClient::new("127.0.0.1:4110");
    
    // Tokyo coordinates
    let result = client.get_weather_by_coordinates(
        35.6812,  // latitude
        139.7671, // longitude
        true,     // weather data
        true,     // temperature
        true,     // precipitation probability
        false,    // alerts
        false,    // disaster info
        0         // today (0), tomorrow (1), etc.
    )?;
    
    println!("Area Code: {}", result.get("area_code").unwrap_or(&0));
    println!("Weather Code: {}", result.get("weather_code").unwrap_or(&0));
    println!("Temperature: {}°C", result.get("temperature").unwrap_or(&0));
    
    Ok(())
}
```

## Weather Data Retrieval

### Getting Weather for Multiple Cities

```rust
use wip_rust::wip_common_rs::clients::weather_client::WeatherClient;

fn get_multi_city_weather() -> Result<(), Box<dyn std::error::Error>> {
    let client = WeatherClient::new("127.0.0.1:4110");
    
    let cities = vec![
        (35.6812, 139.7671, "Tokyo"),
        (34.6937, 135.5023, "Osaka"),
        (43.0642, 141.3469, "Sapporo"),
        (33.5904, 130.4017, "Fukuoka"),
    ];
    
    for (lat, lng, city) in cities {
        match client.get_weather_by_coordinates(lat, lng, true, true, true, false, false, 0) {
            Ok(weather) => {
                println!("{}: Weather Code {}, Temp {}°C", 
                    city,
                    weather.get("weather_code").unwrap_or(&0),
                    weather.get("temperature").unwrap_or(&0)
                );
            },
            Err(e) => {
                println!("{}: Failed to get weather: {}", city, e);
            }
        }
        
        // Rate limiting
        std::thread::sleep(Duration::from_millis(100));
    }
    
    Ok(())
}
```

### Weather with Alerts and Disaster Information

```rust
use wip_rust::wip_common_rs::clients::weather_client::WeatherClient;

fn get_weather_with_alerts() -> Result<(), Box<dyn std::error::Error>> {
    let client = WeatherClient::new("127.0.0.1:4110");
    
    let result = client.get_weather_by_coordinates(
        35.6812, 139.7671, 
        true,  // weather
        true,  // temperature
        true,  // precipitation
        true,  // alerts
        true,  // disaster info
        0      // today
    )?;
    
    // Check for alerts
    if let Some(alerts) = result.get("alerts") {
        if *alerts > 0 {
            println!("⚠️ Weather alerts active in this area");
        }
    }
    
    // Check for disaster information
    if let Some(disaster) = result.get("disaster") {
        if *disaster > 0 {
            println!("🚨 Disaster information available");
        }
    }
    
    Ok(())
}
```

## Location Resolution

### Coordinate to Area Code Conversion

```rust
use wip_rust::wip_common_rs::clients::location_client::LocationClient;

fn resolve_coordinates() -> Result<(), Box<dyn std::error::Error>> {
    let client = LocationClient::new("127.0.0.1:4109");
    
    let area_code = client.resolve_coordinates(35.6812, 139.7671)?;
    println!("Tokyo area code: {}", area_code);
    
    // Batch resolution
    let coordinates = vec![
        (35.6812, 139.7671), // Tokyo
        (34.6937, 135.5023), // Osaka
        (43.0642, 141.3469), // Sapporo
    ];
    
    for (lat, lng) in coordinates {
        match client.resolve_coordinates(lat, lng) {
            Ok(code) => println!("({:.4}, {:.4}) -> Area Code: {}", lat, lng, code),
            Err(e) => println!("Failed to resolve ({:.4}, {:.4}): {}", lat, lng, e),
        }
    }
    
    Ok(())
}
```

### Area Code Validation

```rust
use wip_rust::wip_common_rs::clients::location_client::LocationClient;

fn validate_area_codes() -> Result<(), Box<dyn std::error::Error>> {
    let client = LocationClient::new("127.0.0.1:4109");
    
    let test_coordinates = vec![
        (35.6812, 139.7671, "Tokyo"),
        (34.6937, 135.5023, "Osaka"),
        (90.0, 0.0, "North Pole"),      // Edge case
        (0.0, 0.0, "Null Island"),      // Edge case
    ];
    
    for (lat, lng, name) in test_coordinates {
        println!("Testing {}: ({:.4}, {:.4})", name, lat, lng);
        
        match client.resolve_coordinates(lat, lng) {
            Ok(area_code) => {
                // Validate area code range (JMA codes are 6 digits)
                if area_code >= 100000 && area_code <= 999999 {
                    println!("  ✓ Valid area code: {}", area_code);
                } else {
                    println!("  ⚠️ Unusual area code: {}", area_code);
                }
            },
            Err(e) => {
                println!("  ✗ Resolution failed: {}", e);
            }
        }
    }
    
    Ok(())
}
```

## Disaster Reporting

### Basic Sensor Report

```rust
use wip_rust::wip_common_rs::clients::report_client::ReportClient;

fn send_sensor_report() -> Result<(), Box<dyn std::error::Error>> {
    let client = ReportClient::new("127.0.0.1:4112");
    
    let report_id = client.send_sensor_report(
        "earthquake",                           // disaster type
        7,                                      // severity (1-10)
        "Strong earthquake detected by sensor", // description
        Some(35.6812),                         // latitude
        Some(139.7671)                         // longitude
    )?;
    
    println!("Report submitted successfully, ID: {}", report_id);
    Ok(())
}
```

### Batch Sensor Reports

```rust
use wip_rust::wip_common_rs::clients::report_client::ReportClient;

fn send_batch_reports() -> Result<(), Box<dyn std::error::Error>> {
    let client = ReportClient::new("127.0.0.1:4112");
    
    let reports = vec![
        ("temperature", 1, "Normal temperature reading", 35.6812, 139.7671),
        ("humidity", 2, "High humidity detected", 35.6813, 139.7672),
        ("seismic", 3, "Minor seismic activity", 35.6814, 139.7673),
        ("wind", 4, "Strong wind conditions", 35.6815, 139.7674),
    ];
    
    let mut successful_reports = Vec::new();
    
    for (disaster_type, severity, description, lat, lng) in reports {
        match client.send_sensor_report(disaster_type, severity, description, Some(lat), Some(lng)) {
            Ok(report_id) => {
                successful_reports.push(report_id);
                println!("Report {}: {} (ID: {})", disaster_type, description, report_id);
            },
            Err(e) => {
                println!("Failed to send {} report: {}", disaster_type, e);
            }
        }
        
        // Avoid overwhelming the server
        std::thread::sleep(Duration::from_millis(100));
    }
    
    println!("Successfully submitted {} reports", successful_reports.len());
    Ok(())
}
```

### Emergency Response Scenario

```rust
use wip_rust::wip_common_rs::clients::{
    weather_client::WeatherClient,
    location_client::LocationClient,
    report_client::ReportClient,
};

fn emergency_response() -> Result<(), Box<dyn std::error::Error>> {
    // Emergency location
    let emergency_lat = 35.6812;
    let emergency_lng = 139.7671;
    
    // Step 1: Report the emergency
    let report_client = ReportClient::new("127.0.0.1:4112");
    let report_id = report_client.send_sensor_report(
        "earthquake",
        8,
        "Major earthquake - immediate response required",
        Some(emergency_lat),
        Some(emergency_lng)
    )?;
    println!("Emergency reported, ID: {}", report_id);
    
    // Step 2: Get current weather conditions for response planning
    let weather_client = WeatherClient::new("127.0.0.1:4110");
    let weather = weather_client.get_weather_by_coordinates(
        emergency_lat, emergency_lng,
        true, true, true, true, true, 0
    )?;
    
    println!("Weather conditions at emergency site:");
    println!("  Weather Code: {}", weather.get("weather_code").unwrap_or(&0));
    println!("  Temperature: {}°C", weather.get("temperature").unwrap_or(&0));
    
    // Step 3: Resolve area code for coordination
    let location_client = LocationClient::new("127.0.0.1:4109");
    let area_code = location_client.resolve_coordinates(emergency_lat, emergency_lng)?;
    println!("Area code for coordination: {}", area_code);
    
    Ok(())
}
```

## Advanced Features

### Asynchronous Operations

```rust
use wip_rust::wip_common_rs::clients::async_weather_client::AsyncWeatherClient;
use tokio;

#[tokio::main]
async fn async_weather_requests() -> Result<(), Box<dyn std::error::Error>> {
    let client = AsyncWeatherClient::new("127.0.0.1:4110").await?;
    
    // Concurrent requests
    let tokyo_task = client.get_weather_by_coordinates_async(35.6812, 139.7671, true, true, false, false, false, 0);
    let osaka_task = client.get_weather_by_coordinates_async(34.6937, 135.5023, true, true, false, false, false, 0);
    let sapporo_task = client.get_weather_by_coordinates_async(43.0642, 141.3469, true, true, false, false, false, 0);
    
    // Wait for all requests to complete
    let (tokyo_result, osaka_result, sapporo_result) = tokio::try_join!(
        tokyo_task,
        osaka_task,
        sapporo_task
    )?;
    
    println!("Tokyo: {:?}", tokyo_result);
    println!("Osaka: {:?}", osaka_result);
    println!("Sapporo: {:?}", sapporo_result);
    
    Ok(())
}
```

### Connection Pooling

```rust
use wip_rust::wip_common_rs::clients::weather_client::WeatherClient;
use std::sync::Arc;
use std::thread;

fn connection_pooling_example() -> Result<(), Box<dyn std::error::Error>> {
    let client = Arc::new(WeatherClient::new("127.0.0.1:4110"));
    
    // Configure connection pool
    client.set_connection_pool_size(10);
    client.set_connection_timeout(Duration::from_secs(5));
    
    let mut handles = Vec::new();
    
    // Spawn multiple threads using the same client
    for i in 0..5 {
        let client_clone = Arc::clone(&client);
        
        let handle = thread::spawn(move || {
            for j in 0..10 {
                let lat = 35.0 + (i as f64 * 0.1) + (j as f64 * 0.01);
                let lng = 139.0 + (i as f64 * 0.1) + (j as f64 * 0.01);
                
                match client_clone.get_weather_by_coordinates(lat, lng, true, false, false, false, false, 0) {
                    Ok(_) => println!("Thread {}: Request {} succeeded", i, j),
                    Err(e) => println!("Thread {}: Request {} failed: {}", i, j, e),
                }
            }
        });
        
        handles.push(handle);
    }
    
    // Wait for all threads to complete
    for handle in handles {
        handle.join().unwrap();
    }
    
    Ok(())
}
```

## Error Handling

### Comprehensive Error Handling

```rust
use wip_rust::wip_common_rs::clients::weather_client::WeatherClient;
use wip_rust::wip_common_rs::packet::core::WipPacketError;

fn robust_weather_request() -> Result<(), Box<dyn std::error::Error>> {
    let client = WeatherClient::new("127.0.0.1:4110");
    
    match client.get_weather_by_coordinates(35.6812, 139.7671, true, true, false, false, false, 0) {
        Ok(weather_data) => {
            println!("Weather data received successfully");
            // Process weather data
        },
        Err(e) => {
            match e.downcast_ref::<WipPacketError>() {
                Some(WipPacketError::NetworkError(msg)) => {
                    println!("Network error: {}. Retrying...", msg);
                    // Implement retry logic
                },
                Some(WipPacketError::TimeoutError) => {
                    println!("Request timed out. Check server status.");
                },
                Some(WipPacketError::ChecksumError) => {
                    println!("Data corruption detected. Retrying...");
                },
                Some(WipPacketError::InvalidResponse(msg)) => {
                    println!("Invalid response from server: {}", msg);
                },
                _ => {
                    println!("Unknown error: {}", e);
                }
            }
        }
    }
    
    Ok(())
}
```

### Retry Logic with Exponential Backoff

```rust
use wip_rust::wip_common_rs::clients::weather_client::WeatherClient;
use std::time::Duration;
use std::thread;

fn weather_request_with_retry() -> Result<(), Box<dyn std::error::Error>> {
    let client = WeatherClient::new("127.0.0.1:4110");
    let max_retries = 3;
    let mut retry_delay = Duration::from_millis(100);
    
    for attempt in 0..max_retries {
        match client.get_weather_by_coordinates(35.6812, 139.7671, true, true, false, false, false, 0) {
            Ok(weather_data) => {
                println!("Weather data received on attempt {}", attempt + 1);
                return Ok(());
            },
            Err(e) => {
                println!("Attempt {} failed: {}", attempt + 1, e);
                
                if attempt < max_retries - 1 {
                    println!("Retrying in {:?}...", retry_delay);
                    thread::sleep(retry_delay);
                    retry_delay *= 2; // Exponential backoff
                }
            }
        }
    }
    
    Err("All retry attempts failed".into())
}
```

## Performance Optimization

### Batch Processing

```rust
use wip_rust::wip_common_rs::clients::weather_client::WeatherClient;
use std::sync::{Arc, Mutex};
use std::thread;

fn batch_weather_processing() -> Result<(), Box<dyn std::error::Error>> {
    let client = Arc::new(WeatherClient::new("127.0.0.1:4110"));
    let results = Arc::new(Mutex::new(Vec::new()));
    
    // Coordinates for processing
    let coordinates = vec![
        (35.6812, 139.7671), // Tokyo
        (34.6937, 135.5023), // Osaka
        (43.0642, 141.3469), // Sapporo
        (33.5904, 130.4017), // Fukuoka
        (35.0116, 135.7681), // Kyoto
        (35.1815, 136.9066), // Nagoya
    ];
    
    let batch_size = 2;
    let mut handles = Vec::new();
    
    // Process in batches
    for batch in coordinates.chunks(batch_size) {
        let client_clone = Arc::clone(&client);
        let results_clone = Arc::clone(&results);
        let batch_coords = batch.to_vec();
        
        let handle = thread::spawn(move || {
            for (lat, lng) in batch_coords {
                match client_clone.get_weather_by_coordinates(lat, lng, true, true, false, false, false, 0) {
                    Ok(weather) => {
                        let mut results = results_clone.lock().unwrap();
                        results.push((lat, lng, weather));
                    },
                    Err(e) => {
                        println!("Failed to get weather for ({}, {}): {}", lat, lng, e);
                    }
                }
                
                // Rate limiting within batch
                thread::sleep(Duration::from_millis(50));
            }
        });
        
        handles.push(handle);
    }
    
    // Wait for all batches to complete
    for handle in handles {
        handle.join().unwrap();
    }
    
    let results = results.lock().unwrap();
    println!("Processed {} locations successfully", results.len());
    
    Ok(())
}
```

## Testing Examples

### Unit Testing with Mock Data

```rust
#[cfg(test)]
mod tests {
    use super::*;
    use wip_rust::wip_common_rs::packet::types::location_packet::LocationRequest;
    
    #[test]
    fn test_packet_creation() {
        let mut request = LocationRequest::new();
        request.set_latitude(35.6812);
        request.set_longitude(139.7671);
        
        assert_eq!(request.get_latitude(), 35.6812);
        assert_eq!(request.get_longitude(), 139.7671);
        
        let bytes = request.to_bytes();
        assert!(!bytes.is_empty());
    }
    
    #[test]
    fn test_checksum_validation() {
        use wip_rust::wip_common_rs::packet::core::checksum::{calc_checksum12, verify_checksum12};
        
        let test_data = vec![0x12, 0x34, 0x56, 0x78, 0x00, 0x00];
        let checksum = calc_checksum12(&test_data[..4]);
        
        assert!(checksum <= 0xFFF);
        
        let mut data_with_checksum = test_data;
        data_with_checksum[4] = (checksum & 0xFF) as u8;
        data_with_checksum[5] = ((checksum >> 8) & 0xFF) as u8;
        
        assert!(verify_checksum12(&data_with_checksum, 0, 4).unwrap());
    }
}
```

### Integration Testing

```rust
#[cfg(test)]
mod integration_tests {
    use super::*;
    use wip_rust::wip_common_rs::clients::weather_client::WeatherClient;
    
    #[test]
    #[ignore] // Run with: cargo test -- --ignored
    fn test_real_server_integration() {
        let client = WeatherClient::new("127.0.0.1:4110");
        
        // This test requires a running server
        match client.get_weather_by_coordinates(35.6812, 139.7671, true, false, false, false, false, 0) {
            Ok(weather) => {
                assert!(weather.contains_key("area_code"));
                println!("Integration test passed: {:?}", weather);
            },
            Err(e) => {
                println!("Integration test failed (server may not be running): {}", e);
            }
        }
    }
}
```

### Performance Testing

```rust
#[cfg(test)]
mod performance_tests {
    use super::*;
    use std::time::Instant;
    
    #[test]
    fn test_packet_serialization_performance() {
        use wip_rust::wip_common_rs::packet::types::location_packet::LocationRequest;
        
        let mut request = LocationRequest::new();
        request.set_latitude(35.6812);
        request.set_longitude(139.7671);
        
        let iterations = 10000;
        let start = Instant::now();
        
        for _ in 0..iterations {
            let _bytes = request.to_bytes();
        }
        
        let elapsed = start.elapsed();
        let per_operation = elapsed / iterations;
        
        println!("Serialization: {:?} per operation", per_operation);
        assert!(per_operation < Duration::from_micros(100));
    }
}
```

## Tips and Best Practices

1. **Connection Management**: Use connection pooling for high-throughput applications
2. **Error Handling**: Always implement proper error handling with retries
3. **Rate Limiting**: Avoid overwhelming servers with too many concurrent requests
4. **Caching**: Cache area code resolutions to reduce server load
5. **Timeouts**: Set appropriate timeouts based on your application's needs
6. **Monitoring**: Log important operations for debugging and monitoring
7. **Testing**: Use mock servers for unit testing, real servers for integration testing

## Configuration Examples

### Client Configuration

```rust
use wip_rust::wip_common_rs::clients::weather_client::WeatherClient;

fn configure_client() -> WeatherClient {
    let client = WeatherClient::new("127.0.0.1:4110");
    
    // Timeout configuration
    client.set_timeout(Duration::from_secs(10));
    client.set_connection_timeout(Duration::from_secs(5));
    
    // Retry configuration
    client.set_retry_count(3);
    client.set_retry_delay(Duration::from_millis(100));
    
    // Connection pool configuration
    client.set_connection_pool_size(10);
    client.set_max_idle_connections(5);
    
    // Enable debug logging
    client.set_debug_mode(true);
    
    client
}
```

This documentation provides comprehensive examples for using the WIP Rust implementation effectively. For more advanced use cases, refer to the API documentation generated with `cargo doc`.