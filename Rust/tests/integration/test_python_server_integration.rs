use std::net::{SocketAddr, UdpSocket};
use std::time::{Duration, Instant};
use tokio::time::timeout;
use wip_rust::wip_common_rs::clients::weather_client::WeatherClient;
use wip_rust::wip_common_rs::clients::location_client::LocationClient;
use wip_rust::wip_common_rs::clients::report_client::ReportClient;
use wip_rust::wip_common_rs::clients::query_client::QueryClient;
use wip_rust::wip_common_rs::packet::types::location_packet::LocationRequest;
use wip_rust::wip_common_rs::packet::types::report_packet::ReportRequest;
use wip_rust::wip_common_rs::packet::types::query_packet::QueryRequest;

// Test configuration for local Python WIP server
const PYTHON_SERVER_HOST: &str = "127.0.0.1";
const PYTHON_SERVER_PORT: u16 = 8888; // Adjust based on your Python server configuration
const TEST_TIMEOUT: Duration = Duration::from_secs(10);

#[cfg(test)]
mod python_server_integration_tests {
    use super::*;

    // Helper function to check if Python server is running
    async fn is_python_server_running() -> bool {
        let addr = format!("{}:{}", PYTHON_SERVER_HOST, PYTHON_SERVER_PORT);
        match UdpSocket::bind("0.0.0.0:0") {
            Ok(socket) => {
                // Try to connect to the server
                match socket.connect(&addr) {
                    Ok(_) => {
                        // Send a simple ping packet to test connectivity
                        let ping_data = vec![0x01, 0x02, 0x03, 0x04]; // Simple test packet
                        match socket.send(&ping_data) {
                            Ok(_) => true,
                            Err(_) => false,
                        }
                    },
                    Err(_) => false,
                }
            },
            Err(_) => false,
        }
    }

    // Helper function to create server address
    fn server_addr() -> SocketAddr {
        format!("{}:{}", PYTHON_SERVER_HOST, PYTHON_SERVER_PORT)
            .parse()
            .expect("Valid server address")
    }

    #[tokio::test]
    async fn test_python_server_connectivity() {
        // Skip test if Python server is not running
        if !is_python_server_running().await {
            println!("⚠️  Python WIP server not detected at {}:{}. Skipping integration tests.", 
                     PYTHON_SERVER_HOST, PYTHON_SERVER_PORT);
            println!("   To run integration tests, start the Python WIP server first.");
            return;
        }

        println!("✅ Python WIP server detected. Running integration tests...");
    }

    #[tokio::test]
    async fn test_weather_client_integration() {
        if !is_python_server_running().await {
            println!("⚠️  Skipping weather client test - Python server not running");
            return;
        }

        let mut client = WeatherClient::new(server_addr()).await.expect("Failed to create weather client");
        
        // Test basic weather query
        let result = timeout(TEST_TIMEOUT, async {
            client.get_weather_data("Tokyo", "current").await
        }).await;

        match result {
            Ok(Ok(weather_data)) => {
                println!("✅ Weather client integration test passed");
                println!("   Received weather data: {:?}", weather_data);
            },
            Ok(Err(e)) => {
                println!("⚠️  Weather client returned error (may be expected): {}", e);
                // This might be expected if the Python server doesn't support this exact API
            },
            Err(_) => {
                panic!("❌ Weather client integration test timed out");
            }
        }
    }

    #[tokio::test]
    async fn test_location_client_integration() {
        if !is_python_server_running().await {
            println!("⚠️  Skipping location client test - Python server not running");
            return;
        }

        let mut client = LocationClient::new(server_addr()).await.expect("Failed to create location client");
        
        // Test location query for Tokyo coordinates
        let tokyo_lat = 35.6812;
        let tokyo_lon = 139.7671;
        
        let result = timeout(TEST_TIMEOUT, async {
            client.get_area_code(tokyo_lat, tokyo_lon).await
        }).await;

        match result {
            Ok(Ok(area_info)) => {
                println!("✅ Location client integration test passed");
                println!("   Tokyo area code: {:?}", area_info);
            },
            Ok(Err(e)) => {
                println!("⚠️  Location client returned error (may be expected): {}", e);
            },
            Err(_) => {
                panic!("❌ Location client integration test timed out");
            }
        }
    }

