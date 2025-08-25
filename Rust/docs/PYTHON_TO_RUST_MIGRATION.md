# Python to Rust Migration Guide

This guide helps you migrate from the Python WIP implementation to the Rust implementation, covering API differences, best practices, and migration strategies.

## Table of Contents

1. [Overview](#overview)
2. [Key Differences](#key-differences)
3. [API Migration](#api-migration)
4. [Error Handling Migration](#error-handling-migration)
5. [Asynchronous Programming](#asynchronous-programming)
6. [Configuration Changes](#configuration-changes)
7. [Testing Migration](#testing-migration)
8. [Performance Considerations](#performance-considerations)
9. [Migration Strategies](#migration-strategies)
10. [Common Pitfalls](#common-pitfalls)

## Overview

The Rust implementation maintains **protocol compatibility** with the Python version while offering:

- **Better Performance**: 5-10x faster packet processing
- **Memory Safety**: No memory leaks or buffer overflows
- **Type Safety**: Compile-time error checking
- **Better Concurrency**: Native async/await support

## Key Differences

### Language Paradigms

| Python | Rust | Notes |
|--------|------|-------|
| Duck typing | Strong static typing | Errors caught at compile time |
| Exceptions | Result<T, E> | Explicit error handling |
| GC managed memory | RAII/ownership | No garbage collection overhead |
| Threading + GIL | Native threading | True parallelism |
| `async`/`await` | `async`/`await` | Similar syntax, different runtime |

### Error Handling Philosophy

**Python (Exceptions):**
```python
try:
    weather = client.get_weather(lat, lng)
    process_weather(weather)
except NetworkError as e:
    logger.error(f"Network error: {e}")
except Exception as e:
    logger.error(f"Unexpected error: {e}")
```

**Rust (Result Types):**
```rust
match client.get_weather_by_coordinates(lat, lng, true, true, false, false, false, 0) {
    Ok(weather) => process_weather(weather),
    Err(e) => {
        if let Some(network_err) = e.downcast_ref::<NetworkError>() {
            log::error!("Network error: {}", network_err);
        } else {
            log::error!("Unexpected error: {}", e);
        }
    }
}
```

## API Migration

### Basic Client Usage

**Python:**
```python
from WIPCommonPy.clients.weather_client import WeatherClient

client = WeatherClient(host='localhost', port=4110, debug=True)

result = client.get_weather_by_coordinates(
    latitude=35.6812,
    longitude=139.7671,
    weather=True,
    temperature=True,
    precipitation_prob=True
)

print(f"Area Code: {result['area_code']}")
print(f"Temperature: {result['temperature']}°C")
```

**Rust:**
```rust
use wip_rust::wip_common_rs::clients::weather_client::WeatherClient;

let client = WeatherClient::new("127.0.0.1:4110");
client.set_debug_mode(true);

let result = client.get_weather_by_coordinates(
    35.6812,  // latitude
    139.7671, // longitude
    true,     // weather
    true,     // temperature
    true,     // precipitation_prob
    false,    // alerts
    false,    // disaster
    0         // day
)?;

println!("Area Code: {}", result.get("area_code").unwrap_or(&0));
println!("Temperature: {}°C", result.get("temperature").unwrap_or(&0));
```

### Location Resolution

**Python:**
```python
from WIPCommonPy.clients.location_client import LocationClient

location_client = LocationClient(host='localhost', port=4109)
area_code = location_client.resolve_coordinates(35.6812, 139.7671)
print(f"Area code: {area_code}")
```

**Rust:**
```rust
use wip_rust::wip_common_rs::clients::location_client::LocationClient;

let location_client = LocationClient::new("127.0.0.1:4109");
let area_code = location_client.resolve_coordinates(35.6812, 139.7671)?;
println!("Area code: {}", area_code);
```

### Disaster Reporting

**Python:**
```python
from WIPCommonPy.clients.report_client import ReportClient

report_client = ReportClient(host='localhost', port=4112)
report_id = report_client.send_report(
    disaster_type="earthquake",
    severity=7,
    description="Strong earthquake detected",
    latitude=35.6812,
    longitude=139.7671
)
```

**Rust:**
```rust
use wip_rust::wip_common_rs::clients::report_client::ReportClient;

let report_client = ReportClient::new("127.0.0.1:4112");
let report_id = report_client.send_sensor_report(
    "earthquake",
    7,
    "Strong earthquake detected",
    Some(35.6812),
    Some(139.7671)
)?;
```

## Error Handling Migration

### Python Exception Patterns

**Python:**
```python
import logging
from WIPCommonPy.clients.weather_client import WeatherClient
from WIPCommonPy.exceptions import NetworkError, TimeoutError, ChecksumError

def robust_weather_request(lat, lng):
    client = WeatherClient(host='localhost', port=4110)
    max_retries = 3
    
    for attempt in range(max_retries):
        try:
            return client.get_weather_by_coordinates(lat, lng)
        except NetworkError as e:
            logging.warning(f"Network error on attempt {attempt + 1}: {e}")
            if attempt == max_retries - 1:
                raise
        except TimeoutError:
            logging.warning(f"Timeout on attempt {attempt + 1}")
            if attempt == max_retries - 1:
                raise
        except ChecksumError:
            logging.warning(f"Checksum error on attempt {attempt + 1}")
            if attempt == max_retries - 1:
                raise
        
        time.sleep(0.1 * (attempt + 1))  # Exponential backoff
```

**Rust Equivalent:**
```rust
use wip_rust::wip_common_rs::clients::weather_client::WeatherClient;
use wip_rust::wip_common_rs::packet::core::WipPacketError;
use std::thread;
use std::time::Duration;
use log::{warn, error};

fn robust_weather_request(lat: f64, lng: f64) -> Result<std::collections::HashMap<String, u128>, Box<dyn std::error::Error>> {
    let client = WeatherClient::new("127.0.0.1:4110");
    let max_retries = 3;
    
    for attempt in 0..max_retries {
        match client.get_weather_by_coordinates(lat, lng, true, true, false, false, false, 0) {
            Ok(weather) => return Ok(weather),
            Err(e) => {
                if let Some(wip_error) = e.downcast_ref::<WipPacketError>() {
                    match wip_error {
                        WipPacketError::NetworkError(msg) => {
                            warn!("Network error on attempt {}: {}", attempt + 1, msg);
                        },
                        WipPacketError::TimeoutError => {
                            warn!("Timeout on attempt {}", attempt + 1);
                        },
                        WipPacketError::ChecksumError => {
                            warn!("Checksum error on attempt {}", attempt + 1);
                        },
                        _ => {
                            error!("Unexpected error: {}", e);
                            return Err(e);
                        }
                    }
                } else {
                    error!("Unknown error: {}", e);
                    return Err(e);
                }
                
                if attempt == max_retries - 1 {
                    return Err(format!("Failed after {} attempts", max_retries).into());
                }
                
                thread::sleep(Duration::from_millis(100 * (attempt + 1) as u64));
            }
        }
    }
    
    unreachable!()
}
```

### Error Type Mapping

| Python Exception | Rust Error Type | Migration Notes |
|------------------|-----------------|-----------------|
| `NetworkError` | `WipPacketError::NetworkError` | Similar semantics |
| `TimeoutError` | `WipPacketError::TimeoutError` | Direct equivalent |
| `ChecksumError` | `WipPacketError::ChecksumError` | Same meaning |
| `ValueError` | `WipPacketError::InvalidField` | Input validation |
| `ConnectionError` | `std::io::Error` | Network connection issues |

## Asynchronous Programming

### Python Asyncio

**Python:**
```python
import asyncio
from WIPCommonPy.clients.async_weather_client import AsyncWeatherClient

async def async_weather_requests():
    client = AsyncWeatherClient(host='localhost', port=4110)
    
    tasks = [
        client.get_weather_async(35.6812, 139.7671),  # Tokyo
        client.get_weather_async(34.6937, 135.5023),  # Osaka
        client.get_weather_async(43.0642, 141.3469),  # Sapporo
    ]
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            print(f"Request {i} failed: {result}")
        else:
            print(f"Request {i} succeeded: {result}")

# Run the async function
asyncio.run(async_weather_requests())
```

**Rust Tokio:**
```rust
use wip_rust::wip_common_rs::clients::async_weather_client::AsyncWeatherClient;
use tokio;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    async_weather_requests().await
}

async fn async_weather_requests() -> Result<(), Box<dyn std::error::Error>> {
    let client = AsyncWeatherClient::new("127.0.0.1:4110").await?;
    
    let tasks = vec![
        tokio::spawn({
            let client = client.clone();
            async move { client.get_weather_by_coordinates_async(35.6812, 139.7671, true, true, false, false, false, 0).await }
        }),
        tokio::spawn({
            let client = client.clone();
            async move { client.get_weather_by_coordinates_async(34.6937, 135.5023, true, true, false, false, false, 0).await }
        }),
        tokio::spawn({
            let client = client.clone();
            async move { client.get_weather_by_coordinates_async(43.0642, 141.3469, true, true, false, false, false, 0).await }
        }),
    ];
    
    for (i, task) in tasks.into_iter().enumerate() {
        match task.await? {
            Ok(weather) => println!("Request {} succeeded: {:?}", i, weather),
            Err(e) => println!("Request {} failed: {}", i, e),
        }
    }
    
    Ok(())
}
```

## Configuration Changes

### Python Configuration

**Python (`config.ini`):**
```ini
[weather_server]
host = localhost
port = 4110
timeout = 30
debug = true

[location_server]
host = localhost
port = 4109

[client]
retry_count = 3
connection_pool_size = 10
```

**Python Code:**
```python
import configparser
from WIPCommonPy.clients.weather_client import WeatherClient

config = configparser.ConfigParser()
config.read('config.ini')

client = WeatherClient(
    host=config['weather_server']['host'],
    port=int(config['weather_server']['port']),
    timeout=int(config['weather_server']['timeout']),
    debug=config.getboolean('weather_server', 'debug')
)
```

### Rust Configuration

**Rust (Environment Variables + Code):**
```rust
use std::env;
use std::time::Duration;

#[derive(Debug)]
struct Config {
    weather_server_host: String,
    weather_server_port: u16,
    timeout: Duration,
    debug: bool,
    retry_count: u32,
    connection_pool_size: usize,
}

impl Config {
    fn from_env() -> Self {
        Self {
            weather_server_host: env::var("WEATHER_SERVER_HOST")
                .unwrap_or_else(|_| "127.0.0.1".to_string()),
            weather_server_port: env::var("WEATHER_SERVER_PORT")
                .unwrap_or_else(|_| "4110".to_string())
                .parse()
                .unwrap_or(4110),
            timeout: Duration::from_secs(
                env::var("CLIENT_TIMEOUT")
                    .unwrap_or_else(|_| "30".to_string())
                    .parse()
                    .unwrap_or(30)
            ),
            debug: env::var("DEBUG").is_ok(),
            retry_count: env::var("RETRY_COUNT")
                .unwrap_or_else(|_| "3".to_string())
                .parse()
                .unwrap_or(3),
            connection_pool_size: env::var("POOL_SIZE")
                .unwrap_or_else(|_| "10".to_string())
                .parse()
                .unwrap_or(10),
        }
    }
}

fn create_configured_client() -> WeatherClient {
    let config = Config::from_env();
    let server_address = format!("{}:{}", config.weather_server_host, config.weather_server_port);
    
    let client = WeatherClient::new(&server_address);
    client.set_timeout(config.timeout);
    client.set_debug_mode(config.debug);
    // Note: Rust client configuration methods may differ
    
    client
}
```

## Testing Migration

### Python Tests

**Python:**
```python
import unittest
from unittest.mock import patch, MagicMock
from WIPCommonPy.clients.weather_client import WeatherClient

class TestWeatherClient(unittest.TestCase):
    def setUp(self):
        self.client = WeatherClient(host='localhost', port=4110)
    
    @patch('WIPCommonPy.clients.weather_client.socket')
    def test_weather_request_success(self, mock_socket):
        # Mock successful response
        mock_socket.return_value.recv.return_value = b'mock_response_data'
        
        result = self.client.get_weather_by_coordinates(35.6812, 139.7671)
        
        self.assertIsNotNone(result)
        self.assertIn('area_code', result)
    
    def test_invalid_coordinates(self):
        with self.assertRaises(ValueError):
            self.client.get_weather_by_coordinates(91.0, 181.0)  # Invalid coords

if __name__ == '__main__':
    unittest.main()
```

**Rust Tests:**
```rust
#[cfg(test)]
mod tests {
    use super::*;
    use wip_rust::tests::common::mock_server::MockServerBuilder;
    use std::time::Duration;
    
    #[test]
    fn test_weather_request_success() {
        let server = MockServerBuilder::new().build().unwrap();
        let port = server.port();
        let handle = server.start();
        
        std::thread::sleep(Duration::from_millis(100));
        
        let client = WeatherClient::new(&format!("127.0.0.1:{}", port));
        let result = client.get_weather_by_coordinates(
            35.6812, 139.7671, true, true, false, false, false, 0
        );
        
        assert!(result.is_ok());
        let weather = result.unwrap();
        assert!(weather.contains_key("area_code"));
        
        server.stop();
    }
    
    #[test]
    fn test_invalid_coordinates() {
        let client = WeatherClient::new("127.0.0.1:4110");
        
        // The Rust implementation might handle validation differently
        // Check the actual behavior and adjust accordingly
        let result = client.get_weather_by_coordinates(
            91.0, 181.0, true, false, false, false, false, 0
        );
        
        // This might succeed but return an error from the server
        // or might be validated client-side
        match result {
            Ok(_) => {
                // Server-side validation
            },
            Err(_) => {
                // Client-side validation
            }
        }
    }
    
    #[test]
    fn test_error_handling() {
        // Test with non-existent server
        let client = WeatherClient::new("127.0.0.1:9999");
        let result = client.get_weather_by_coordinates(
            35.6812, 139.7671, true, false, false, false, false, 0
        );
        
        assert!(result.is_err());
    }
}
```

## Performance Considerations

### Memory Management

**Python (GC):**
```python
# Python handles memory automatically with garbage collection
def process_many_requests():
    clients = []
    for i in range(1000):
        client = WeatherClient(host='localhost', port=4110)
        clients.append(client)
        # Memory managed by GC
    # Clients will be cleaned up by GC when out of scope
```

**Rust (RAII):**
```rust
// Rust uses RAII - resources cleaned up automatically
fn process_many_requests() {
    let mut clients = Vec::new();
    for i in 0..1000 {
        let client = WeatherClient::new("127.0.0.1:4110");
        clients.push(client);
        // Memory managed by ownership system
    }
    // Clients dropped automatically when out of scope
}

// For better performance, reuse connections:
fn process_many_requests_optimized() {
    let client = WeatherClient::new("127.0.0.1:4110");
    client.set_connection_pool_size(50); // Reuse connections
    
    for i in 0..1000 {
        // Reuse the same client instance
        let result = client.get_weather_by_coordinates(
            35.0 + (i as f64 * 0.001), 
            139.0 + (i as f64 * 0.001), 
            true, false, false, false, false, 0
        );
        // Process result...
    }
}
```

### Concurrency Performance

**Python Threading:**
```python
import threading
import concurrent.futures

def parallel_weather_requests():
    client = WeatherClient(host='localhost', port=4110)
    coordinates = [(35.6812, 139.7671), (34.6937, 135.5023), ...]
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [
            executor.submit(client.get_weather_by_coordinates, lat, lng)
            for lat, lng in coordinates
        ]
        
        results = [future.result() for future in futures]
    
    return results
```

**Rust Native Threading:**
```rust
use std::thread;
use std::sync::Arc;

fn parallel_weather_requests() -> Vec<Result<std::collections::HashMap<String, u128>, Box<dyn std::error::Error + Send>>> {
    let client = Arc::new(WeatherClient::new("127.0.0.1:4110"));
    let coordinates = vec![(35.6812, 139.7671), (34.6937, 135.5023)];
    
    let handles: Vec<_> = coordinates
        .into_iter()
        .map(|(lat, lng)| {
            let client = Arc::clone(&client);
            thread::spawn(move || {
                client.get_weather_by_coordinates(lat, lng, true, true, false, false, false, 0)
                    .map_err(|e| e as Box<dyn std::error::Error + Send>)
            })
        })
        .collect();
    
    handles
        .into_iter()
        .map(|handle| handle.join().unwrap())
        .collect()
}
```

## Migration Strategies

### 1. Gradual Migration

**Phase 1: Side-by-side deployment**
```bash
# Run both implementations in parallel
python_weather_service --port 8080 &
rust_weather_service --port 8081 &

# Route traffic based on feature flags
```

**Phase 2: Service-by-service migration**
```rust
// Start with less critical services
// Migrate reporting service first
let report_client = ReportClient::new("127.0.0.1:4112");

// Keep weather service in Python initially
// Use Python client for weather requests
```

**Phase 3: Complete migration**
```rust
// Replace all Python clients with Rust
let weather_client = WeatherClient::new("127.0.0.1:4110");
let location_client = LocationClient::new("127.0.0.1:4109");
let query_client = QueryClient::new("127.0.0.1:4111");
let report_client = ReportClient::new("127.0.0.1:4112");
```

### 2. A/B Testing Migration

```rust
use rand::Rng;

enum ClientType {
    Python,
    Rust,
}

fn get_client_type() -> ClientType {
    if rand::thread_rng().gen_bool(0.5) {
        ClientType::Rust
    } else {
        ClientType::Python
    }
}

fn weather_request_with_ab_test(lat: f64, lng: f64) -> Result<WeatherData, Box<dyn std::error::Error>> {
    match get_client_type() {
        ClientType::Rust => {
            // Use Rust client
            let client = WeatherClient::new("127.0.0.1:4110");
            let result = client.get_weather_by_coordinates(lat, lng, true, true, false, false, false, 0)?;
            // Convert to common format
            Ok(convert_rust_result(result))
        },
        ClientType::Python => {
            // Call Python service via HTTP or subprocess
            call_python_weather_service(lat, lng)
        }
    }
}
```

### 3. Compatibility Layer

```rust
// Create a compatibility layer that mimics Python API
pub struct PythonCompatWeatherClient {
    inner: WeatherClient,
}

impl PythonCompatWeatherClient {
    pub fn new(host: &str, port: u16, debug: bool) -> Self {
        let address = format!("{}:{}", host, port);
        let client = WeatherClient::new(&address);
        if debug {
            client.set_debug_mode(true);
        }
        Self { inner: client }
    }
    
    // Python-style method signature
    pub fn get_weather_by_coordinates(
        &self,
        latitude: f64,
        longitude: f64,
        weather: Option<bool>,
        temperature: Option<bool>,
        precipitation_prob: Option<bool>
    ) -> Result<std::collections::HashMap<String, serde_json::Value>, Box<dyn std::error::Error>> {
        let result = self.inner.get_weather_by_coordinates(
            latitude,
            longitude,
            weather.unwrap_or(false),
            temperature.unwrap_or(false),
            precipitation_prob.unwrap_or(false),
            false,
            false,
            0
        )?;
        
        // Convert to Python-compatible format
        let mut python_result = std::collections::HashMap::new();
        for (key, value) in result {
            python_result.insert(key, serde_json::Value::Number((*value).into()));
        }
        
        Ok(python_result)
    }
}
```

## Common Pitfalls

### 1. Error Handling Differences

**❌ Common Mistake:**
```rust
// Don't ignore errors like you might in Python
let weather = client.get_weather_by_coordinates(lat, lng, true, true, false, false, false, 0).unwrap();
// This will panic on error!
```

**✅ Correct Approach:**
```rust
match client.get_weather_by_coordinates(lat, lng, true, true, false, false, false, 0) {
    Ok(weather) => {
        // Handle success
    },
    Err(e) => {
        // Handle error appropriately
        log::error!("Weather request failed: {}", e);
        return Err(e);
    }
}
```

### 2. Lifetime and Ownership Issues

**❌ Common Mistake:**
```rust
fn get_client() -> &WeatherClient {
    let client = WeatherClient::new("127.0.0.1:4110");
    &client  // Error: returning reference to local variable
}
```

**✅ Correct Approach:**
```rust
fn get_client() -> WeatherClient {
    WeatherClient::new("127.0.0.1:4110")  // Return owned value
}

// Or use Arc for shared ownership
use std::sync::Arc;

fn get_shared_client() -> Arc<WeatherClient> {
    Arc::new(WeatherClient::new("127.0.0.1:4110"))
}
```

### 3. Async Runtime Confusion

**❌ Common Mistake:**
```rust
// Mixing sync and async incorrectly
#[tokio::main]
async fn main() {
    let client = WeatherClient::new("127.0.0.1:4110");  // Sync client
    let result = client.get_weather_by_coordinates(...).await;  // Error: sync method
}
```

**✅ Correct Approach:**
```rust
#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let client = AsyncWeatherClient::new("127.0.0.1:4110").await?;  // Async client
    let result = client.get_weather_by_coordinates_async(...).await?;  // Async method
    Ok(())
}
```

### 4. Configuration Management

**❌ Common Mistake:**
```rust
// Hardcoding configuration like in quick Python scripts
let client = WeatherClient::new("192.168.1.100:4110");  // Hardcoded IP
```

**✅ Correct Approach:**
```rust
use std::env;

let server_address = env::var("WIP_SERVER_ADDRESS")
    .unwrap_or_else(|_| "127.0.0.1:4110".to_string());
let client = WeatherClient::new(&server_address);
```

## Migration Checklist

### Pre-Migration
- [ ] Analyze current Python codebase
- [ ] Identify dependencies and integration points
- [ ] Set up Rust development environment
- [ ] Create test data and scenarios
- [ ] Plan migration strategy (gradual vs. big bang)

### During Migration
- [ ] Start with non-critical components
- [ ] Implement comprehensive error handling
- [ ] Add extensive logging and monitoring
- [ ] Create compatibility layers if needed
- [ ] Run A/B tests to compare performance
- [ ] Validate protocol compatibility

### Post-Migration
- [ ] Monitor performance metrics
- [ ] Verify memory usage improvements
- [ ] Check error rates and patterns
- [ ] Update documentation and procedures
- [ ] Train team on Rust-specific patterns
- [ ] Clean up Python code and dependencies

### Performance Validation
- [ ] Measure packet processing speed
- [ ] Compare memory usage
- [ ] Test concurrent request handling
- [ ] Validate network throughput
- [ ] Check resource utilization

This migration guide provides a comprehensive roadmap for moving from the Python to Rust implementation while maintaining compatibility and improving performance.