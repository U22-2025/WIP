use std::time::Duration;
use std::thread;
use std::sync::{Arc, Mutex};
use wip_rust::wip_common_rs::clients::weather_client::WeatherClient;
use wip_rust::wip_common_rs::clients::location_client::LocationClient;
use wip_rust::wip_common_rs::clients::query_client::QueryClient;
use wip_rust::wip_common_rs::clients::report_client::ReportClient;

mod common;
use common::mock_server::{MockServerCluster, MockServerBuilder};
use common::test_data_generator::{TestDataGenerator, TestScenario};

/// Comprehensive end-to-end integration tests for complete WIP workflows
/// Tests realistic scenarios from client request to server response

#[cfg(test)]
mod comprehensive_end_to_end_tests {
    use super::*;

    // ============================================================================
    // Complete Weather Data Retrieval Workflows
    // ============================================================================

    #[test]
    fn test_complete_weather_lookup_workflow() {
        let mut cluster = MockServerCluster::new().unwrap();
        cluster.start_all();
        
        let ports = cluster.ports();
        thread::sleep(Duration::from_millis(100));
        
        // Simulate complete weather lookup workflow
        let tokyo_lat = 35.6812;
        let tokyo_lng = 139.7671;
        
        // Step 1: Resolve coordinates to area code
        let location_client = LocationClient::new(&format!("127.0.0.1:{}", ports.1));
        let area_code = location_client.resolve_coordinates(tokyo_lat, tokyo_lng);
        
        assert!(area_code.is_ok(), "Location resolution failed: {:?}", area_code);
        let area_code = area_code.unwrap();
        
        // Step 2: Query weather data for the area
        let query_client = QueryClient::new(&format!("127.0.0.1:{}", ports.2));
        let weather_data = query_client.query_weather_data(&area_code.to_string(), "weather,temperature,precipitation");
        
        assert!(weather_data.is_ok(), "Weather query failed: {:?}", weather_data);
        let weather_data = weather_data.unwrap();
        
        // Step 3: Verify weather data format
        assert!(!weather_data.is_empty(), "Weather data should not be empty");
        assert!(weather_data.contains("weather") || weather_data.contains("temperature"), 
               "Weather data should contain expected fields");
        
        // Step 4: Alternative direct weather request
        let weather_client = WeatherClient::new(&format!("127.0.0.1:{}", ports.0));
        let direct_weather = weather_client.get_weather_by_coordinates(
            tokyo_lat, tokyo_lng, true, true, true, false, false, 0
        );
        
        assert!(direct_weather.is_ok(), "Direct weather request failed: {:?}", direct_weather);
        
        cluster.stop_all();
    }

    #[test]
    fn test_disaster_reporting_workflow() {
        let mut cluster = MockServerCluster::new().unwrap();
        cluster.start_all();
        
        let ports = cluster.ports();
        thread::sleep(Duration::from_millis(100));
        
        let report_client = ReportClient::new(&format!("127.0.0.1:{}", ports.3));
        
        // Simulate disaster reporting workflow
        let disaster_scenarios = vec![
            ("earthquake", 7, "Strong earthquake in Tokyo area", 35.6812, 139.7671),
            ("tsunami", 9, "Tsunami warning for coastal areas", 38.2682, 140.8694),
            ("typhoon", 5, "Typhoon approaching Osaka", 34.6937, 135.5023),
        ];
        
        let mut report_ids = Vec::new();
        
        for (disaster_type, severity, description, lat, lng) in disaster_scenarios {
            // Submit disaster report
            let result = report_client.send_sensor_report(
                disaster_type, severity, description, Some(lat), Some(lng)
            );
            
            assert!(result.is_ok(), 
                "Disaster report failed for {}: {:?}", disaster_type, result);
            
            let report_id = result.unwrap();
            assert!(report_id > 0, "Report ID should be positive");
            report_ids.push(report_id);
            
            // Small delay between reports
            thread::sleep(Duration::from_millis(50));
        }
        
        // Verify all reports have unique IDs
        for i in 0..report_ids.len() {
            for j in (i + 1)..report_ids.len() {
                assert_ne!(report_ids[i], report_ids[j], 
                          "Report IDs should be unique: {} vs {}", report_ids[i], report_ids[j]);
            }
        }
        
        cluster.stop_all();
    }

