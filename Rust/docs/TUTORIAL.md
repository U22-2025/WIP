# WIP Rust Implementation - Tutorial

## 🚀 Getting Started

This tutorial will guide you through using the WIP Rust implementation for disaster management communications.

### Prerequisites

- Rust 1.70+ installed
- Access to a running Python WIP server (for integration testing)
- Basic understanding of async Rust programming

### Installation

Add WIP Rust to your `Cargo.toml`:

```toml
[dependencies]
wip_rust = { path = "path/to/wip_rust" }
tokio = { version = "1.0", features = ["full"] }
```

## 📍 Tutorial 1: Basic Location Services

Let's start with a simple example of resolving coordinates to area codes.

```rust
use wip_rust::wip_common_rs::clients::location_client::LocationClient;
use std::error::Error;

#[tokio::main]
async fn main() -> Result<(), Box<dyn Error>> {
    // Connect to the WIP server
    let server_addr = "127.0.0.1:8888".parse()?;
    let mut client = LocationClient::new(server_addr).await?;
    
    // Tokyo coordinates
    let tokyo_lat = 35.6812;
    let tokyo_lon = 139.7671;
    
    println!("🌍 Resolving location for Tokyo...");
    
    match client.get_area_code(tokyo_lat, tokyo_lon).await {
        Ok(area_info) => {
            println!("✅ Tokyo area code: {}", area_info);
        },
        Err(e) => {
            println!("❌ Error: {}", e);
        }
    }
    
    Ok(())
}
```

### Key Concepts

1. **Client Creation**: All WIP clients are created asynchronously
2. **Error Handling**: Use `Result` types for robust error handling
3. **Coordinates**: Use standard latitude/longitude format

## 🚨 Tutorial 2: Disaster Reporting

Learn how to submit disaster reports to the WIP system.

```rust
use wip_rust::wip_common_rs::clients::report_client::ReportClient;
use std::error::Error;

#[tokio::main]
async fn main() -> Result<(), Box<dyn Error>> {
    let server_addr = "127.0.0.1:8888".parse()?;
    let mut client = ReportClient::new(server_addr).await?;
    
    println!("🚨 Submitting earthquake report...");
    
    let report_id = client.submit_disaster_report(
        "earthquake",           // Disaster type
        7,                     // Severity (1-10 scale)
        35.6812,              // Latitude
        139.7671,             // Longitude
        "Major earthquake detected in Tokyo metropolitan area. Buildings shaking, people evacuating."
    ).await?;
    
    println!("✅ Report submitted successfully!");
    println!("📋 Report ID: {}", report_id);
    
    Ok(())
}
```

### Disaster Types

Common disaster types supported:
- `"earthquake"`
- `"tsunami"`
- `"typhoon"`
- `"flood"`
- `"landslide"`
- `"volcanic_eruption"`
- `"fire"`
- `"explosion"`

### Severity Scale

Use a 1-10 scale where:
- 1-3: Minor incidents
- 4-6: Moderate disasters
- 7-8: Major disasters
- 9-10: Catastrophic events

## 🌤️ Tutorial 3: Weather Information

Access weather data and forecasts.

```rust
use wip_rust::wip_common_rs::clients::weather_client::WeatherClient;
use std::error::Error;

#[tokio::main]
async fn main() -> Result<(), Box<dyn Error>> {
    let server_addr = "127.0.0.1:8888".parse()?;
    let mut client = WeatherClient::new(server_addr).await?;
    
    println!("🌤️ Fetching weather data for Tokyo...");
    
    // Get current weather
    match client.get_weather_data("Tokyo", "current").await {
        Ok(weather_data) => {
            println!("📊 Current weather: {:?}", weather_data);
        },
        Err(e) => {
            println!("⚠️ Weather service error: {}", e);
        }
    }
    
    // Get 24-hour forecast
    println!("🔮 Fetching 24-hour forecast...");
    match client.get_weather_data("Tokyo", "24h").await {
        Ok(forecast) => {
            println!("📈 24h forecast: {:?}", forecast);
        },
        Err(e) => {
            println!("⚠️ Forecast service error: {}", e);
        }
    }
    
    Ok(())
}
```