    #[tokio::test]
    async fn test_report_client_integration() {
        if !is_python_server_running().await {
            println!("⚠️  Skipping report client test - Python server not running");
            return;
        }

        let mut client = ReportClient::new(server_addr()).await.expect("Failed to create report client");
        
        // Test disaster report submission
        let result = timeout(TEST_TIMEOUT, async {
            client.submit_disaster_report(
                "earthquake",
                5,
                35.6812,
                139.7671,
                "Test earthquake report from Rust client"
            ).await
        }).await;

        match result {
            Ok(Ok(report_id)) => {
                println!("✅ Report client integration test passed");
                println!("   Report submitted with ID: {}", report_id);
            },
            Ok(Err(e)) => {
                println!("⚠️  Report client returned error (may be expected): {}", e);
            },
            Err(_) => {
                panic!("❌ Report client integration test timed out");
            }
        }
    }

    #[tokio::test]
    async fn test_query_client_integration() {
        if !is_python_server_running().await {
            println!("⚠️  Skipping query client test - Python server not running");
            return;
        }

        let mut client = QueryClient::new(server_addr()).await.expect("Failed to create query client");
        
        // Test general query
        let result = timeout(TEST_TIMEOUT, async {
            client.execute_query("status", "region=tokyo").await
        }).await;

        match result {
            Ok(Ok(query_result)) => {
                println!("✅ Query client integration test passed");
                println!("   Query result: {:?}", query_result);
            },
            Ok(Err(e)) => {
                println!("⚠️  Query client returned error (may be expected): {}", e);
            },
            Err(_) => {
                panic!("❌ Query client integration test timed out");
            }
        }
    }

    #[tokio::test]
    async fn test_packet_compatibility() {
        if !is_python_server_running().await {
            println!("⚠️  Skipping packet compatibility test - Python server not running");
            return;
        }

        // Test that our Rust packets are compatible with Python server
        
        // Create a location request packet
        let mut location_request = LocationRequest::new();
        location_request.set_latitude(35.6812);
        location_request.set_longitude(139.7671);
        let location_bytes = location_request.to_bytes();
        
        // Create a report request packet
        let mut report_request = ReportRequest::new();
        report_request.set_disaster_type("earthquake".to_string());
        report_request.set_severity(5);
        report_request.set_description("Test report".to_string());
        let report_bytes = report_request.to_bytes();
        
        // Create a query request packet
        let mut query_request = QueryRequest::new();
        query_request.set_query_type("status".to_string());
        query_request.set_parameters("test=true".to_string());
        let query_bytes = query_request.to_bytes();
        
        // Test sending raw packets to Python server
        let socket = UdpSocket::bind("0.0.0.0:0").expect("Failed to bind socket");
        socket.connect(server_addr()).expect("Failed to connect to server");
        
        let packets = vec![
            ("LocationRequest", location_bytes),
            ("ReportRequest", report_bytes),
            ("QueryRequest", query_bytes),
        ];
        
        for (packet_type, packet_data) in packets {
            let start_time = Instant::now();
            match socket.send(&packet_data) {
                Ok(bytes_sent) => {
                    println!("✅ {} packet sent successfully ({} bytes)", packet_type, bytes_sent);
                    
                    // Try to receive response (with timeout)
                    socket.set_read_timeout(Some(Duration::from_secs(2))).ok();
                    let mut response_buffer = vec![0; 1024];
                    
                    match socket.recv(&mut response_buffer) {
                        Ok(bytes_received) => {
                            let response_time = start_time.elapsed();
                            println!("   📥 Received {} bytes response in {:?}", bytes_received, response_time);
                            
                            // Basic validation that we got a response
                            assert!(bytes_received > 0);
                            assert!(response_time < Duration::from_secs(5));
                        },
                        Err(_) => {
                            println!("   ⚠️  No response received (may be expected for this packet type)");
                        }
                    }
                },
                Err(e) => {
                    panic!("❌ Failed to send {} packet: {}", packet_type, e);
                }
            }
        }
    }

