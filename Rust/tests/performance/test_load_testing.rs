use std::time::{Duration, Instant};
use std::thread;
use std::sync::{Arc, Mutex};
use wip_rust::wip_common_rs::clients::weather_client::WeatherClient;
use wip_rust::wip_common_rs::clients::location_client::LocationClient;
use wip_rust::wip_common_rs::clients::query_client::QueryClient;
use wip_rust::wip_common_rs::clients::report_client::ReportClient;
use wip_rust::wip_common_rs::packet::types::location_packet::LocationRequest;
use wip_rust::wip_common_rs::packet::core::PacketFormat;

mod common;
use common::mock_server::{MockServerCluster, MockServerBuilder};
use common::test_data_generator::TestDataGenerator;

/// Comprehensive load testing suite for WIP servers and clients
/// Tests system behavior under various load conditions

#[cfg(test)]
mod load_testing_suite {
    use super::*;

    // ============================================================================
    // Single Client Load Tests
    // ============================================================================

    #[test]
    fn test_weather_client_sustained_load() {
        let mut cluster = MockServerCluster::new().unwrap();
        cluster.start_all();
        
        let ports = cluster.ports();
        thread::sleep(Duration::from_millis(100));
        
        let client = WeatherClient::new(&format!("127.0.0.1:{}", ports.0));
        let mut generator = TestDataGenerator::new();
        
        let mut stats = LoadTestStats::new();
        let request_count = 1000;
        
        println!("Starting sustained weather client load test ({} requests)...", request_count);
        
        for i in 0..request_count {
            let start_time = Instant::now();
            let (lat, lng) = generator.random_coordinates();
            
            match client.get_weather_by_coordinates(lat, lng, true, true, false, false, false, 0) {
                Ok(_) => {
                    stats.record_success(start_time.elapsed());
                },
                Err(_) => {
                    stats.record_failure(start_time.elapsed());
                }
            }
            
            // Print progress every 100 requests
            if (i + 1) % 100 == 0 {
                println!("Completed {}/{} requests", i + 1, request_count);
            }
        }
        
        stats.print_summary("Weather Client Sustained Load");
        
        // Performance requirements
        assert!(stats.success_rate() > 0.95, "Success rate too low: {:.2}%", stats.success_rate() * 100.0);
        assert!(stats.average_response_time() < Duration::from_millis(100), 
               "Average response time too high: {:?}", stats.average_response_time());
        assert!(stats.p99_response_time() < Duration::from_millis(500),
               "P99 response time too high: {:?}", stats.p99_response_time());
        
        cluster.stop_all();
    }

    #[test]
    fn test_report_client_bulk_submissions() {
        let mut cluster = MockServerCluster::new().unwrap();
        cluster.start_all();
        
        let ports = cluster.ports();
        thread::sleep(Duration::from_millis(100));
        
        let client = ReportClient::new(&format!("127.0.0.1:{}", ports.3));
        let mut generator = TestDataGenerator::new();
        
        let mut stats = LoadTestStats::new();
        let report_count = 500;
        
        println!("Starting bulk report submission test ({} reports)...", report_count);
        
        for i in 0..report_count {
            let start_time = Instant::now();
            let disaster_type = generator.random_disaster_type();
            let severity = generator.random_severity();
            let description = generator.random_disaster_description(disaster_type);
            let (lat, lng) = generator.random_coordinates();
            
            match client.send_sensor_report(disaster_type, severity, &description, Some(lat), Some(lng)) {
                Ok(_) => {
                    stats.record_success(start_time.elapsed());
                },
                Err(_) => {
                    stats.record_failure(start_time.elapsed());
                }
            }
            
            if (i + 1) % 50 == 0 {
                println!("Submitted {}/{} reports", i + 1, report_count);
            }
        }
        
        stats.print_summary("Report Client Bulk Submissions");
        
        assert!(stats.success_rate() > 0.90, "Success rate too low: {:.2}%", stats.success_rate() * 100.0);
        assert!(stats.average_response_time() < Duration::from_millis(200),
               "Average response time too high: {:?}", stats.average_response_time());
        
        cluster.stop_all();
    }