## 🔍 Tutorial 4: Information Queries

Perform general information queries.

```rust
use wip_rust::wip_common_rs::clients::query_client::QueryClient;
use std::error::Error;

#[tokio::main]
async fn main() -> Result<(), Box<dyn Error>> {
    let server_addr = "127.0.0.1:8888".parse()?;
    let mut client = QueryClient::new(server_addr).await?;
    
    // Query system status
    println!("📊 Querying system status...");
    match client.execute_query("status", "region=tokyo").await {
        Ok(results) => {
            println!("✅ System status: {:?}", results);
        },
        Err(e) => {
            println!("❌ Query failed: {}", e);
        }
    }
    
    // Query active alerts
    println!("🚨 Checking active alerts...");
    match client.execute_query("alerts", "severity=high&region=kanto").await {
        Ok(alerts) => {
            println!("🔔 Active alerts: {:?}", alerts);
        },
        Err(e) => {
            println!("❌ Alert query failed: {}", e);
        }
    }
    
    // Query historical data
    println!("📈 Fetching historical data...");
    match client.execute_query("history", "type=earthquake&from=2024-01-01&to=2024-12-31").await {
        Ok(history) => {
            println!("📚 Historical data: {:?}", history);
        },
        Err(e) => {
            println!("❌ History query failed: {}", e);
        }
    }
    
    Ok(())
}
```

### Common Query Types

- `"status"` - System and regional status
- `"alerts"` - Active alerts and warnings
- `"history"` - Historical disaster data
- `"statistics"` - Statistical summaries
- `"forecast"` - Predictive information
- `"resources"` - Available resources (shelters, etc.)

## 🔄 Tutorial 5: Complete Disaster Response Workflow

A comprehensive example showing a complete disaster response workflow.

```rust
use wip_rust::wip_common_rs::clients::{
    location_client::LocationClient,
    report_client::ReportClient,
    weather_client::WeatherClient,
    query_client::QueryClient,
};
use std::error::Error;
use std::time::Instant;

#[tokio::main]
async fn main() -> Result<(), Box<dyn Error>> {
    let server_addr = "127.0.0.1:8888".parse()?;
    
    println!("🚨 Emergency Response Workflow Starting...");
    let start_time = Instant::now();
    
    // Step 1: Determine location
    println!("\n📍 Step 1: Resolving incident location...");
    let mut location_client = LocationClient::new(server_addr).await?;
    
    // Incident coordinates (example: major earthquake near Tokyo)
    let incident_lat = 35.6812;
    let incident_lon = 139.7671;
    
    let area_info = match location_client.get_area_code(incident_lat, incident_lon).await {
        Ok(area) => {
            println!("✅ Location resolved: {}", area);
            area
        },
        Err(e) => {
            println!("⚠️ Location resolution failed: {}", e);
            "Unknown Area".to_string()
        }
    };
    
    // Step 2: Submit initial disaster report
    println!("\n🚨 Step 2: Submitting initial disaster report...");
    let mut report_client = ReportClient::new(server_addr).await?;
    
    let report_id = report_client.submit_disaster_report(
        "earthquake",
        8, // Major earthquake
        incident_lat,
        incident_lon,
        &format!("Major earthquake magnitude 8.0 detected in {}. Immediate response required. Buildings damaged, people trapped.", area_info)
    ).await?;
    
    println!("✅ Initial report submitted: ID {}", report_id);
    
    // Step 3: Get weather context
    println!("\n🌤️ Step 3: Gathering weather context...");
    let mut weather_client = WeatherClient::new(server_addr).await?;
    
    match weather_client.get_weather_data("Tokyo", "current").await {
        Ok(weather) => {
            println!("📊 Current weather conditions: {:?}", weather);
        },
        Err(e) => {
            println!("⚠️ Weather data unavailable: {}", e);
        }
    }
    
    // Step 4: Check system status and resources
    println!("\n📊 Step 4: Checking system resources...");
    let mut query_client = QueryClient::new(server_addr).await?;
    
    // Check evacuation routes
    match query_client.execute_query("resources", "type=evacuation&location=tokyo&radius=10km").await {
        Ok(routes) => {
            println!("🛣️ Evacuation routes: {:?}", routes);
        },
        Err(e) => {
            println!("⚠️ Evacuation route query failed: {}", e);
        }
    }
    
    // Check available shelters
    match query_client.execute_query("resources", "type=shelter&location=tokyo&radius=5km").await {
        Ok(shelters) => {
            println!("🏠 Available shelters: {:?}", shelters);
        },
        Err(e) => {
            println!("⚠️ Shelter query failed: {}", e);
        }
    }
    
    // Step 5: Submit follow-up reports
    println!("\n📋 Step 5: Submitting follow-up reports...");
    
    let follow_up_scenarios = vec![
        ("aftershock", 6, "Aftershock magnitude 6.0 detected"),
        ("fire", 5, "Fire reported in damaged building"),
        ("landslide", 4, "Minor landslide on hillside due to earthquake"),
    ];
    
    for (disaster_type, severity, description) in follow_up_scenarios {
        match report_client.submit_disaster_report(
            disaster_type,
            severity,
            incident_lat + fastrand::f64() * 0.01, // Slight position variation
            incident_lon + fastrand::f64() * 0.01,
            &format!("{} - Follow-up to incident {}", description, report_id)
        ).await {
            Ok(follow_up_id) => {
                println!("✅ Follow-up report {}: ID {}", disaster_type, follow_up_id);
            },
            Err(e) => {
                println!("❌ Follow-up report {} failed: {}", disaster_type, e);
            }
        }
    }
    
    // Step 6: Final status check
    println!("\n🔍 Step 6: Final status verification...");
    match query_client.execute_query("status", &format!("region={}&incident={}", area_info, report_id)).await {
        Ok(status) => {
            println!("📊 Final system status: {:?}", status);
        },
        Err(e) => {
            println!("⚠️ Status query failed: {}", e);
        }
    }
    
    let total_time = start_time.elapsed();
    println!("\n✅ Emergency Response Workflow Completed");
    println!("⏱️ Total time: {:?}", total_time);
    println!("📋 Primary incident ID: {}", report_id);
    println!("📍 Location: {} ({:.4}, {:.4})", area_info, incident_lat, incident_lon);
    
    Ok(())
}
```

