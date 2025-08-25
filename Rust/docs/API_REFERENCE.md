# WIP Rust Implementation - API Reference

## 📚 Overview

WIP Rust Implementation provides a complete Rust-based client library for the WIP (Weather Information Protocol) disaster management system. This library offers full compatibility with the Python WIP server while providing Rust's performance and safety benefits.

## 🏗️ Architecture

### Core Components

- **Packet Types**: Location, Report, Query, and Response packets
- **Client Libraries**: Weather, Location, Report, and Query clients  
- **Utilities**: Memory management, error handling, metrics, health checking
- **Advanced Features**: Auto-recovery, communication optimization, monitoring

## 📦 Packet Types

### LocationRequest

Requests area code information for given coordinates.

```rust
use wip_rust::wip_common_rs::packet::types::location_packet::LocationRequest;

let mut request = LocationRequest::new();
request.set_latitude(35.6812);  // Tokyo latitude
request.set_longitude(139.7671); // Tokyo longitude

let packet_bytes = request.to_bytes();
```

**Methods:**
- `new() -> Self` - Create a new location request
- `set_latitude(lat: f64)` - Set latitude (-90.0 to 90.0)
- `set_longitude(lon: f64)` - Set longitude (-180.0 to 180.0)
- `get_latitude() -> f64` - Get current latitude
- `get_longitude() -> f64` - Get current longitude
- `to_bytes() -> Vec<u8>` - Serialize to byte array

### LocationResponse

Contains area code and region information for a location.

```rust
use wip_rust::wip_common_rs::packet::types::location_packet::LocationResponse;

let mut response = LocationResponse::new();
response.set_area_code(123456);
response.set_region_name("Tokyo".to_string());
```

**Methods:**
- `new() -> Self` - Create a new location response
- `set_area_code(code: u32)` - Set numeric area code
- `set_region_name(name: String)` - Set human-readable region name
- `get_area_code() -> u32` - Get area code
- `get_region_name() -> String` - Get region name

### ReportRequest

Submits disaster report information.

```rust
use wip_rust::wip_common_rs::packet::types::report_packet::ReportRequest;

let mut request = ReportRequest::new();
request.set_disaster_type("earthquake".to_string());
request.set_severity(7); // Scale 1-10
request.set_description("Major earthquake detected in Tokyo".to_string());
```

**Methods:**
- `new() -> Self` - Create a new report request
- `set_disaster_type(type: String)` - Set disaster type
- `set_severity(level: u8)` - Set severity (1-10 scale)
- `set_description(desc: String)` - Set detailed description
- `get_disaster_type() -> String` - Get disaster type
- `get_severity() -> u8` - Get severity level
- `get_description() -> String` - Get description

### ReportResponse

Acknowledges disaster report submission.

```rust
use wip_rust::wip_common_rs::packet::types::report_packet::ReportResponse;

let mut response = ReportResponse::new();
response.set_report_id(12345);
response.set_status("accepted".to_string());
```

### QueryRequest

Performs general information queries.

```rust
use wip_rust::wip_common_rs::packet::types::query_packet::QueryRequest;

let mut request = QueryRequest::new();
request.set_query_type("status".to_string());
request.set_parameters("region=tokyo&type=current".to_string());
```

### QueryResponse

Returns query results.

```rust
use wip_rust::wip_common_rs::packet::types::query_packet::QueryResponse;

let mut response = QueryResponse::new();
response.set_result_count(42);
response.set_data(r#"{"status": "ok", "data": [...]}}"#.to_string());
```

## 🌐 Client Libraries

### WeatherClient

High-level client for weather information queries.

```rust
use wip_rust::wip_common_rs::clients::weather_client::WeatherClient;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let server_addr = "127.0.0.1:8888".parse()?;
    let mut client = WeatherClient::new(server_addr).await?;
    
    let weather_data = client.get_weather_data("Tokyo", "current").await?;
    println!("Weather: {:?}", weather_data);
    
    Ok(())
}
```

