use std::time::{Duration, Instant};
use std::thread;
use std::sync::{Arc, Mutex};
use std::sync::atomic::{AtomicU64, Ordering};
use wip_rust::wip_common_rs::clients::weather_client::WeatherClient;
use wip_rust::wip_common_rs::clients::location_client::LocationClient;
use wip_rust::wip_common_rs::clients::query_client::QueryClient;
use wip_rust::wip_common_rs::clients::report_client::ReportClient;
use wip_rust::wip_common_rs::packet::core::checksum::{calc_checksum12, verify_checksum12, embed_checksum12_le};
use wip_rust::wip_common_rs::packet::types::location_packet::{LocationRequest, LocationResponse};

mod common;
use common::mock_server::{MockServerCluster, MockServerBuilder};
use common::test_data_generator::TestDataGenerator;

/// Performance and load testing suite for WIP Rust implementation
/// Measures throughput, latency, memory usage, and scalability

#[cfg(test)]
mod performance_tests {
    use super::*;

    const PERFORMANCE_TEST_ITERATIONS: usize = 1000;
    const STRESS_TEST_ITERATIONS: usize = 10000;
    const LOAD_TEST_DURATION: Duration = Duration::from_secs(30);

    // ============================================================================
    // Packet Processing Performance Tests
    // ============================================================================

    #[test]
    fn test_packet_serialization_performance() {
        let mut generator = TestDataGenerator::new();
        let packets: Vec<LocationRequest> = (0..PERFORMANCE_TEST_ITERATIONS)
            .map(|_| generator.location_request())
            .collect();

        let start = Instant::now();
        
        for packet in &packets {
            let _bytes = packet.to_bytes();
        }
        
        let elapsed = start.elapsed();
        let packets_per_second = PERFORMANCE_TEST_ITERATIONS as f64 / elapsed.as_secs_f64();
        
        println!("Packet serialization: {:.2} packets/second", packets_per_second);
        println!("Average time per packet: {:.2}μs", elapsed.as_micros() as f64 / PERFORMANCE_TEST_ITERATIONS as f64);
        
        // Performance requirement: should serialize at least 10,000 packets/second
        assert!(packets_per_second > 10000.0, 
            "Serialization too slow: {:.2} packets/second", packets_per_second);
    }

    #[test]
    fn test_checksum_calculation_performance() {
        let mut generator = TestDataGenerator::new();
        let test_data: Vec<Vec<u8>> = (0..PERFORMANCE_TEST_ITERATIONS)
            .map(|_| {
                let packet = generator.location_request();
                packet.to_bytes()
            })
            .collect();

        let start = Instant::now();
        
        for data in &test_data {
            let _checksum = calc_checksum12(data);
        }
        
        let elapsed = start.elapsed();
        let checksums_per_second = PERFORMANCE_TEST_ITERATIONS as f64 / elapsed.as_secs_f64();
        
        println!("Checksum calculation: {:.2} checksums/second", checksums_per_second);
        
        // Performance requirement: should calculate at least 50,000 checksums/second
        assert!(checksums_per_second > 50000.0, 
            "Checksum calculation too slow: {:.2} checksums/second", checksums_per_second);
    }

    #[test]
    fn test_checksum_verification_performance() {
        let mut generator = TestDataGenerator::new();
        let mut test_data: Vec<Vec<u8>> = (0..PERFORMANCE_TEST_ITERATIONS)
            .map(|_| {
                let packet = generator.location_request();
                let mut bytes = packet.to_bytes();
                embed_checksum12_le(&mut bytes);
                bytes
            })
            .collect();

        let start = Instant::now();
        
        for data in &test_data {
            let _is_valid = verify_checksum12(data, 0, data.len() - 2).unwrap_or(false);
        }
        
        let elapsed = start.elapsed();
        let verifications_per_second = PERFORMANCE_TEST_ITERATIONS as f64 / elapsed.as_secs_f64();
        
        println!("Checksum verification: {:.2} verifications/second", verifications_per_second);
        
        // Performance requirement: should verify at least 40,000 checksums/second
        assert!(verifications_per_second > 40000.0, 
            "Checksum verification too slow: {:.2} verifications/second", verifications_per_second);
    }

