/*! 
# WIP Rust Implementation

A high-performance Weather Information Protocol (WIP) client library and utilities implemented in Rust.

## Overview

WIP (Weather Transfer Protocol) is an NTP-based UDP application protocol designed for lightweight 
weather data transfer. This Rust implementation provides a complete client library with support for:

- **Weather Server Communication**: Fetch weather data by coordinates or area codes
- **Location Resolution**: Convert GPS coordinates to JMA area codes
- **Query Operations**: Direct weather data queries with flexible parameters  
- **Disaster Reporting**: Submit sensor data and disaster reports
- **Packet Format Support**: Full WIP packet specification compliance
- **Performance Optimized**: Zero-copy operations and efficient memory management

## Architecture

The library follows a modular architecture:

- **Packet Layer**: Binary packet format handling with checksum validation
- **Client Layer**: High-level UDP clients for different server types
- **Utils Layer**: Authentication, caching, configuration, and logging utilities

## Quick Start

```rust
use wip_rust::wip_common_rs::clients::weather_client::WeatherClient;

let client = WeatherClient::new("127.0.0.1:4110");
let weather_data = client.get_weather_by_coordinates(
    35.6812, 139.7671, // Tokyo coordinates
    true, true, false, false, false, 0
)?;
```

## Features

- **Full Python Compatibility**: API and protocol compatible with WIPCommonPy
- **Async Support**: Built on tokio for high-performance async operations
- **Connection Pooling**: Efficient connection management with automatic retries
- **Caching**: In-memory and file-based caching for improved performance
- **Security**: Checksum validation, timestamp verification, and authentication
- **Monitoring**: Comprehensive metrics and health check capabilities
- **Testing**: Extensive test suite with mock servers and load testing

## Performance

- **Target Response Time**: <100ms average
- **Throughput**: >100 requests/second  
- **Memory Optimized**: Zero-copy operations and buffer pooling
- **Concurrent**: Full multi-threading support with connection pooling

## Data Sources

- **JMA (Japan Meteorological Agency)**: Primary weather data source
- **Area Codes**: 6-digit JMA regional classification system
- **Weather Codes**: JMA weather code system (100-series clear, 200-series cloudy, etc.)

## Packet Format

WIP uses a binary packet format optimized for UDP transmission:

- **Base Size**: 16 bytes (128 bits) minimum
- **Header**: Version (4bit), Packet ID (12bit), Type (3bit), Flags (8bit)
- **Core Data**: Timestamp (64bit), Area Code (20bit), Checksum (12bit)
- **Extensions**: Variable-length fields for coordinates, alerts, disaster info

## Compatibility

This implementation maintains full compatibility with:
- WIPCommonPy (Python reference implementation)
- WIP Protocol Specification v1.0
- JMA data formats and area code system

## Examples

See the `examples/` directory for comprehensive usage examples covering:
- Basic weather queries
- Location resolution
- Disaster reporting
- Async client usage
- Custom packet handling
*/

// 新しい構造化されたライブラリ
pub mod wip_common_rs;

/// Common imports for WIP Rust users
/// 
/// This prelude module contains the most commonly used types and traits.
/// Import this to get started quickly with the WIP library.
/// 
/// # Example
/// 
/// ```rust
/// use wip_rust::prelude::*;
/// 
/// let client = WeatherClient::new("127.0.0.1:4110");
/// let location_client = LocationClient::new("127.0.0.1:4109");
/// ```
pub mod prelude {
    // Client APIs
    pub use crate::wip_common_rs::clients::weather_client::WeatherClient;
    pub use crate::wip_common_rs::clients::location_client::LocationClient;
    pub use crate::wip_common_rs::clients::query_client::QueryClient;
    pub use crate::wip_common_rs::clients::report_client::ReportClient;
    
    // Async clients
    pub use crate::wip_common_rs::clients::async_weather_client::AsyncWeatherClient;

    // Packet types
    pub use crate::wip_common_rs::packet::types::location_packet::{LocationRequest, LocationResponse};
    pub use crate::wip_common_rs::packet::types::query_packet::{QueryRequest, QueryResponse};
    pub use crate::wip_common_rs::packet::types::report_packet::{ReportRequest, ReportResponse};
    pub use crate::wip_common_rs::packet::types::error_response::ErrorResponse;

    // Unified client
    pub use crate::wip_common_rs::client::WipClient;
    
    // Core traits
    pub use crate::wip_common_rs::packet::core::PacketFormat;
    
    // Utilities
    pub use crate::wip_common_rs::clients::utils::packet_id_generator::PacketIDGenerator12Bit;
    pub use crate::wip_common_rs::utils::config_loader::ConfigLoader;
    pub use crate::wip_common_rs::utils::auth::WIPAuth;
    
    // Common errors
    pub use crate::wip_common_rs::packet::core::exceptions::{
        PacketParseError, ChecksumError, InvalidFieldError
    };
}