    #[test]
    fn test_location_client_coordinate_resolution_load() {
        let mut cluster = MockServerCluster::new().unwrap();
        cluster.start_all();
        
        let ports = cluster.ports();
        thread::sleep(Duration::from_millis(100));
        
        let client = LocationClient::new(&format!("127.0.0.1:{}", ports.1));
        let mut generator = TestDataGenerator::new();
        
        let mut stats = LoadTestStats::new();
        let resolution_count = 800;
        
        println!("Starting coordinate resolution load test ({} resolutions)...", resolution_count);
        
        for i in 0..resolution_count {
            let start_time = Instant::now();
            let (lat, lng) = generator.random_coordinates();
            
            match client.resolve_coordinates(lat, lng) {
                Ok(_) => {
                    stats.record_success(start_time.elapsed());
                },
                Err(_) => {
                    stats.record_failure(start_time.elapsed());
                }
            }
            
            if (i + 1) % 80 == 0 {
                println!("Resolved {}/{} coordinates", i + 1, resolution_count);
            }
        }
        
        stats.print_summary("Location Client Coordinate Resolution Load");
        
        assert!(stats.success_rate() > 0.90, "Success rate too low: {:.2}%", stats.success_rate() * 100.0);
        
        cluster.stop_all();
    }

    // ============================================================================
    // Multi-Client Concurrent Load Tests
    // ============================================================================

    #[test]
    fn test_concurrent_weather_clients_load() {
        let mut cluster = MockServerCluster::new().unwrap();
        cluster.start_all();
        
        let ports = cluster.ports();
        thread::sleep(Duration::from_millis(100));
        
        let client_count = 10;
        let requests_per_client = 50;
        let weather_port = ports.0;
        
        println!("Starting concurrent weather clients load test ({} clients, {} requests each)...", 
                client_count, requests_per_client);
        
        let handles: Vec<_> = (0..client_count).map(|client_id| {
            thread::spawn(move || {
                let client = WeatherClient::new(&format!("127.0.0.1:{}", weather_port));
                let mut generator = TestDataGenerator::new();
                let mut stats = LoadTestStats::new();
                
                for i in 0..requests_per_client {
                    let start_time = Instant::now();
                    let (lat, lng) = generator.random_coordinates();
                    
                    match client.get_weather_by_coordinates(lat, lng, true, false, false, false, false, 0) {
                        Ok(_) => stats.record_success(start_time.elapsed()),
                        Err(_) => stats.record_failure(start_time.elapsed()),
                    }
                    
                    // Small delay to prevent overwhelming
                    thread::sleep(Duration::from_millis(10));
                }
                
                println!("Client {} completed {} requests", client_id, requests_per_client);
                stats
            })
        }).collect();
        
        // Collect results from all clients
        let mut combined_stats = LoadTestStats::new();
        for handle in handles {
            let client_stats = handle.join().unwrap();
            combined_stats.merge(client_stats);
        }
        
        combined_stats.print_summary("Concurrent Weather Clients Load");
        
        assert!(combined_stats.success_rate() > 0.85, 
               "Concurrent success rate too low: {:.2}%", combined_stats.success_rate() * 100.0);
        
        cluster.stop_all();
    }