    #[test]
    fn test_multi_region_weather_monitoring() {
        let mut cluster = MockServerCluster::new().unwrap();
        cluster.start_all();
        
        let (weather_port, _, _, _) = cluster.ports();
        thread::sleep(Duration::from_millis(100));
        
        let client = WeatherClient::new(&format!("127.0.0.1:{}", weather_port));
        
        // Monitor weather across multiple Japanese regions
        let regions = vec![
            (35.6812, 139.7671, "Tokyo"),
            (34.6937, 135.5023, "Osaka"),
            (35.0116, 135.7681, "Kyoto"),
            (43.0642, 141.3469, "Sapporo"),
            (33.5904, 130.4017, "Fukuoka"),
        ];
        
        let mut results = Vec::new();
        
        for (lat, lng, city) in regions {
            let result = client.get_weather_by_coordinates(
                lat, lng, true, true, true, true, false, 0
            );
            
            match result {
                Ok(weather_data) => {
                    println!("{}: Weather data received", city);
                    results.push((city, weather_data));
                },
                Err(e) => {
                    println!("{}: Weather request failed: {:?}", city, e);
                }
            }
            
            // Stagger requests
            thread::sleep(Duration::from_millis(100));
        }
        
        // At least half of the regions should return data
        assert!(results.len() >= regions.len() / 2, 
               "Too many regions failed: {}/{} successful", results.len(), regions.len());
        
        cluster.stop_all();
    }

    // ============================================================================
    // Complex Scenario Tests
    // ============================================================================

    #[test]
    fn test_emergency_response_scenario() {
        let mut cluster = MockServerCluster::new().unwrap();
        cluster.start_all();
        
        let ports = cluster.ports();
        thread::sleep(Duration::from_millis(100));
        
        // Simulate emergency response scenario
        let emergency_location = (35.6812, 139.7671); // Tokyo
        
        // Step 1: Emergency detection and reporting
        let report_client = ReportClient::new(&format!("127.0.0.1:{}", ports.3));
        let report_result = report_client.send_sensor_report(
            "earthquake", 
            8, 
            "Major earthquake detected, immediate response required",
            Some(emergency_location.0),
            Some(emergency_location.1)
        );
        
        assert!(report_result.is_ok(), "Emergency report failed: {:?}", report_result);
        let report_id = report_result.unwrap();
        
        // Step 2: Get current weather conditions for emergency response
        let weather_client = WeatherClient::new(&format!("127.0.0.1:{}", ports.0));
        let weather_result = weather_client.get_weather_by_coordinates(
            emergency_location.0, emergency_location.1, 
            true, true, true, true, true, 0 // Request all available data
        );
        
        assert!(weather_result.is_ok(), "Emergency weather request failed: {:?}", weather_result);
        
        // Step 3: Query for additional emergency information
        let query_client = QueryClient::new(&format!("127.0.0.1:{}", ports.2));
        let emergency_query = query_client.query_weather_data(
            "130010", // Tokyo area code
            "alerts,disaster,evacuation,emergency"
        );
        
        assert!(emergency_query.is_ok(), "Emergency query failed: {:?}", emergency_query);
        
        // Step 4: Verify emergency response completed
        println!("Emergency response scenario completed:");
        println!("  Report ID: {}", report_id);
        println!("  Weather data: Available");
        println!("  Emergency info: Available");
        
        cluster.stop_all();
    }