**Methods:**
- `new(addr: SocketAddr) -> Result<Self, Error>` - Create new weather client
- `get_weather_data(location: &str, period: &str) -> Result<WeatherData, Error>` - Get weather information
- `get_forecast(location: &str, hours: u32) -> Result<Forecast, Error>` - Get weather forecast

### LocationClient

Client for coordinate-to-area-code resolution.

```rust
use wip_rust::wip_common_rs::clients::location_client::LocationClient;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let server_addr = "127.0.0.1:8888".parse()?;
    let mut client = LocationClient::new(server_addr).await?;
    
    let area_info = client.get_area_code(35.6812, 139.7671).await?;
    println!("Area: {}", area_info);
    
    Ok(())
}
```

**Methods:**
- `new(addr: SocketAddr) -> Result<Self, Error>` - Create new location client
- `get_area_code(lat: f64, lon: f64) -> Result<String, Error>` - Get area code for coordinates
- `resolve_location(lat: f64, lon: f64) -> Result<LocationInfo, Error>` - Get detailed location information

### ReportClient

Client for disaster report submission.

```rust
use wip_rust::wip_common_rs::clients::report_client::ReportClient;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let server_addr = "127.0.0.1:8888".parse()?;
    let mut client = ReportClient::new(server_addr).await?;
    
    let report_id = client.submit_disaster_report(
        "earthquake",
        7,
        35.6812,
        139.7671,
        "Major earthquake detected in Tokyo metropolitan area"
    ).await?;
    
    println!("Report submitted with ID: {}", report_id);
    
    Ok(())
}
```

**Methods:**
- `new(addr: SocketAddr) -> Result<Self, Error>` - Create new report client
- `submit_disaster_report(type: &str, severity: u8, lat: f64, lon: f64, description: &str) -> Result<u32, Error>` - Submit disaster report
- `get_report_status(report_id: u32) -> Result<ReportStatus, Error>` - Check report status

### QueryClient

Client for general information queries.

```rust
use wip_rust::wip_common_rs::clients::query_client::QueryClient;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let server_addr = "127.0.0.1:8888".parse()?;
    let mut client = QueryClient::new(server_addr).await?;
    
    let results = client.execute_query("status", "region=tokyo").await?;
    println!("Query results: {:?}", results);
    
    Ok(())
}
```

**Methods:**
- `new(addr: SocketAddr) -> Result<Self, Error>` - Create new query client
- `execute_query(query_type: &str, parameters: &str) -> Result<QueryResults, Error>` - Execute query
- `get_statistics(area: &str, period: &str) -> Result<Statistics, Error>` - Get statistical data

## 🔧 Utility Functions

### Checksum Operations

```rust
use wip_rust::wip_common_rs::packet::core::checksum::{
    calc_checksum12, verify_checksum12, embed_checksum12_le
};

// Calculate 12-bit checksum
let data = vec![0x12, 0x34, 0x56, 0x78];
let checksum = calc_checksum12(&data);

// Embed checksum in packet
let mut packet = vec![0x12, 0x34, 0x56, 0x78, 0x00, 0x00];
embed_checksum12_le(&mut packet);

// Verify packet integrity
let is_valid = verify_checksum12(&packet).is_ok();
```

### Bit Manipulation

```rust
use wip_rust::wip_common_rs::packet::core::bit_utils::{
    extract_bits, set_bits, bytes_to_u128_le, u128_to_bytes_le
};

// Extract specific bits
let data = 0x12345678u128;
let bits = extract_bits(data, 8, 8); // Extract 8 bits starting at position 8

// Set specific bits
let mut data = 0u128;
set_bits(&mut data, 0, 8, 0xFF); // Set first 8 bits to 0xFF

// Convert between bytes and u128
let bytes = vec![0x12, 0x34, 0x56, 0x78];
let value = bytes_to_u128_le(&bytes);
let bytes_back = u128_to_bytes_le(value);
```

## 🔍 Error Codes

WIP Rust uses standardized error codes compatible with the Python implementation:

