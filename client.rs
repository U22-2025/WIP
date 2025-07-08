use std::env;
use std::time;

// Rustディレクトリ以下の構造に合わせてモジュールを参照
use rust_common::clients::utils::packet_id_generator::PacketIDGenerator12Bit;
use rust_common::packet::models::request::{LocationRequest, QueryRequest};

fn main() {
    let args: Vec<String> = env::args().collect();
    let use_coordinates = args.iter().any(|arg| arg == "--coord");
    let use_proxy = args.iter().any(|arg| arg == "--proxy");

    let pidg = PacketIDGenerator12Bit::new();

    if use_proxy {
        println!("Weather Client Example - Via Weather Server (Proxy Mode)");
    } else {
        println!("Weather Client Example - Direct Communication");
    }
    println!("{}", "=".repeat(60));

    if use_coordinates {
        if use_proxy {
            // Weather Server経由での座標リクエスト
            println!("\n1. Coordinate-based request via Weather Server (Proxy)");
            println!("{}", "-".repeat(50));

            let mut client = rust_common::clients::weather_client::WeatherClient::new(true);
            
            let request = LocationRequest::create_coordinate_lookup(
                35.6895,
                139.6917,
                pidg.next_id(),
                true,  // weather
                true,  // temperature
                true,  // precipitation_prob
                true,  // alert
                true,  // disaster
                1      // version
            );
            
            match client.execute_location_request(&request) {
                Ok(result) => {
                    println!("\n✓ Request successful via Weather Server!");
                    println!("=== Received packet content ===");
                    for (key, value) in result {
                        println!("  {}: {}", key, value);
                    }
                    println!("{}", "=".repeat(30));
                },
                Err(e) => println!("\n✗ Request failed: {}", e),
            }
        } else {
            // 直接通信での座標リクエスト
            println!("\n1. Direct coordinate-based request (LocationClient + QueryClient)");
            println!("{}", "-".repeat(65));

            // Step 1: LocationClientで座標からエリアコードを取得
            let mut location_client = rust_common::clients::location_client::LocationClient::new(true, 60); // キャッシュ有効期限60分
            
            let location_request = LocationRequest::create_coordinate_lookup(
                35.6895,
                139.6917,
                pidg.next_id(),
                1  // version
            );

            println!("Step 1: Getting area code from coordinates...");
            let cache_stats = location_client.get_cache_stats();
            println!("Cache stats before request: {:?}", cache_stats);
            println!("Using persistent cache file: {}", cache_stats.get("cache_file").unwrap_or(&"N/A".to_string()));

            let area_code_with_cache_info = location_client.get_area_code_simple(
                35.6895,
                139.6917,
                true,
                true
            );

            if let Ok((area_code, cache_hit)) = area_code_with_cache_info {
                println!("Area code: {} (Cache {})", area_code, if cache_hit { "HIT" } else { "MISS" });
            }

            // 従来のメソッドも実行してレスポンスを取得
            let (location_response, raw_data) = location_client.get_location_data(
                35.6895,
                139.6917,
                true
            ).unwrap();

            println!("Cache stats after request: {:?}", location_client.get_cache_stats());

            if let Some(response) = location_response {
                if response.is_valid() {
                    let area_code = response.get_area_code();
                    let cache_hit = response.cache_hit;
                    println!("✓ Area code obtained: {} (Cache {})", area_code, if cache_hit { "HIT" } else { "MISS" });

                    // キャッシュテスト：同じ座標を再度取得
                    println!("\n--- Cache Test: Getting same coordinates again ---");
                    let (location_response2, raw_data2) = location_client.get_location_data(
                        35.6895,
                        139.6917,
                        true
                    ).unwrap();

                    if let Some(response2) = location_response2 {
                        if response2.is_valid() {
                            let area_code2 = response2.get_area_code();
                            let cache_hit2 = response2.cache_hit;
                            println!("✓ Second request - Area code: {} (Cache {})", 
                                area_code2, if cache_hit2 { "HIT" } else { "MISS" });
                        } else {
                            println!("\n✗ Second request failed");
                        }
                    }

                    // Step 2: QueryClientで天気データを取得
                    println!("\nStep 2: Getting weather data...");
                    let mut query_client = rust_common::clients::query_client::QueryClient::new(true);
                    
                    match query_client.get_weather_data(
                        area_code,
                        true,  // weather
                        true,  // temperature
                        true,  // precipitation_prob
                        true,  // alert
                        true   // disaster
                    ) {
                        Ok(weather_result) => {
                            println!("\n✓ Direct request successful!");
                            println!("=== Received weather data ===");
                            // 座標情報を追加
                            let mut weather_result = weather_result;
                            weather_result.insert("latitude".to_string(), "35.6895".to_string());
                            weather_result.insert("longitude".to_string(), "139.6917".to_string());
                            for (key, value) in weather_result {
                                println!("  {}: {}", key, value);
                            }
                            println!("{}", "=".repeat(30));
                        },
                        Err(e) => println!("\n✗ Weather data request failed: {}", e),
                    }
                } else {
                    println!("\n✗ Failed to get area code from coordinates");
                }
            }
        }
    } else {
        // エリアコード指定の場合
        if use_proxy {
            // Weather Server経由でのエリアコードリクエスト
            println!("\n1. Area code request via Weather Server (Proxy)");
            println!("{}", "-".repeat(45));

            let mut client = rust_common::clients::weather_client::WeatherClient::new(true);
            match client.get_weather_data(
                460010,
                true,  // weather
                true,  // temperature
                true,  // precipitation_prob
                true,  // alert
                true   // disaster
            ) {
                Ok(result) => {
                    println!("\n✓ Success via Weather Server!");
                    if let Some(area_code) = result.get("area_code") {
                        println!("Area Code: {}", area_code);
                    } else if let Some(error_code) = result.get("error_code") {
                        println!("Error Code: {}", error_code);
                    }
                    if let Some(timestamp) = result.get("timestamp") {
                        println!("Timestamp: {}", time::UNIX_EPOCH + time::Duration::from_secs(timestamp.parse().unwrap()));
                    }
                    if let Some(weather_code) = result.get("weather_code") {
                        println!("Weather Code: {}", weather_code);
                    }
                    if let Some(temperature) = result.get("temperature") {
                        println!("Temperature: {}°C", temperature);
                    }
                    if let Some(precipitation_prob) = result.get("precipitation_prob") {
                        println!("precipitation_prob: {}%", precipitation_prob);
                    }
                    if let Some(alert) = result.get("alert") {
                        println!("alert: {}", alert);
                    }
                    if let Some(disaster) = result.get("disaster") {
                        println!("disaster: {}", disaster);
                    }
                },
                Err(e) => println!("\n✗ Failed to get weather data via Weather Server: {}", e),
            }
        } else {
            // 直接QueryClientでのエリアコードリクエスト
            println!("\n1. Direct area code request (QueryClient)");
            println!("{}", "-".repeat(40));

            let mut query_client = rust_common::clients::query_client::QueryClient::new(true);
            match query_client.get_weather_data(
                460010,
                true,  // weather
                true,  // temperature
                true,  // precipitation_prob
                true,  // alert
                true   // disaster
            ) {
                Ok(result) => {
                    println!("\n✓ Direct request successful!");
                    println!("=== Received weather data ===");
                    if let Some(area_code) = result.get("area_code") {
                        println!("Area Code: {}", area_code);
                    } else if let Some(error_code) = result.get("error_code") {
                        println!("Error Code: {}", error_code);
                    }
                    if let Some(timestamp) = result.get("timestamp") {
                        println!("Timestamp: {}", time::UNIX_EPOCH + time::Duration::from_secs(timestamp.parse().unwrap()));
                    }
                    if let Some(weather_code) = result.get("weather_code") {
                        println!("Weather Code: {}", weather_code);
                    }
                    if let Some(temperature) = result.get("temperature") {
                        println!("Temperature: {}°C", temperature);
                    }
                    if let Some(precipitation_prob) = result.get("precipitation_prob") {
                        println!("precipitation_prob: {}%", precipitation_prob);
                    }
                    if let Some(alert) = result.get("alert") {
                        println!("alert: {}", alert);
                    }
                    if let Some(disaster) = result.get("disaster") {
                        println!("disaster: {}", disaster);
                    }
                    println!("{}", "=".repeat(30));
                },
                Err(e) => println!("\n✗ Failed to get weather data: {}", e),
            }
        }
    }
}