    #[test]
    fn test_sensor_network_simulation() {
        let mut cluster = MockServerCluster::new().unwrap();
        cluster.start_all();
        
        let ports = cluster.ports();
        thread::sleep(Duration::from_millis(100));
        
        // Simulate a network of sensors reporting data
        let report_client = ReportClient::new(&format!("127.0.0.1:{}", ports.3));
        let mut generator = TestDataGenerator::new();
        
        let sensor_locations = vec![
            (35.6812, 139.7671, "Tokyo_Sensor_001"),
            (35.6950, 139.7514, "Tokyo_Sensor_002"),
            (35.6586, 139.7454, "Tokyo_Sensor_003"),
            (35.6681, 139.7506, "Tokyo_Sensor_004"),
            (35.6762, 139.7679, "Tokyo_Sensor_005"),
        ];
        
        let mut successful_reports = 0;
        
        for (lat, lng, sensor_id) in sensor_locations {
            // Each sensor reports different types of data
            let sensor_data_types = vec![
                ("temperature", 1, format!("Normal temperature reading from {}", sensor_id)),
                ("humidity", 2, format!("Humidity monitoring from {}", sensor_id)),
                ("seismic", 3, format!("Seismic activity monitoring from {}", sensor_id)),
            ];
            
            for (data_type, severity, description) in sensor_data_types {
                let result = report_client.send_sensor_report(
                    data_type, severity, &description, Some(lat), Some(lng)
                );
                
                match result {
                    Ok(report_id) => {
                        successful_reports += 1;
                        println!("{}: Report {} submitted successfully", sensor_id, report_id);
                    },
                    Err(e) => {
                        println!("{}: Report failed: {:?}", sensor_id, e);
                    }
                }
                
                // Stagger sensor reports
                thread::sleep(Duration::from_millis(25));
            }
        }
        
        // Most sensor reports should succeed
        let total_reports = sensor_locations.len() * 3;
        assert!(successful_reports >= total_reports * 3 / 4, 
               "Too many sensor reports failed: {}/{} successful", 
               successful_reports, total_reports);
        
        cluster.stop_all();
    }

    #[test]
    fn test_data_consistency_across_servers() {
        let mut cluster = MockServerCluster::new().unwrap();
        cluster.start_all();
        
        let ports = cluster.ports();
        thread::sleep(Duration::from_millis(100));
        
        let location_client = LocationClient::new(&format!("127.0.0.1:{}", ports.1));
        let query_client = QueryClient::new(&format!("127.0.0.1:{}", ports.2));
        let weather_client = WeatherClient::new(&format!("127.0.0.1:{}", ports.0));
        
        let test_coordinates = (35.6812, 139.7671); // Tokyo
        
        // Get area code from location server
        let area_code_result = location_client.resolve_coordinates(
            test_coordinates.0, test_coordinates.1
        );
        
        if let Ok(area_code) = area_code_result {
            // Query weather data directly
            let direct_weather = query_client.query_weather_data(
                &area_code.to_string(), "weather,temperature"
            );
            
            // Get weather data via coordinate lookup
            let coordinate_weather = weather_client.get_weather_by_coordinates(
                test_coordinates.0, test_coordinates.1, true, true, false, false, false, 0
            );
            
            // Both methods should succeed
            assert!(direct_weather.is_ok(), "Direct weather query failed");
            assert!(coordinate_weather.is_ok(), "Coordinate weather query failed");
            
            // Data should be consistent (both should contain weather information)
            let direct_data = direct_weather.unwrap();
            let coordinate_data = coordinate_weather.unwrap();
            
            assert!(!direct_data.is_empty(), "Direct weather data should not be empty");
            
            // Coordinate-based query should return area code
            if let Some(returned_area_code) = coordinate_data.get("area_code") {
                // Area codes should match
                assert_eq!(*returned_area_code as u32, area_code, 
                          "Area codes should match between queries");
            }
        }
        
        cluster.stop_all();
    }