- **400**: Bad Request - Invalid input parameters
- **410**: Not Found - Requested resource not found
- **411**: Payload Too Large - Request data too large
- **420**: Request Timeout - Operation timed out
- **421**: Too Many Requests - Rate limit exceeded
- **500**: Internal Server Error - Unexpected server error
- **501**: Not Implemented - Feature not implemented
- **503**: Service Unavailable - Service temporarily unavailable
- **504**: Gateway Timeout - Upstream timeout
- **600-699**: Network errors
- **700-799**: Protocol errors
- **800-899**: System errors

## 🎛️ Configuration

### Environment Variables

- `WIP_SERVER_HOST`: Default server hostname (default: "127.0.0.1")
- `WIP_SERVER_PORT`: Default server port (default: "8888")
- `WIP_LOG_LEVEL`: Logging level (default: "info")
- `WIP_CACHE_SIZE`: Buffer pool cache size (default: "1000")
- `WIP_METRICS_ENABLED`: Enable metrics collection (default: "true")

### Configuration Files

WIP Rust supports TOML configuration files:

```toml
[server]
host = "127.0.0.1"
port = 8888
timeout = 30

[client]
retry_attempts = 3
retry_delay = 1000
compression_threshold = 1024

[metrics]
enabled = true
collection_interval = 30
export_format = "prometheus"

[health_check]
enabled = true
check_interval = 30
timeout = 10

[memory]
pool_size = 1000
max_buffer_size = 65536
cleanup_interval = 300
```

## 📈 Performance Considerations

### Memory Usage

- Buffer pooling reduces allocation overhead
- Zero-copy operations where possible
- Configurable memory limits and cleanup

### Network Optimization

- Packet compression for large payloads
- Connection pooling and reuse
- Adaptive concurrency control

### Monitoring

- Built-in metrics collection
- Prometheus-compatible export
- Health check endpoints
- Performance profiling support

## 🧪 Testing

### Running Tests

```bash
# Run all tests
cargo test

# Run unit tests only
cargo test --lib

# Run integration tests
cargo test --test '*'

# Run with Python server integration
cargo test --test test_python_server_integration

# Run performance benchmarks
cargo bench
```

### Test Categories

- **Unit Tests**: Individual component testing
- **Integration Tests**: Python server compatibility
- **End-to-End Tests**: Complete workflow validation
- **Performance Tests**: Benchmarking and profiling
- **Stress Tests**: High-load scenarios

## 🔗 Python Compatibility

WIP Rust maintains full API compatibility with the Python WIP implementation:

- Same packet formats and checksums
- Compatible error codes and messages
- Identical network protocol
- Matching configuration options
- Comparable performance characteristics

## 📋 Best Practices

### Error Handling

```rust
// Always handle errors appropriately
match client.get_area_code(lat, lon).await {
    Ok(area) => println!("Area: {}", area),
    Err(WIPError { code: WIPErrorCode::BadRequest, .. }) => {
        eprintln!("Invalid coordinates provided");
    },
    Err(WIPError { code: WIPErrorCode::RequestTimeout, .. }) => {
        eprintln!("Server timeout - retrying...");
        // Implement retry logic
    },
    Err(error) => {
        eprintln!("Unexpected error: {}", error.message);
    }
}
```

### Resource Management

```rust
// Use RAII for resource cleanup
{
    let buffer = get_buffer(1024);
    // Buffer automatically returned when scope ends
    process_data(&buffer)?;
} // Buffer returned here

// Prefer async/await for network operations
async fn fetch_weather_data() -> WIPResult<WeatherData> {
    let mut client = WeatherClient::new(server_addr).await?;
    let data = client.get_weather_data("Tokyo", "current").await?;
    Ok(data)
}
```

### Performance Optimization

```rust
// Reuse clients when possible
let mut client = LocationClient::new(server_addr).await?;
for location in locations {
    let area = client.get_area_code(location.lat, location.lon).await?;
    // Process area...
}

// Use bulk operations for better performance
let requests: Vec<_> = locations.iter()
    .map(|loc| client.get_area_code(loc.lat, loc.lon))
    .collect();
let results = futures::future::join_all(requests).await;
```