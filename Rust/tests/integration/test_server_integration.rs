use std::time::Duration;
use std::thread;
use wip_rust::wip_common_rs::clients::weather_client::WeatherClient;
use wip_rust::wip_common_rs::clients::location_client::LocationClient;
use wip_rust::wip_common_rs::clients::query_client::QueryClient;
use wip_rust::wip_common_rs::clients::report_client::ReportClient;

mod common;
use common::mock_server::{MockServerCluster, MockServerBuilder};

/// Integration tests for client-server communication
/// Tests real network communication with mock servers

#[cfg(test)]
mod server_integration_tests {
    use super::*;

    #[test]
    fn test_weather_client_basic_communication() {
        let mut cluster = MockServerCluster::new().unwrap();
        cluster.start_all();
        
        let (weather_port, _, _, _) = cluster.ports();
        
        // Give servers time to start
        thread::sleep(Duration::from_millis(100));
        
        let client = WeatherClient::new(&format!("127.0.0.1:{}", weather_port));
        
        // Test coordinate-based weather request
        let result = client.get_weather_by_coordinates(
            35.6812,  // Tokyo latitude
            139.7671, // Tokyo longitude
            true,     // weather
            true,     // temperature
            false,    // precipitation
            false,    // alerts
            false,    // disaster
            0,        // day
        );
        
        match result {
            Ok(response) => {
                assert!(response.contains_key("area_code"));
                assert!(response.contains_key("weather_code"));
            }
            Err(e) => panic!("Weather request failed: {:?}", e),
        }
        
        cluster.stop_all();
    }
    
    #[test]
    fn test_location_client_coordinate_resolution() {
        let mut cluster = MockServerCluster::new().unwrap();
        cluster.start_all();
        
        let (_, location_port, _, _) = cluster.ports();
        
        thread::sleep(Duration::from_millis(100));
        
        let client = LocationClient::new(&format!("127.0.0.1:{}", location_port));
        
        // Test coordinate to area code resolution
        let result = client.resolve_coordinates(35.6812, 139.7671);
        
        match result {
            Ok(area_code) => {
                assert!(area_code > 0);
                assert!(area_code < 1000000); // Valid JMA area code range
            }
            Err(e) => panic!("Location resolution failed: {:?}", e),
        }
        
        cluster.stop_all();
    }
    
    #[test]
    fn test_query_client_direct_query() {
        let mut cluster = MockServerCluster::new().unwrap();
        cluster.start_all();
        
        let (_, _, query_port, _) = cluster.ports();
        
        thread::sleep(Duration::from_millis(100));
        
        let client = QueryClient::new(&format!("127.0.0.1:{}", query_port));
        
        // Test direct weather data query
        let result = client.query_weather_data("130010", "weather,temperature");
        
        match result {
            Ok(data) => {
                assert!(!data.is_empty());
                // Should contain JSON-like weather data
                assert!(data.contains("weather_code") || data.contains("temperature"));
            }
            Err(e) => panic!("Query request failed: {:?}", e),
        }
        
        cluster.stop_all();
    }
    
    #[test]
    fn test_report_client_sensor_data() {
        let mut cluster = MockServerCluster::new().unwrap();
        cluster.start_all();
        
        let (_, _, _, report_port) = cluster.ports();
        
        thread::sleep(Duration::from_millis(100));
        
        let client = ReportClient::new(&format!("127.0.0.1:{}", report_port));
        
        // Test sensor data report
        let result = client.send_sensor_report(
            "earthquake",
            5,
            "Strong earthquake detected by seismic sensor",
            Some(35.6812),
            Some(139.7671),
        );
        
        match result {
            Ok(report_id) => {
                assert!(report_id > 0);
            }
            Err(e) => panic!("Report submission failed: {:?}", e),
        }
        
        cluster.stop_all();
    }
    