## 🔧 Tutorial 6: Advanced Features

### Error Handling and Retry Logic

```rust
use wip_rust::common::utils::auto_recovery::{RetryManager, RetryConfig};
use wip_rust::common::utils::error_handling::{WIPError, WIPErrorCode};
use std::time::Duration;

#[tokio::main]
async fn main() -> Result<(), Box<dyn Error>> {
    // Configure retry behavior
    let retry_config = RetryConfig {
        max_attempts: 5,
        base_delay: Duration::from_millis(100),
        max_delay: Duration::from_secs(10),
        backoff_multiplier: 2.0,
        jitter: true,
    };
    
    let retry_manager = RetryManager::new(retry_config);
    
    // Retry a potentially failing operation
    let result = retry_manager.retry(|| async {
        let server_addr = "127.0.0.1:8888".parse().unwrap();
        let mut client = LocationClient::new(server_addr).await?;
        client.get_area_code(35.6812, 139.7671).await
    }).await;
    
    match result {
        Ok(area) => println!("✅ Location resolved: {}", area),
        Err(WIPError { code: WIPErrorCode::RequestTimeout, .. }) => {
            println!("❌ Server timeout after retries");
        },
        Err(e) => println!("❌ Failed after retries: {}", e),
    }
    
    Ok(())
}
```

### Metrics and Monitoring