    #[test]
    fn test_memory_usage_packet_creation() {
        let start_memory = get_memory_usage();
        
        let mut packets = Vec::new();
        for i in 0..STRESS_TEST_ITERATIONS {
            let mut generator = TestDataGenerator::new();
            let packet = generator.location_request();
            packets.push(packet);
            
            // Check memory usage periodically
            if i % 1000 == 0 {
                let current_memory = get_memory_usage();
                let memory_diff = current_memory - start_memory;
                
                // Memory usage should be reasonable (less than 100MB for 10k packets)
                assert!(memory_diff < 100 * 1024 * 1024, 
                    "Memory usage too high: {} bytes for {} packets", memory_diff, i + 1);
            }
        }
        
        let end_memory = get_memory_usage();
        let total_memory_used = end_memory - start_memory;
        let memory_per_packet = total_memory_used / STRESS_TEST_ITERATIONS;
        
        println!("Memory usage: {} bytes total, {} bytes per packet", 
                total_memory_used, memory_per_packet);
        
        // Each packet should use less than 1KB of memory on average
        assert!(memory_per_packet < 1024, 
            "Memory usage per packet too high: {} bytes", memory_per_packet);
    }

    // ============================================================================
    // Network Communication Performance Tests
    // ============================================================================

    #[test]
    fn test_client_throughput() {
        let mut cluster = MockServerCluster::new().unwrap();
        cluster.start_all();
        
        let (weather_port, _, _, _) = cluster.ports();
        thread::sleep(Duration::from_millis(100));
        
        let client = WeatherClient::new(&format!("127.0.0.1:{}", weather_port));
        let mut generator = TestDataGenerator::new();
        
        let start = Instant::now();
        let mut successful_requests = 0;
        
        for _ in 0..100 { // Smaller number for network tests
            let (lat, lon) = generator.random_coordinates();
            
            match client.get_weather_by_coordinates(lat, lon, true, false, false, false, false, 0) {
                Ok(_) => successful_requests += 1,
                Err(_) => {}, // Some failures are acceptable
            }
        }
        
        let elapsed = start.elapsed();
        let requests_per_second = successful_requests as f64 / elapsed.as_secs_f64();
        
        println!("Client throughput: {:.2} requests/second ({}/100 successful)", 
                requests_per_second, successful_requests);
        
        // Should complete at least 50 requests per second
        assert!(requests_per_second > 50.0, 
            "Client throughput too low: {:.2} requests/second", requests_per_second);
        
        cluster.stop_all();
    }

    #[test]
    fn test_concurrent_client_performance() {
        let mut cluster = MockServerCluster::new().unwrap();
        cluster.start_all();
        
        let (weather_port, _, _, _) = cluster.ports();
        thread::sleep(Duration::from_millis(100));
        
        let num_threads = 4;
        let requests_per_thread = 25;
        let successful_requests = Arc::new(AtomicU64::new(0));
        let total_requests = Arc::new(AtomicU64::new(0));
        
        let start = Instant::now();
        
        let handles: Vec<_> = (0..num_threads).map(|_| {
            let successful = Arc::clone(&successful_requests);
            let total = Arc::clone(&total_requests);
            let port = weather_port;
            
            thread::spawn(move || {
                let client = WeatherClient::new(&format!("127.0.0.1:{}", port));
                let mut generator = TestDataGenerator::new();
                
                for _ in 0..requests_per_thread {
                    total.fetch_add(1, Ordering::Relaxed);
                    let (lat, lon) = generator.random_coordinates();
                    
                    match client.get_weather_by_coordinates(lat, lon, true, false, false, false, false, 0) {
                        Ok(_) => {
                            successful.fetch_add(1, Ordering::Relaxed);
                        },
                        Err(_) => {},
                    }
                }
            })
        }).collect();
        
        for handle in handles {
            handle.join().unwrap();
        }
        
        let elapsed = start.elapsed();
        let total_count = total_requests.load(Ordering::Relaxed);
        let success_count = successful_requests.load(Ordering::Relaxed);
        let requests_per_second = success_count as f64 / elapsed.as_secs_f64();
        
        println!("Concurrent performance: {:.2} requests/second ({}/{} successful)", 
                requests_per_second, success_count, total_count);
        
        // Should handle concurrent requests efficiently
        assert!(requests_per_second > 100.0, 
            "Concurrent throughput too low: {:.2} requests/second", requests_per_second);
        
        cluster.stop_all();
    }