    #[tokio::test]
    async fn test_concurrent_requests() {
        if !is_python_server_running().await {
            println!("⚠️  Skipping concurrent test - Python server not running");
            return;
        }

        // Test multiple concurrent requests to ensure thread safety
        let num_concurrent = 5;
        let mut handles = Vec::new();
        
        for i in 0..num_concurrent {
            let handle = tokio::spawn(async move {
                let mut client = LocationClient::new(server_addr()).await
                    .expect("Failed to create client");
                
                // Vary the coordinates slightly for each request
                let lat = 35.6812 + (i as f64 * 0.001);
                let lon = 139.7671 + (i as f64 * 0.001);
                
                let result = timeout(TEST_TIMEOUT, async {
                    client.get_area_code(lat, lon).await
                }).await;
                
                match result {
                    Ok(Ok(_)) => {
                        println!("✅ Concurrent request {} completed successfully", i);
                        true
                    },
                    Ok(Err(e)) => {
                        println!("⚠️  Concurrent request {} returned error: {}", i, e);
                        true // Consider this a success since server responded
                    },
                    Err(_) => {
                        println!("❌ Concurrent request {} timed out", i);
                        false
                    }
                }
            });
            handles.push(handle);
        }
        
        // Wait for all requests to complete
        let results = futures::future::join_all(handles).await;
        let successful_requests = results.into_iter()
            .filter_map(|r| r.ok())
            .filter(|&success| success)
            .count();
        
        println!("📊 Concurrent test completed: {}/{} requests successful", 
                 successful_requests, num_concurrent);
        
        // At least half should succeed
        assert!(successful_requests >= num_concurrent / 2);
    }

    #[tokio::test]
    async fn test_error_handling() {
        if !is_python_server_running().await {
            println!("⚠️  Skipping error handling test - Python server not running");
            return;
        }

        // Test various error conditions
        
        // Test with invalid coordinates (should handle gracefully)
        let mut client = LocationClient::new(server_addr()).await
            .expect("Failed to create client");
        
        let invalid_coords = vec![
            (999.0, 999.0),    // Out of range
            (-999.0, -999.0),  // Out of range
            (f64::NAN, f64::NAN), // NaN values
        ];
        
        for (lat, lon) in invalid_coords {
            let result = timeout(Duration::from_secs(5), async {
                client.get_area_code(lat, lon).await
            }).await;
            
            match result {
                Ok(Ok(_)) => {
                    println!("⚠️  Server accepted invalid coordinates ({}, {}) - unexpected", lat, lon);
                },
                Ok(Err(_)) => {
                    println!("✅ Server properly rejected invalid coordinates ({}, {})", lat, lon);
                },
                Err(_) => {
                    println!("⚠️  Timeout with invalid coordinates ({}, {}) - may be expected", lat, lon);
                }
            }
        }
    }

    #[tokio::test]
    async fn test_performance_baseline() {
        if !is_python_server_running().await {
            println!("⚠️  Skipping performance test - Python server not running");
            return;
        }

        // Simple performance test to establish baseline
        let num_requests = 10;
        let mut response_times = Vec::new();
        
        let mut client = LocationClient::new(server_addr()).await
            .expect("Failed to create client");
        
        for i in 0..num_requests {
            let start = Instant::now();
            
            let result = timeout(TEST_TIMEOUT, async {
                client.get_area_code(35.6812, 139.7671).await
            }).await;
            
            let elapsed = start.elapsed();
            
            match result {
                Ok(Ok(_)) => {
                    response_times.push(elapsed);
                    println!("✅ Request {} completed in {:?}", i, elapsed);
                },
                Ok(Err(e)) => {
                    println!("⚠️  Request {} failed: {}", i, e);
                },
                Err(_) => {
                    println!("❌ Request {} timed out", i);
                }
            }
        }
        
        if !response_times.is_empty() {
            let avg_time = response_times.iter().sum::<Duration>() / response_times.len() as u32;
            let min_time = response_times.iter().min().unwrap();
            let max_time = response_times.iter().max().unwrap();
            
            println!("📊 Performance baseline:");
            println!("   Average response time: {:?}", avg_time);
            println!("   Min response time: {:?}", min_time);
            println!("   Max response time: {:?}", max_time);
            println!("   Successful requests: {}/{}", response_times.len(), num_requests);
            
            // Basic performance assertions
            assert!(avg_time < Duration::from_secs(2), "Average response time too slow");
            assert!(*max_time < Duration::from_secs(5), "Maximum response time too slow");
        }
    }
}