```rust
use wip_rust::common::utils::metrics::{GLOBAL_METRICS, GLOBAL_COMM_METRICS, Timer};
use std::sync::Arc;

#[tokio::main]
async fn main() -> Result<(), Box<dyn Error>> {
    // Time an operation
    let _timer = Timer::new("location_lookup".to_string(), Arc::clone(&GLOBAL_METRICS));
    
    let server_addr = "127.0.0.1:8888".parse()?;
    let mut client = LocationClient::new(server_addr).await?;
    
    // Perform operations that will be tracked
    for i in 0..10 {
        let lat = 35.6812 + (i as f64 * 0.001);
        let lon = 139.7671 + (i as f64 * 0.001);
        
        match client.get_area_code(lat, lon).await {
            Ok(_) => {
                GLOBAL_METRICS.increment_counter("successful_requests");
            },
            Err(_) => {
                GLOBAL_METRICS.increment_counter("failed_requests");
            }
        }
    }
    
    // Export metrics
    let metrics_snapshot = GLOBAL_METRICS.get_snapshot();
    println!("📊 Metrics collected:");
    for (name, counter) in &metrics_snapshot.counters {
        println!("  {}: {}", name, counter.value);
    }
    
    let comm_metrics = GLOBAL_COMM_METRICS.get_metrics();
    println!("📡 Communication metrics:");
    println!("  Success rate: {:.2}%", comm_metrics.success_rate() * 100.0);
    println!("  Total requests: {}", comm_metrics.requests_total);
    
    Ok(())
}
```

### Health Monitoring

```rust
use wip_rust::common::utils::health_check::{
    HealthCheckManager, HealthCheckConfig, create_network_checker
};

#[tokio::main]
async fn main() -> Result<(), Box<dyn Error>> {
    let config = HealthCheckConfig::default();
    let mut health_manager = HealthCheckManager::new(
        config,
        Arc::clone(&GLOBAL_METRICS)
    );
    
    // Add health checkers
    let network_checker = create_network_checker(
        "wip_server",
        vec![("127.0.0.1".to_string(), 8888)]
    );
    health_manager.add_checker(network_checker);
    
    // Run health checks
    let health_report = health_manager.check_all().await;
    
    println!("🏥 System Health Report:");
    println!("Overall status: {:?}", health_report.overall_status);
    
    for (name, result) in &health_report.checks {
        println!("  {}: {:?} ({}ms)", 
                 name, 
                 result.status, 
                 result.duration.as_millis());
    }
    
    // Get HTTP-compatible health endpoint
    let (status_code, json_response) = health_manager.health_endpoint().await;
    println!("HTTP Status: {}", status_code);
    println!("Response: {}", json_response);
    
    Ok(())
}
```

## 🧪 Tutorial 7: Testing and Development

### Unit Testing

```rust
#[cfg(test)]
mod tests {
    use super::*;
    use wip_rust::wip_common_rs::packet::types::location_packet::LocationRequest;
    
    #[test]
    fn test_location_packet_creation() {
        let mut request = LocationRequest::new();
        request.set_latitude(35.6812);
        request.set_longitude(139.7671);
        
        assert_eq!(request.get_latitude(), 35.6812);
        assert_eq!(request.get_longitude(), 139.7671);
        
        let bytes = request.to_bytes();
        assert!(!bytes.is_empty());
    }
    
    #[tokio::test]
    async fn test_location_client_integration() {
        // This test requires a running Python WIP server
        let server_addr = "127.0.0.1:8888".parse().unwrap();
        
        match LocationClient::new(server_addr).await {
            Ok(mut client) => {
                match client.get_area_code(35.6812, 139.7671).await {
                    Ok(area) => println!("Integration test passed: {}", area),
                    Err(e) => println!("Server error (may be expected): {}", e),
                }
            },
            Err(_) => println!("Server not available - skipping integration test"),
        }
    }
}
```

### Performance Testing

```rust
use std::time::Instant;

#[tokio::main]
async fn main() -> Result<(), Box<dyn Error>> {
    let server_addr = "127.0.0.1:8888".parse()?;
    let mut client = LocationClient::new(server_addr).await?;
    
    println!("🏃 Running performance test...");
    
    let test_count = 100;
    let start = Instant::now();
    let mut successful = 0;
    
    for i in 0..test_count {
        let lat = 35.6812 + (i as f64 * 0.0001);
        let lon = 139.7671 + (i as f64 * 0.0001);
        
        if client.get_area_code(lat, lon).await.is_ok() {
            successful += 1;
        }
    }
    
    let duration = start.elapsed();
    
    println!("📊 Performance Results:");
    println!("  Total requests: {}", test_count);
    println!("  Successful: {}", successful);
    println!("  Success rate: {:.1}%", (successful as f64 / test_count as f64) * 100.0);
    println!("  Total time: {:?}", duration);
    println!("  Average time per request: {:?}", duration / test_count);
    println!("  Requests per second: {:.1}", test_count as f64 / duration.as_secs_f64());
    
    Ok(())
}
```