    #[test]
    fn test_latency_distribution() {
        let mut cluster = MockServerCluster::new().unwrap();
        cluster.start_all();
        
        let (weather_port, _, _, _) = cluster.ports();
        thread::sleep(Duration::from_millis(100));
        
        let client = WeatherClient::new(&format!("127.0.0.1:{}", weather_port));
        let mut generator = TestDataGenerator::new();
        
        let mut latencies = Vec::new();
        
        for _ in 0..100 {
            let (lat, lon) = generator.random_coordinates();
            let start = Instant::now();
            
            match client.get_weather_by_coordinates(lat, lon, true, false, false, false, false, 0) {
                Ok(_) => {
                    let latency = start.elapsed();
                    latencies.push(latency);
                },
                Err(_) => {}, // Skip failed requests
            }
        }
        
        if !latencies.is_empty() {
            latencies.sort();
            
            let mean_latency = latencies.iter().sum::<Duration>() / latencies.len() as u32;
            let p50_latency = latencies[latencies.len() / 2];
            let p95_latency = latencies[(latencies.len() * 95) / 100];
            let p99_latency = latencies[(latencies.len() * 99) / 100];
            
            println!("Latency distribution:");
            println!("  Mean: {:.2}ms", mean_latency.as_millis());
            println!("  P50:  {:.2}ms", p50_latency.as_millis());
            println!("  P95:  {:.2}ms", p95_latency.as_millis());
            println!("  P99:  {:.2}ms", p99_latency.as_millis());
            
            // Performance requirements
            assert!(mean_latency < Duration::from_millis(100), 
                "Mean latency too high: {:.2}ms", mean_latency.as_millis());
            assert!(p95_latency < Duration::from_millis(200), 
                "P95 latency too high: {:.2}ms", p95_latency.as_millis());
        }
        
        cluster.stop_all();
    }

    // ============================================================================
    // Load and Stress Tests
    // ============================================================================

    #[test]
    fn test_sustained_load() {
        let mut cluster = MockServerCluster::new().unwrap();
        cluster.start_all();
        
        let (weather_port, _, _, _) = cluster.ports();
        thread::sleep(Duration::from_millis(100));
        
        let client = WeatherClient::new(&format!("127.0.0.1:{}", weather_port));
        let mut generator = TestDataGenerator::new();
        
        let start = Instant::now();
        let successful_requests = Arc::new(AtomicU64::new(0));
        let total_requests = Arc::new(AtomicU64::new(0));
        
        // Run load test for specified duration
        while start.elapsed() < LOAD_TEST_DURATION {
            total_requests.fetch_add(1, Ordering::Relaxed);
            let (lat, lon) = generator.random_coordinates();
            
            match client.get_weather_by_coordinates(lat, lon, true, false, false, false, false, 0) {
                Ok(_) => {
                    successful_requests.fetch_add(1, Ordering::Relaxed);
                },
                Err(_) => {},
            }
            
            // Small delay to prevent overwhelming the system
            thread::sleep(Duration::from_millis(10));
        }
        
        let elapsed = start.elapsed();
        let total_count = total_requests.load(Ordering::Relaxed);
        let success_count = successful_requests.load(Ordering::Relaxed);
        let success_rate = success_count as f64 / total_count as f64;
        let requests_per_second = success_count as f64 / elapsed.as_secs_f64();
        
        println!("Sustained load test:");
        println!("  Duration: {:.2}s", elapsed.as_secs_f64());
        println!("  Total requests: {}", total_count);
        println!("  Successful requests: {}", success_count);
        println!("  Success rate: {:.2}%", success_rate * 100.0);
        println!("  Throughput: {:.2} requests/second", requests_per_second);
        
        // Success rate should be high under sustained load
        assert!(success_rate > 0.9, "Success rate too low: {:.2}%", success_rate * 100.0);
        
        cluster.stop_all();
    }