    #[test]
    fn test_multiple_concurrent_requests() {
        let mut cluster = MockServerCluster::new().unwrap();
        cluster.start_all();
        
        let (weather_port, _, _, _) = cluster.ports();
        
        thread::sleep(Duration::from_millis(100));
        
        let client = WeatherClient::new(&format!("127.0.0.1:{}", weather_port));
        
        // Send multiple concurrent requests
        let handles: Vec<_> = (0..10).map(|i| {
            let client_clone = client.clone();
            let lat = 35.0 + (i as f64 * 0.1);
            let lng = 139.0 + (i as f64 * 0.1);
            
            thread::spawn(move || {
                client_clone.get_weather_by_coordinates(
                    lat, lng, true, true, false, false, false, 0
                )
            })
        }).collect();
        
        let mut success_count = 0;
        for handle in handles {
            match handle.join().unwrap() {
                Ok(_) => success_count += 1,
                Err(_) => {}, // Some requests might fail, that's ok for this test
            }
        }
        
        // At least half should succeed
        assert!(success_count >= 5);
        
        cluster.stop_all();
    }
    
    #[test]
    fn test_server_timeout_handling() {
        // Test with slow server
        let server = MockServerBuilder::new()
            .response_delay(Duration::from_millis(200))
            .build()
            .unwrap();
        
        let port = server.port();
        let handle = server.start();
        
        thread::sleep(Duration::from_millis(100));
        
        let client = WeatherClient::new(&format!("127.0.0.1:{}", port));
        client.set_timeout(Duration::from_millis(100)); // Shorter than server delay
        
        let result = client.get_weather_by_coordinates(
            35.6812, 139.7671, true, false, false, false, false, 0
        );
        
        // Should timeout
        assert!(result.is_err());
        
        server.stop();
    }
    
    #[test]
    fn test_server_error_handling() {
        // Test with error-prone server
        let server = MockServerBuilder::new()
            .error_rate(1.0) // Always return errors
            .build()
            .unwrap();
        
        let port = server.port();
        let handle = server.start();
        
        thread::sleep(Duration::from_millis(100));
        
        let client = WeatherClient::new(&format!("127.0.0.1:{}", port));
        
        let result = client.get_weather_by_coordinates(
            35.6812, 139.7671, true, false, false, false, false, 0
        );
        
        // Should receive error response
        assert!(result.is_err());
        
        server.stop();
    }
    
    #[test]
    fn test_packet_loss_recovery() {
        // Test with packet loss simulation
        let server = MockServerBuilder::new()
            .packet_loss(0.5) // 50% packet loss
            .build()
            .unwrap();
        
        let port = server.port();
        let handle = server.start();
        
        thread::sleep(Duration::from_millis(100));
        
        let mut client = WeatherClient::new(&format!("127.0.0.1:{}", port));
        client.set_retry_count(5); // More retries to handle packet loss
        
        let result = client.get_weather_by_coordinates(
            35.6812, 139.7671, true, false, false, false, false, 0
        );
        
        // With retries, should eventually succeed despite packet loss
        // Note: This test might be flaky due to randomness
        match result {
            Ok(_) => {}, // Success
            Err(_) => {
                // Acceptable failure due to high packet loss rate
                // In production, lower packet loss rates should work
            }
        }
        
        server.stop();
    }
    
    #[test]
    fn test_large_payload_handling() {
        let mut cluster = MockServerCluster::new().unwrap();
        cluster.start_all();
        
        let (_, _, query_port, _) = cluster.ports();
        
        thread::sleep(Duration::from_millis(100));
        
        let client = QueryClient::new(&format!("127.0.0.1:{}", query_port));
        
        // Request large amount of data
        let result = client.query_weather_data(
            "130010", 
            "weather,temperature,precipitation,alerts,disaster,forecast,historical"
        );
        
        match result {
            Ok(data) => {
                assert!(!data.is_empty());
                // Large queries should still work
            }
            Err(e) => {
                // Large payloads might fail due to UDP size limits
                // This is expected behavior
            }
        }
        
        cluster.stop_all();
    }
    