    #[test]
    fn test_mixed_client_types_concurrent_load() {
        let mut cluster = MockServerCluster::new().unwrap();
        cluster.start_all();
        
        let ports = cluster.ports();
        thread::sleep(Duration::from_millis(100));
        
        let requests_per_type = 30;
        
        println!("Starting mixed client types concurrent load test ({} requests per type)...", 
                requests_per_type);
        
        let handles = vec![
            // Weather clients
            thread::spawn({
                let weather_port = ports.0;
                move || {
                    let client = WeatherClient::new(&format!("127.0.0.1:{}", weather_port));
                    let mut generator = TestDataGenerator::new();
                    let mut stats = LoadTestStats::new();
                    
                    for _ in 0..requests_per_type {
                        let start_time = Instant::now();
                        let (lat, lng) = generator.random_coordinates();
                        
                        match client.get_weather_by_coordinates(lat, lng, true, true, false, false, false, 0) {
                            Ok(_) => stats.record_success(start_time.elapsed()),
                            Err(_) => stats.record_failure(start_time.elapsed()),
                        }
                        thread::sleep(Duration::from_millis(20));
                    }
                    
                    ("Weather", stats)
                }
            }),
            
            // Location clients
            thread::spawn({
                let location_port = ports.1;
                move || {
                    let client = LocationClient::new(&format!("127.0.0.1:{}", location_port));
                    let mut generator = TestDataGenerator::new();
                    let mut stats = LoadTestStats::new();
                    
                    for _ in 0..requests_per_type {
                        let start_time = Instant::now();
                        let (lat, lng) = generator.random_coordinates();
                        
                        match client.resolve_coordinates(lat, lng) {
                            Ok(_) => stats.record_success(start_time.elapsed()),
                            Err(_) => stats.record_failure(start_time.elapsed()),
                        }
                        thread::sleep(Duration::from_millis(20));
                    }
                    
                    ("Location", stats)
                }
            }),
            
            // Query clients
            thread::spawn({
                let query_port = ports.2;
                move || {
                    let client = QueryClient::new(&format!("127.0.0.1:{}", query_port));
                    let mut stats = LoadTestStats::new();
                    
                    for i in 0..requests_per_type {
                        let start_time = Instant::now();
                        let area_code = format!("13{:04}", i % 1000);
                        
                        match client.query_weather_data(&area_code, "weather,temperature") {
                            Ok(_) => stats.record_success(start_time.elapsed()),
                            Err(_) => stats.record_failure(start_time.elapsed()),
                        }
                        thread::sleep(Duration::from_millis(20));
                    }
                    
                    ("Query", stats)
                }
            }),
            
            // Report clients
            thread::spawn({
                let report_port = ports.3;
                move || {
                    let client = ReportClient::new(&format!("127.0.0.1:{}", report_port));
                    let mut generator = TestDataGenerator::new();
                    let mut stats = LoadTestStats::new();
                    
                    for _ in 0..requests_per_type {
                        let start_time = Instant::now();
                        let disaster_type = generator.random_disaster_type();
                        let severity = generator.random_severity();
                        let description = generator.random_disaster_description(disaster_type);
                        
                        match client.send_sensor_report(disaster_type, severity, &description, None, None) {
                            Ok(_) => stats.record_success(start_time.elapsed()),
                            Err(_) => stats.record_failure(start_time.elapsed()),
                        }
                        thread::sleep(Duration::from_millis(20));
                    }
                    
                    ("Report", stats)
                }
            }),
        ];
        
        // Collect and analyze results
        for handle in handles {
            let (client_type, stats) = handle.join().unwrap();
            stats.print_summary(&format!("Mixed Load - {} Clients", client_type));
            
            assert!(stats.success_rate() > 0.80, 
                   "{} client success rate too low: {:.2}%", client_type, stats.success_rate() * 100.0);
        }
        
        cluster.stop_all();
    }

    // ============================================================================
    // Stress Testing with Resource Constraints
    // ============================================================================

    #[test]
    fn test_packet_generation_stress() {
        println!("Starting packet generation stress test...");
        
        let mut stats = LoadTestStats::new();
        let packet_count = 10000;
        
        for i in 0..packet_count {
            let start_time = Instant::now();
            
            // Create and serialize various packet types
            let mut location_request = LocationRequest::new();
            location_request.set_latitude(35.6812 + (i as f64 * 0.001));
            location_request.set_longitude(139.7671 + (i as f64 * 0.001));
            
            let bytes = location_request.to_bytes();
            
            // Verify packet integrity
            if !bytes.is_empty() && bytes.len() >= 16 {
                stats.record_success(start_time.elapsed());
            } else {
                stats.record_failure(start_time.elapsed());
            }
            
            if (i + 1) % 1000 == 0 {
                println!("Generated {}/{} packets", i + 1, packet_count);
            }
        }
        
        stats.print_summary("Packet Generation Stress Test");
        
        // Should handle packet generation efficiently
        assert!(stats.success_rate() > 0.99, "Packet generation success rate too low");
        assert!(stats.average_response_time() < Duration::from_micros(100),
               "Packet generation too slow: {:?}", stats.average_response_time());
    }