    #[test]
    fn test_memory_leak_detection() {
        let start_memory = get_memory_usage();
        
        // Perform many operations that could potentially leak memory
        for cycle in 0..10 {
            let mut generator = TestDataGenerator::new();
            let mut packets = Vec::new();
            
            // Create many packets
            for _ in 0..1000 {
                packets.push(generator.location_request());
            }
            
            // Serialize them
            let mut serialized = Vec::new();
            for packet in &packets {
                serialized.push(packet.to_bytes());
            }
            
            // Calculate checksums
            for data in &serialized {
                let _checksum = calc_checksum12(data);
            }
            
            // Force garbage collection by dropping everything
            drop(packets);
            drop(serialized);
            
            // Check memory usage every few cycles
            if cycle % 3 == 0 {
                let current_memory = get_memory_usage();
                let memory_growth = current_memory - start_memory;
                
                println!("Cycle {}: Memory growth: {} bytes", cycle, memory_growth);
                
                // Memory should not grow excessively
                assert!(memory_growth < 50 * 1024 * 1024, 
                    "Potential memory leak detected: {} bytes growth", memory_growth);
            }
        }
        
        let end_memory = get_memory_usage();
        let total_growth = end_memory - start_memory;
        
        println!("Total memory growth: {} bytes", total_growth);
        
        // Final memory usage should be reasonable
        assert!(total_growth < 100 * 1024 * 1024, 
            "Memory leak detected: {} bytes total growth", total_growth);
    }

    #[test]
    fn test_packet_size_efficiency() {
        let mut generator = TestDataGenerator::new();
        let mut total_size = 0;
        let packet_count = 1000;
        
        for _ in 0..packet_count {
            let packet = generator.location_request();
            let bytes = packet.to_bytes();
            total_size += bytes.len();
        }
        
        let average_size = total_size / packet_count;
        
        println!("Average packet size: {} bytes", average_size);
        
        // WIP packets should be small and efficient
        assert!(average_size < 100, "Packets too large: {} bytes average", average_size);
        assert!(average_size >= 16, "Packets too small: {} bytes average", average_size);
    }

    #[test]
    fn test_cpu_intensive_operations() {
        let mut generator = TestDataGenerator::new();
        let start = Instant::now();
        
        // Perform CPU-intensive operations
        for _ in 0..STRESS_TEST_ITERATIONS {
            let packet = generator.location_request();
            let mut bytes = packet.to_bytes();
            
            // Multiple checksum operations
            let checksum1 = calc_checksum12(&bytes);
            embed_checksum12_le(&mut bytes);
            let _is_valid = verify_checksum12(&bytes, 0, bytes.len() - 2).unwrap_or(false);
            
            // Bit manipulations
            for i in 0..bytes.len() {
                bytes[i] ^= (checksum1 as u8);
            }
        }
        
        let elapsed = start.elapsed();
        let operations_per_second = STRESS_TEST_ITERATIONS as f64 / elapsed.as_secs_f64();
        
        println!("CPU-intensive operations: {:.2} operations/second", operations_per_second);
        
        // Should handle CPU-intensive operations efficiently
        assert!(operations_per_second > 1000.0, 
            "CPU operations too slow: {:.2} operations/second", operations_per_second);
    }