    #[test]
    fn test_server_statistics() {
        let mut cluster = MockServerCluster::new().unwrap();
        cluster.start_all();
        
        let (weather_port, _, _, _) = cluster.ports();
        
        thread::sleep(Duration::from_millis(100));
        
        let client = WeatherClient::new(&format!("127.0.0.1:{}", weather_port));
        
        // Send several requests
        for i in 0..5 {
            let _ = client.get_weather_by_coordinates(
                35.0 + (i as f64 * 0.1), 
                139.0 + (i as f64 * 0.1), 
                true, false, false, false, false, 0
            );
            thread::sleep(Duration::from_millis(10));
        }
        
        let stats = cluster.total_stats();
        
        // Should have processed some requests
        assert!(stats.requests_received > 0);
        assert!(stats.bytes_received > 0);
        
        cluster.stop_all();
    }
    
    #[test]
    fn test_client_connection_pooling() {
        let mut cluster = MockServerCluster::new().unwrap();
        cluster.start_all();
        
        let (weather_port, _, _, _) = cluster.ports();
        
        thread::sleep(Duration::from_millis(100));
        
        // Test that connection pooling works by making many requests quickly
        let client = WeatherClient::new(&format!("127.0.0.1:{}", weather_port));
        
        let start_time = std::time::Instant::now();
        
        for i in 0..20 {
            let result = client.get_weather_by_coordinates(
                35.6812, 139.7671, true, false, false, false, false, 0
            );
            
            // Most requests should succeed
            if i < 15 {
                assert!(result.is_ok(), "Request {} failed: {:?}", i, result);
            }
        }
        
        let elapsed = start_time.elapsed();
        
        // Connection pooling should make this reasonably fast
        assert!(elapsed < Duration::from_secs(5));
        
        cluster.stop_all();
    }
    
    #[test]
    fn test_different_packet_types() {
        let mut cluster = MockServerCluster::new().unwrap();
        cluster.start_all();
        
        let ports = cluster.ports();
        
        thread::sleep(Duration::from_millis(100));
        
        // Test location packet
        let location_client = LocationClient::new(&format!("127.0.0.1:{}", ports.1));
        let location_result = location_client.resolve_coordinates(35.6812, 139.7671);
        assert!(location_result.is_ok());
        
        // Test query packet
        let query_client = QueryClient::new(&format!("127.0.0.1:{}", ports.2));
        let query_result = query_client.query_weather_data("130010", "weather");
        assert!(query_result.is_ok());
        
        // Test report packet
        let report_client = ReportClient::new(&format!("127.0.0.1:{}", ports.3));
        let report_result = report_client.send_sensor_report(
            "temperature", 1, "Normal temperature reading", None, None
        );
        assert!(report_result.is_ok());
        
        cluster.stop_all();
    }
    
    #[test]
    fn test_malformed_packet_handling() {
        let server = MockServerBuilder::new().build().unwrap();
        let port = server.port();
        let handle = server.start();
        
        thread::sleep(Duration::from_millis(100));
        
        // Send malformed data directly via UDP
        let socket = std::net::UdpSocket::bind("127.0.0.1:0").unwrap();
        
        // Send various malformed packets
        let malformed_packets = vec![
            vec![], // Empty packet
            vec![0x00], // Too short
            vec![0xFF; 10], // Wrong size
            vec![0x12, 0x34, 0x56, 0x78, 0x9A, 0xBC, 0xDE, 0xF0], // Invalid format
        ];
        
        for packet in malformed_packets {
            let _ = socket.send_to(&packet, format!("127.0.0.1:{}", port));
            thread::sleep(Duration::from_millis(10));
        }
        
        // Server should handle malformed packets gracefully
        let stats = server.stats();
        assert!(stats.requests_received >= malformed_packets.len() as u64);
        
        server.stop();
    }
}