    // ============================================================================
    // Load and Stress Testing Scenarios
    // ============================================================================

    #[test]
    fn test_high_volume_scenario() {
        let mut cluster = MockServerCluster::new().unwrap();
        cluster.start_all();
        
        let ports = cluster.ports();
        thread::sleep(Duration::from_millis(100));
        
        let weather_client = WeatherClient::new(&format!("127.0.0.1:{}", ports.0));
        let report_client = ReportClient::new(&format!("127.0.0.1:{}", ports.3));
        
        let mut generator = TestDataGenerator::new();
        
        let mut weather_requests = 0;
        let mut weather_successes = 0;
        let mut report_requests = 0;
        let mut report_successes = 0;
        
        // High volume mixed operations
        for i in 0..100 {
            // Alternate between weather requests and reports
            if i % 2 == 0 {
                weather_requests += 1;
                let (lat, lng) = generator.random_coordinates();
                
                match weather_client.get_weather_by_coordinates(
                    lat, lng, true, false, false, false, false, 0
                ) {
                    Ok(_) => weather_successes += 1,
                    Err(_) => {},
                }
            } else {
                report_requests += 1;
                let disaster_type = generator.random_disaster_type();
                let severity = generator.random_severity();
                let description = generator.random_disaster_description(disaster_type);
                
                match report_client.send_sensor_report(
                    disaster_type, severity, &description, None, None
                ) {
                    Ok(_) => report_successes += 1,
                    Err(_) => {},
                }
            }
            
            // Small delay to prevent overwhelming
            if i % 10 == 0 {
                thread::sleep(Duration::from_millis(50));
            }
        }
        
        println!("High volume test results:");
        println!("  Weather: {}/{} successful", weather_successes, weather_requests);
        println!("  Reports: {}/{} successful", report_successes, report_requests);
        
        // At least 70% should succeed under high volume
        let weather_success_rate = weather_successes as f64 / weather_requests as f64;
        let report_success_rate = report_successes as f64 / report_requests as f64;
        
        assert!(weather_success_rate > 0.7, 
               "Weather success rate too low: {:.2}%", weather_success_rate * 100.0);
        assert!(report_success_rate > 0.7, 
               "Report success rate too low: {:.2}%", report_success_rate * 100.0);
        
        cluster.stop_all();
    }

    #[test]
    fn test_concurrent_different_operations() {
        let mut cluster = MockServerCluster::new().unwrap();
        cluster.start_all();
        
        let ports = cluster.ports();
        thread::sleep(Duration::from_millis(100));
        
        let weather_port = ports.0;
        let location_port = ports.1;
        let query_port = ports.2;
        let report_port = ports.3;
        
        // Spawn threads for different types of operations
        let handles = vec![
            // Weather requests thread
            thread::spawn(move || {
                let client = WeatherClient::new(&format!("127.0.0.1:{}", weather_port));
                let mut successes = 0;
                
                for i in 0..20 {
                    let lat = 35.0 + (i as f64 * 0.01);
                    let lng = 139.0 + (i as f64 * 0.01);
                    
                    if client.get_weather_by_coordinates(lat, lng, true, false, false, false, false, 0).is_ok() {
                        successes += 1;
                    }
                    thread::sleep(Duration::from_millis(25));
                }
                successes
            }),
            
            // Location resolution thread
            thread::spawn(move || {
                let client = LocationClient::new(&format!("127.0.0.1:{}", location_port));
                let mut successes = 0;
                
                for i in 0..20 {
                    let lat = 34.0 + (i as f64 * 0.01);
                    let lng = 135.0 + (i as f64 * 0.01);
                    
                    if client.resolve_coordinates(lat, lng).is_ok() {
                        successes += 1;
                    }
                    thread::sleep(Duration::from_millis(25));
                }
                successes
            }),
            
            // Query requests thread
            thread::spawn(move || {
                let client = QueryClient::new(&format!("127.0.0.1:{}", query_port));
                let mut successes = 0;
                
                for i in 0..20 {
                    let area_code = format!("13{:04}", i);
                    
                    if client.query_weather_data(&area_code, "weather").is_ok() {
                        successes += 1;
                    }
                    thread::sleep(Duration::from_millis(25));
                }
                successes
            }),
            
            // Report submissions thread
            thread::spawn(move || {
                let client = ReportClient::new(&format!("127.0.0.1:{}", report_port));
                let mut successes = 0;
                
                for i in 0..20 {
                    let description = format!("Test report {}", i);
                    
                    if client.send_sensor_report("test", 1, &description, None, None).is_ok() {
                        successes += 1;
                    }
                    thread::sleep(Duration::from_millis(25));
                }
                successes
            }),
        ];
        
        // Collect results
        let mut total_successes = 0;
        let mut total_requests = 0;
        
        for handle in handles {
            let successes = handle.join().unwrap();
            total_successes += successes;
            total_requests += 20;
        }
        
        let overall_success_rate = total_successes as f64 / total_requests as f64;
        
        println!("Concurrent operations test:");
        println!("  Total successes: {}/{}", total_successes, total_requests);
        println!("  Success rate: {:.2}%", overall_success_rate * 100.0);
        
        // Should handle concurrent different operations well
        assert!(overall_success_rate > 0.8, 
               "Concurrent operations success rate too low: {:.2}%", 
               overall_success_rate * 100.0);
        
        cluster.stop_all();
    }