    // ============================================================================
    // Comparison and Regression Tests
    // ============================================================================

    #[test]
    fn test_performance_regression() {
        // Baseline performance benchmarks
        // These would be updated when performance improvements are made
        
        let mut generator = TestDataGenerator::new();
        
        // Packet serialization benchmark
        let start = Instant::now();
        for _ in 0..1000 {
            let packet = generator.location_request();
            let _bytes = packet.to_bytes();
        }
        let serialization_time = start.elapsed();
        
        // Checksum calculation benchmark
        let test_data: Vec<Vec<u8>> = (0..1000)
            .map(|_| generator.location_request().to_bytes())
            .collect();
        
        let start = Instant::now();
        for data in &test_data {
            let _checksum = calc_checksum12(data);
        }
        let checksum_time = start.elapsed();
        
        println!("Performance benchmarks:");
        println!("  Serialization: {:.2}ms for 1000 packets", serialization_time.as_millis());
        println!("  Checksum calc: {:.2}ms for 1000 packets", checksum_time.as_millis());
        
        // Regression thresholds (these would be based on baseline measurements)
        assert!(serialization_time < Duration::from_millis(100), 
            "Serialization performance regression: {:.2}ms", serialization_time.as_millis());
        assert!(checksum_time < Duration::from_millis(50), 
            "Checksum performance regression: {:.2}ms", checksum_time.as_millis());
    }

    // ============================================================================
    // Utility Functions
    // ============================================================================

    /// Get current memory usage (simplified implementation)
    fn get_memory_usage() -> usize {
        // This is a simplified memory usage measurement
        // In practice, you might use a more sophisticated method
        // or external tools for accurate memory measurement
        
        #[cfg(target_os = "linux")]
        {
            use std::fs;
            if let Ok(contents) = fs::read_to_string("/proc/self/status") {
                for line in contents.lines() {
                    if line.starts_with("VmRSS:") {
                        if let Some(kb_str) = line.split_whitespace().nth(1) {
                            if let Ok(kb) = kb_str.parse::<usize>() {
                                return kb * 1024; // Convert KB to bytes
                            }
                        }
                    }
                }
            }
        }
        
        // Fallback: estimate based on allocator stats or return 0
        0
    }

    #[test]
    fn test_benchmark_baseline() {
        // This test establishes performance baselines
        // Run this periodically to track performance trends
        
        let mut results = Vec::new();
        
        // Run multiple iterations to get stable measurements
        for _ in 0..5 {
            let mut generator = TestDataGenerator::new();
            
            // Measure packet creation
            let start = Instant::now();
            for _ in 0..1000 {
                let _packet = generator.location_request();
            }
            let creation_time = start.elapsed();
            
            // Measure serialization
            let packets: Vec<_> = (0..1000).map(|_| generator.location_request()).collect();
            let start = Instant::now();
            for packet in &packets {
                let _bytes = packet.to_bytes();
            }
            let serialization_time = start.elapsed();
            
            results.push((creation_time, serialization_time));
        }
        
        // Calculate averages
        let avg_creation = results.iter().map(|(c, _)| *c).sum::<Duration>() / results.len() as u32;
        let avg_serialization = results.iter().map(|(_, s)| *s).sum::<Duration>() / results.len() as u32;
        
        println!("Baseline benchmarks (average of {} runs):", results.len());
        println!("  Packet creation: {:.2}μs per packet", 
                avg_creation.as_nanos() as f64 / 1000.0 / 1000.0);
        println!("  Serialization: {:.2}μs per packet", 
                avg_serialization.as_nanos() as f64 / 1000.0 / 1000.0);
        
        // These measurements can be used as baselines for future regression testing
    }
}