## 🔧 Tutorial 8: Configuration and Deployment

### Configuration File Example

Create a `wip_config.toml` file:

```toml
[server]
host = "127.0.0.1"
port = 8888
timeout = 30

[client]
retry_attempts = 3
retry_delay = 1000
compression_threshold = 1024
connection_pool_size = 10

[metrics]
enabled = true
collection_interval = 30
export_format = "prometheus"

[health_check]
enabled = true
check_interval = 30
timeout = 10

[logging]
level = "info"
format = "json"
file = "wip_client.log"
```

### Using Configuration

```rust
use wip_rust::common::utils::config_loader::ConfigLoader;

#[tokio::main]
async fn main() -> Result<(), Box<dyn Error>> {
    // Load configuration
    let config = ConfigLoader::from_file("wip_config.toml")?;
    
    let server_host = config.get_string("server.host").unwrap_or("127.0.0.1".to_string());
    let server_port = config.get_u16("server.port").unwrap_or(8888);
    let timeout = config.get_u64("server.timeout").unwrap_or(30);
    
    let server_addr = format!("{}:{}", server_host, server_port).parse()?;
    
    println!("🔧 Connecting to server: {}", server_addr);
    
    let mut client = LocationClient::new(server_addr).await?;
    
    // Use timeout from config
    let result = tokio::time::timeout(
        Duration::from_secs(timeout),
        client.get_area_code(35.6812, 139.7671)
    ).await;
    
    match result {
        Ok(Ok(area)) => println!("✅ Area: {}", area),
        Ok(Err(e)) => println!("❌ Server error: {}", e),
        Err(_) => println!("⏰ Operation timed out"),
    }
    
    Ok(())
}
```

## 🚀 Next Steps

### Advanced Topics

1. **Custom Packet Types**: Learn to create custom packet formats
2. **Protocol Extensions**: Extend the WIP protocol for specific needs
3. **Performance Optimization**: Advanced tuning for high-throughput scenarios
4. **Security**: Implementing authentication and encryption
5. **Clustering**: Multi-server deployments and load balancing

### Resources

- [API Reference](API_REFERENCE.md) - Complete API documentation
- [Examples Directory](../examples/) - More code examples
- [Test Suite](../tests/) - Comprehensive test examples
- [Benchmarks](../benches/) - Performance testing examples

### Community

- Report issues and request features
- Contribute to the codebase
- Share your use cases and experiences

## 🔍 Troubleshooting

### Common Issues

1. **Connection Refused**
   ```
   Error: Connection refused (os error 111)
   ```
   - Ensure the Python WIP server is running
   - Check server host and port configuration
   - Verify firewall settings

2. **Timeout Errors**
   ```
   Error: Request timeout after 30s
   ```
   - Increase timeout values in configuration
   - Check network connectivity
   - Verify server responsiveness

3. **Invalid Coordinates**
   ```
   Error: BadRequest - Invalid coordinates
   ```
   - Ensure latitude is between -90.0 and 90.0
   - Ensure longitude is between -180.0 and 180.0
   - Check for NaN or infinite values

4. **Checksum Errors**
   ```
   Error: ChecksumMismatch - Packet corrupted
   ```
   - Check network stability
   - Verify protocol compatibility
   - Review packet construction code

### Debug Mode

Enable debug logging:

```rust
env_logger::init();
log::set_max_level(log::LevelFilter::Debug);
```

Or set environment variable:
```bash
RUST_LOG=debug cargo run
```

### Performance Issues

1. **Memory Usage**: Monitor with `GLOBAL_BUFFER_POOL.get_stats()`
2. **Network Latency**: Use metrics to track response times
3. **Connection Pool**: Adjust pool size based on usage patterns

Happy coding with WIP Rust! 🦀🌍