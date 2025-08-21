# WIP Rust Implementation - Basic Tutorial

This tutorial will guide you through the basic usage of the WIP (Weather Information Protocol) Rust library, from installation to making your first weather requests.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Installation](#installation)
3. [Quick Start](#quick-start)
4. [Understanding WIP Concepts](#understanding-wip-concepts)
5. [Basic Weather Requests](#basic-weather-requests)
6. [Location Resolution](#location-resolution)
7. [Error Handling](#error-handling)
8. [Working with Different Data Types](#working-with-different-data-types)
9. [Next Steps](#next-steps)

## Prerequisites

Before starting, ensure you have:
- Rust 1.70 or later installed
- Basic knowledge of Rust programming
- Access to WIP servers (or mock servers for testing)
- Understanding of geographic coordinates (latitude/longitude)

## Installation

### 1. Create a new Rust project

```bash
cargo new wip_weather_app
cd wip_weather_app
```

### 2. Add WIP Rust to your dependencies

Edit your `Cargo.toml`:

```toml
[dependencies]
wip-rust = "1.0"
serde_json = "1.0"    # For JSON handling
tokio = { version = "1.0", features = ["full"] }  # For async support (optional)
```

### 3. Import the prelude

In your `src/main.rs`:

```rust
use wip_rust::prelude::*;
```

The prelude includes all commonly used types and functions.

## Quick Start

Let's create your first WIP application:

```rust
use wip_rust::prelude::*;

fn main() -> Result<(), Box<dyn std::error::Error>> {
    // Create a weather client
    let client = WeatherClient::new("127.0.0.1:4110");
    
    // Get weather for Tokyo
    let weather_data = client.get_weather_by_coordinates(
        35.6812,    // Tokyo latitude
        139.7671,   // Tokyo longitude
        true,       // include weather info
        true,       // include temperature
        false,      // exclude precipitation
        false,      // exclude alerts
        false,      // exclude disaster info
        0           // current day (0 = today)
    )?;
    
    println!("Weather data received: {:?}", weather_data);
    Ok(())
}
```

Run your application:
```bash
cargo run
```

## Understanding WIP Concepts

### Core Components

WIP consists of several types of servers and clients:

1. **Weather Server (Port 4110)**: Main proxy server that routes requests
2. **Location Server (Port 4109)**: Converts coordinates to area codes  
3. **Query Server (Port 4111)**: Direct weather data queries
4. **Report Server (Port 4112)**: Accepts sensor data and reports

### Data Flow

```
Coordinates → Location Server → Area Code
Area Code → Query Server → Weather Data
Sensor Data → Report Server → Report ID
```

### Area Codes

WIP uses 6-digit area codes based on Japan Meteorological Agency (JMA) regions:
- 130010: Tokyo
- 270000: Osaka
- 400010: Fukuoka
- etc.

## Basic Weather Requests

### Simple Weather Query

```rust
use wip_rust::prelude::*;

fn simple_weather() -> Result<(), Box<dyn std::error::Error>> {
    let client = WeatherClient::new("127.0.0.1:4110");
    
    // Request basic weather information
    let weather_data = client.get_weather_by_coordinates(
        35.6812, 139.7671,  // Tokyo coordinates
        true,  // weather conditions
        true,  // temperature
        false, // precipitation (not needed)
        false, // alerts (not needed)
        false, // disasters (not needed) 
        0      // today
    )?;
    
    // Process the result
    if let Some(area_code) = weather_data.get("area_code") {
        println!("Area Code: {}", area_code);
    }
    
    if let Some(weather_code) = weather_data.get("weather_code") {
        match *weather_code as u32 {
            100..=199 => println!("Clear skies"),
            200..=299 => println!("Cloudy conditions"),
            300..=399 => println!("Rain expected"),
            _ => println!("Weather code: {}", weather_code),
        }
    }
    
    Ok(())
}
```

### Detailed Weather Query

```rust
use wip_rust::prelude::*;

fn detailed_weather() -> Result<(), Box<dyn std::error::Error>> {
    let client = WeatherClient::new("127.0.0.1:4110");
    
    // Request comprehensive weather information
    let weather_data = client.get_weather_by_coordinates(
        35.6812, 139.7671,  // Tokyo coordinates
        true,  // weather conditions
        true,  // temperature
        true,  // precipitation
        true,  // alerts
        true,  // disaster warnings
        1      // tomorrow's forecast
    )?;
    
    println!("=== Weather Report ===");
    
    // Display available data
    for (key, value) in &weather_data {
        match key.as_str() {
            "area_code" => println!("Area: {}", value),
            "temperature" => println!("Temperature: {}°C", value),
            "weather_code" => {
                let code = *value as u32;
                let description = match code {
                    100..=199 => "Clear",
                    200..=299 => "Cloudy", 
                    300..=399 => "Rainy",
                    400..=499 => "Snow",
                    _ => "Other",
                };
                println!("Weather: {} ({})", description, code);
            },
            "precipitation" => println!("Precipitation: {}mm", value),
            _ => println!("{}: {}", key, value),
        }
    }
    
    Ok(())
}
```

## Location Resolution

Sometimes you need to work with area codes directly:

```rust
use wip_rust::prelude::*;

fn location_resolution() -> Result<(), Box<dyn std::error::Error>> {
    let location_client = LocationClient::new("127.0.0.1:4109");
    
    // Define some Japanese cities
    let cities = vec![
        (35.6812, 139.7671, "Tokyo"),
        (34.6937, 135.5023, "Osaka"),
        (35.0116, 135.7681, "Kyoto"),
        (43.0642, 141.3469, "Sapporo"),
    ];
    
    println!("=== Location Resolution ===");
    
    for (lat, lng, city_name) in cities {
        match location_client.resolve_coordinates(lat, lng) {
            Ok(area_code) => {
                println!("{}: {} (area code: {})", city_name, 
                        format!("{:.4}, {:.4}", lat, lng), area_code);
            },
            Err(e) => {
                println!("{}: Failed to resolve location ({})", city_name, e);
            }
        }
    }
    
    Ok(())
}
```

### Using Area Codes for Direct Queries

```rust
use wip_rust::prelude::*;

fn direct_query() -> Result<(), Box<dyn std::error::Error>> {
    let query_client = QueryClient::new("127.0.0.1:4111");
    
    // Query weather data directly by area code
    let weather_json = query_client.query_weather_data(
        "130010", // Tokyo area code
        "weather,temperature,humidity,pressure"
    )?;
    
    println!("Raw weather data: {}", weather_json);
    
    // Parse JSON if server returns JSON format
    if let Ok(json) = serde_json::from_str::<serde_json::Value>(&weather_json) {
        println!("=== Parsed Weather Data ===");
        if let Some(temp) = json["temperature"].as_f64() {
            println!("Temperature: {}°C", temp);
        }
        if let Some(humidity) = json["humidity"].as_u64() {
            println!("Humidity: {}%", humidity);
        }
        if let Some(pressure) = json["pressure"].as_f64() {
            println!("Pressure: {} hPa", pressure);
        }
    }
    
    Ok(())
}
```

## Error Handling

Proper error handling is crucial for robust applications:

```rust
use wip_rust::prelude::*;

fn robust_weather_request(lat: f64, lng: f64) -> Result<(), Box<dyn std::error::Error>> {
    let client = WeatherClient::new("127.0.0.1:4110");
    
    match client.get_weather_by_coordinates(lat, lng, true, true, false, false, false, 0) {
        Ok(weather_data) => {
            println!("Weather data retrieved successfully");
            println!("Data: {:?}", weather_data);
        },
        Err(e) => {
            // Handle different types of errors
            let error_message = e.to_string();
            
            if error_message.contains("timeout") {
                println!("Request timed out - the server may be busy");
                println!("Try again later or check your network connection");
            } else if error_message.contains("connection") {
                println!("Could not connect to server");
                println!("Please verify the server address and port");
            } else if error_message.contains("checksum") {
                println!("Data corruption detected");
                println!("This may indicate a network issue or security problem");
            } else {
                println!("Unexpected error occurred: {}", e);
            }
            
            return Err(e);
        }
    }
    
    Ok(())
}

fn main() {
    // Test error handling with valid coordinates
    match robust_weather_request(35.6812, 139.7671) {
        Ok(_) => println!("Request completed successfully"),
        Err(_) => println!("Request failed - see error details above"),
    }
}
```

### Implementing Retry Logic

```rust
use wip_rust::prelude::*;
use std::time::Duration;

fn weather_with_retry(lat: f64, lng: f64) -> Result<std::collections::HashMap<String, u128>, Box<dyn std::error::Error>> {
    let client = WeatherClient::new("127.0.0.1:4110");
    let max_attempts = 3;
    let mut attempt = 1;
    
    loop {
        println!("Attempt {} of {}", attempt, max_attempts);
        
        match client.get_weather_by_coordinates(lat, lng, true, true, false, false, false, 0) {
            Ok(data) => {
                println!("Success on attempt {}", attempt);
                return Ok(data);
            },
            Err(e) => {
                if attempt >= max_attempts {
                    println!("All attempts failed");
                    return Err(e);
                }
                
                println!("Attempt {} failed: {}", attempt, e);
                println!("Retrying in {} seconds...", attempt);
                
                std::thread::sleep(Duration::from_secs(attempt as u64));
                attempt += 1;
            }
        }
    }
}
```

## Working with Different Data Types

### Processing Weather Codes

```rust
use wip_rust::prelude::*;

fn interpret_weather_codes() -> Result<(), Box<dyn std::error::Error>> {
    let client = WeatherClient::new("127.0.0.1:4110");
    let weather_data = client.get_weather_by_coordinates(35.6812, 139.7671, true, true, true, false, false, 0)?;
    
    if let Some(weather_code) = weather_data.get("weather_code") {
        let code = *weather_code as u32;
        
        let (condition, description) = match code {
            100 => ("Clear", "Sunny skies"),
            101 => ("Clear", "Partly cloudy"),
            200 => ("Cloudy", "Overcast"),
            201 => ("Cloudy", "Mostly cloudy"),
            300 => ("Rain", "Light rain"),
            301 => ("Rain", "Moderate rain"),
            302 => ("Rain", "Heavy rain"),
            400 => ("Snow", "Light snow"),
            401 => ("Snow", "Heavy snow"),
            _ => ("Unknown", "Weather condition unknown"),
        };
        
        println!("Weather: {} - {}", condition, description);
        println!("Weather code: {}", code);
    }
    
    Ok(())
}
```

### Working with Timestamps

```rust
use wip_rust::prelude::*;
use std::time::{SystemTime, UNIX_EPOCH};

fn weather_with_timing() -> Result<(), Box<dyn std::error::Error>> {
    let client = WeatherClient::new("127.0.0.1:4110");
    
    // Record request time
    let start_time = SystemTime::now();
    
    let weather_data = client.get_weather_by_coordinates(
        35.6812, 139.7671, true, true, false, false, false, 0
    )?;
    
    let elapsed = start_time.elapsed()?;
    
    println!("=== Request Timing ===");
    println!("Request took: {:?}", elapsed);
    
    // Check if response includes timestamp
    if let Some(timestamp) = weather_data.get("timestamp") {
        let timestamp_secs = *timestamp as u64;
        println!("Server timestamp: {}", timestamp_secs);
        
        // Compare with current time
        let current_timestamp = SystemTime::now()
            .duration_since(UNIX_EPOCH)?
            .as_secs();
        
        let age = current_timestamp.saturating_sub(timestamp_secs);
        println!("Data age: {} seconds", age);
        
        if age > 300 { // 5 minutes
            println!("Warning: Weather data is older than 5 minutes");
        }
    }
    
    Ok(())
}
```

## Building a Complete Weather Application

Let's combine everything into a complete weather application:

```rust
use wip_rust::prelude::*;
use std::io::{self, Write};

struct WeatherApp {
    weather_client: WeatherClient,
    location_client: LocationClient,
}

impl WeatherApp {
    fn new() -> Self {
        Self {
            weather_client: WeatherClient::new("127.0.0.1:4110"),
            location_client: LocationClient::new("127.0.0.1:4109"),
        }
    }
    
    fn get_weather_for_city(&self, lat: f64, lng: f64, city_name: &str) -> Result<(), Box<dyn std::error::Error>> {
        println!("\n=== Weather Report for {} ===", city_name);
        println!("Coordinates: {:.4}, {:.4}", lat, lng);
        
        // Step 1: Resolve area code
        print!("Resolving area code... ");
        io::stdout().flush()?;
        
        let area_code = self.location_client.resolve_coordinates(lat, lng)?;
        println!("✓ Area code: {}", area_code);
        
        // Step 2: Get weather data
        print!("Fetching weather data... ");
        io::stdout().flush()?;
        
        let weather_data = self.weather_client.get_weather_by_coordinates(
            lat, lng, true, true, true, true, false, 0
        )?;
        println!("✓ Data received");
        
        // Step 3: Display results
        self.display_weather_data(&weather_data)?;
        
        Ok(())
    }
    
    fn display_weather_data(&self, data: &std::collections::HashMap<String, u128>) -> Result<(), Box<dyn std::error::Error>> {
        println!("\n📊 Current Weather:");
        
        for (key, value) in data {
            match key.as_str() {
                "temperature" => println!("  🌡️  Temperature: {}°C", value),
                "weather_code" => {
                    let code = *value as u32;
                    let emoji = match code {
                        100..=199 => "☀️",
                        200..=299 => "☁️",
                        300..=399 => "🌧️",
                        400..=499 => "❄️",
                        _ => "❓",
                    };
                    println!("  {}  Weather code: {}", emoji, code);
                },
                "precipitation" => {
                    if *value > 0 {
                        println!("  💧 Precipitation: {}mm", value);
                    }
                },
                "humidity" => println!("  💨 Humidity: {}%", value),
                "pressure" => println!("  🔽 Pressure: {} hPa", value),
                _ => println!("  📋 {}: {}", key, value),
            }
        }
        
        Ok(())
    }
    
    fn run_interactive(&self) -> Result<(), Box<dyn std::error::Error>> {
        println!("🌤️  WIP Weather Application");
        println!("============================");
        
        let cities = vec![
            (35.6812, 139.7671, "Tokyo"),
            (34.6937, 135.5023, "Osaka"),
            (35.0116, 135.7681, "Kyoto"),
            (43.0642, 141.3469, "Sapporo"),
            (33.5904, 130.4017, "Fukuoka"),
        ];
        
        for (i, (lat, lng, city)) in cities.iter().enumerate() {
            println!("{}. {}", i + 1, city);
        }
        println!("6. Exit");
        
        loop {
            print!("\nSelect a city (1-6): ");
            io::stdout().flush()?;
            
            let mut input = String::new();
            io::stdin().read_line(&mut input)?;
            
            match input.trim() {
                "1" => self.get_weather_for_city(35.6812, 139.7671, "Tokyo")?,
                "2" => self.get_weather_for_city(34.6937, 135.5023, "Osaka")?,
                "3" => self.get_weather_for_city(35.0116, 135.7681, "Kyoto")?,
                "4" => self.get_weather_for_city(43.0642, 141.3469, "Sapporo")?,
                "5" => self.get_weather_for_city(33.5904, 130.4017, "Fukuoka")?,
                "6" => {
                    println!("Goodbye! 👋");
                    break;
                },
                _ => println!("Invalid selection. Please enter 1-6."),
            }
        }
        
        Ok(())
    }
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let app = WeatherApp::new();
    app.run_interactive()
}
```

## Next Steps

Congratulations! You've learned the basics of the WIP Rust library. Here's what you can explore next:

### Advanced Features
- **Async Clients**: Use `AsyncWeatherClient` for high-performance concurrent operations
- **Disaster Reporting**: Submit sensor data with `ReportClient`
- **Caching**: Implement smart caching for better performance
- **Authentication**: Secure your applications with WIP authentication

### Performance Optimization
- **Connection Pooling**: Use multiple clients for better throughput
- **Error Recovery**: Implement circuit breakers and retry strategies
- **Monitoring**: Add health checks and metrics collection

### Integration
- **Web Applications**: Use with web frameworks like Axum or Warp
- **Database Storage**: Store weather data in databases
- **External APIs**: Combine with other weather data sources

### Learning Resources
- Read `COMPREHENSIVE_EXAMPLES.md` for detailed examples
- Check `FAQ_COMPREHENSIVE.md` for common questions
- Explore the API documentation with `cargo doc --open`
- Study the test files for advanced usage patterns

### Practice Projects
1. **Weather Dashboard**: Build a web interface showing multiple cities
2. **Weather Alerts**: Create a system that monitors weather conditions
3. **Data Collector**: Build a service that collects and stores weather data
4. **Mobile App**: Use the library in a mobile weather application

The WIP Rust library provides a solid foundation for building weather-related applications with performance, reliability, and ease of use. Happy coding! 🦀