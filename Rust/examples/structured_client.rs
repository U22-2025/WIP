/// 新しい構造化されたWIPクライアントの使用例

use wip_rust::prelude::*;

fn main() {
    println!("=== WIP Rust Structured Client Example ===");
    
    // 新しい構造化されたWeatherClientを使用
    let mut client = WeatherClient::new("127.0.0.1", 4110, true)
        .expect("Failed to create weather client");
    
    println!("Connecting to Weather Server...");
    
    match client.get_weather_simple(11000, true, true, true, false, false, 0) {
        Ok(Some(resp)) => {
            println!("\n=== Weather Response ===");
            println!("Version: {}", resp.version);
            println!("Packet ID: {}", resp.packet_id);
            println!("Area Code: {}", resp.area_code);
            
            if let Some(weather_code) = resp.weather_code {
                println!("Weather Code: {}", weather_code);
            }
            
            if let Some(temperature) = resp.temperature {
                println!("Temperature: {}°C", temperature);
            }
            
            if let Some(precipitation) = resp.precipitation {
                println!("Precipitation Probability: {}%", precipitation);
            }
            
            println!("=== Success! ===");
        }
        Ok(None) => println!("No response received"),
        Err(e) => eprintln!("Error: {}", e),
    }
}