    #[test]
    fn test_memory_usage_under_load() {
        let mut cluster = MockServerCluster::new().unwrap();
        cluster.start_all();
        
        let ports = cluster.ports();
        thread::sleep(Duration::from_millis(100));
        
        let client = WeatherClient::new(&format!("127.0.0.1:{}", ports.0));
        let mut generator = TestDataGenerator::new();
        
        println!("Starting memory usage stress test...");
        
        // Rapid-fire requests to test memory management
        let mut successful_requests = 0;
        let total_requests = 2000;
        
        for i in 0..total_requests {
            let (lat, lng) = generator.random_coordinates();
            
            if let Ok(_) = client.get_weather_by_coordinates(lat, lng, true, true, true, true, true, i % 7) {
                successful_requests += 1;
            }
            
            // Brief pause every 100 requests
            if i % 100 == 0 {
                thread::sleep(Duration::from_millis(10));
            }
        }
        
        let success_rate = successful_requests as f64 / total_requests as f64;
        println!("Memory stress test completed: {:.2}% success rate", success_rate * 100.0);
        
        assert!(success_rate > 0.80, "Memory stress test success rate too low: {:.2}%", success_rate * 100.0);
        
        cluster.stop_all();
    }
}

// ============================================================================
// Load Testing Statistics and Utilities
// ============================================================================

#[derive(Debug)]
struct LoadTestStats {
    total_requests: u64,
    successful_requests: u64,
    failed_requests: u64,
    response_times: Vec<Duration>,
    start_time: Instant,
}

impl LoadTestStats {
    fn new() -> Self {
        Self {
            total_requests: 0,
            successful_requests: 0,
            failed_requests: 0,
            response_times: Vec::new(),
            start_time: Instant::now(),
        }
    }
    
    fn record_success(&mut self, response_time: Duration) {
        self.total_requests += 1;
        self.successful_requests += 1;
        self.response_times.push(response_time);
    }
    
    fn record_failure(&mut self, response_time: Duration) {
        self.total_requests += 1;
        self.failed_requests += 1;
        self.response_times.push(response_time);
    }
    
    fn success_rate(&self) -> f64 {
        if self.total_requests == 0 {
            0.0
        } else {
            self.successful_requests as f64 / self.total_requests as f64
        }
    }
    
    fn average_response_time(&self) -> Duration {
        if self.response_times.is_empty() {
            Duration::new(0, 0)
        } else {
            let total_micros: u128 = self.response_times.iter()
                .map(|d| d.as_micros())
                .sum();
            Duration::from_micros((total_micros / self.response_times.len() as u128) as u64)
        }
    }
    
    fn p99_response_time(&self) -> Duration {
        if self.response_times.is_empty() {
            return Duration::new(0, 0);
        }
        
        let mut sorted_times = self.response_times.clone();
        sorted_times.sort();
        
        let p99_index = ((sorted_times.len() as f64 * 0.99) as usize).min(sorted_times.len() - 1);
        sorted_times[p99_index]
    }
    
    fn requests_per_second(&self) -> f64 {
        let elapsed = self.start_time.elapsed();
        if elapsed.as_secs_f64() > 0.0 {
            self.total_requests as f64 / elapsed.as_secs_f64()
        } else {
            0.0
        }
    }
    
    fn merge(&mut self, other: LoadTestStats) {
        self.total_requests += other.total_requests;
        self.successful_requests += other.successful_requests;
        self.failed_requests += other.failed_requests;
        self.response_times.extend(other.response_times);
    }
    
    fn print_summary(&self, test_name: &str) {
        println!("\n=== {} Load Test Results ===", test_name);
        println!("Total requests: {}", self.total_requests);
        println!("Successful: {} ({:.2}%)", self.successful_requests, self.success_rate() * 100.0);
        println!("Failed: {} ({:.2}%)", self.failed_requests, (self.failed_requests as f64 / self.total_requests as f64) * 100.0);
        println!("Average response time: {:?}", self.average_response_time());
        println!("P99 response time: {:?}", self.p99_response_time());
        println!("Requests per second: {:.2}", self.requests_per_second());
        println!("Total test duration: {:?}", self.start_time.elapsed());
        println!("========================================\n");
    }
}