    #[test]
    fn test_realistic_usage_pattern() {
        let mut cluster = MockServerCluster::new().unwrap();
        cluster.start_all();
        
        let ports = cluster.ports();
        thread::sleep(Duration::from_millis(100));
        
        // Simulate realistic usage pattern over time
        let weather_client = WeatherClient::new(&format!("127.0.0.1:{}", ports.0));
        let report_client = ReportClient::new(&format!("127.0.0.1:{}", ports.3));
        
        let mut generator = TestDataGenerator::new();
        
        // Simulate typical daily usage pattern
        for hour in 0..24 {
            // Peak hours (6-9 AM, 5-8 PM) have more requests
            let request_count = if (6..=9).contains(&hour) || (17..=20).contains(&hour) {
                10 // Peak hours
            } else if (22..=5).contains(&hour) {
                2  // Night hours
            } else {
                5  // Normal hours
            };
            
            for _ in 0..request_count {
                // 80% weather requests, 15% reports, 5% other
                let operation_type = generator.random_coordinates().0 as u32 % 100;
                
                if operation_type < 80 {
                    // Weather request
                    let (lat, lng) = generator.random_coordinates();
                    let _ = weather_client.get_weather_by_coordinates(
                        lat, lng, true, true, false, false, false, 0
                    );
                } else if operation_type < 95 {
                    // Sensor report
                    let disaster_type = if operation_type < 85 { "temperature" } else { "earthquake" };
                    let severity = if disaster_type == "temperature" { 1 } else { generator.random_severity() };
                    let description = generator.random_disaster_description(disaster_type);
                    
                    let _ = report_client.send_sensor_report(
                        disaster_type, severity, &description, None, None
                    );
                }
                
                // Realistic delay between requests
                thread::sleep(Duration::from_millis(100));
            }
            
            // Brief pause between "hours"
            thread::sleep(Duration::from_millis(50));
        }
        
        // Check server statistics
        let stats = cluster.total_stats();
        
        println!("Realistic usage pattern completed:");
        println!("  Total requests processed: {}", stats.requests_received);
        println!("  Total responses sent: {}", stats.responses_sent);
        println!("  Total data transferred: {} bytes", stats.bytes_received + stats.bytes_sent);
        
        // Should have processed a reasonable number of requests
        assert!(stats.requests_received > 100, 
               "Too few requests processed: {}", stats.requests_received);
        
        cluster.stop_all();
    }
}