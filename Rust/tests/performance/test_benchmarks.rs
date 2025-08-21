use std::time::{Duration, Instant};
use wip_rust::wip_common_rs::packet::core::checksum::{calc_checksum12, verify_checksum12, embed_checksum12_le};
use wip_rust::wip_common_rs::packet::core::bit_utils::{extract_bits, set_bits};
use wip_rust::wip_common_rs::packet::types::location_packet::{LocationRequest, LocationResponse};
use wip_rust::wip_common_rs::packet::types::query_packet::{QueryRequest, QueryResponse};
use wip_rust::wip_common_rs::packet::types::report_packet::{ReportRequest, ReportResponse};
use wip_rust::wip_common_rs::packet::core::PacketFormat;

/// Comprehensive performance benchmarking suite
/// Measures and validates performance of core WIP operations

#[cfg(test)]
mod performance_benchmarks {
    use super::*;

    // ============================================================================
    // Core Algorithm Benchmarks
    // ============================================================================

    #[test]
    fn benchmark_checksum_calculation() {
        println!("=== Checksum Calculation Benchmark ===");
        
        let test_sizes = vec![16, 64, 256, 1024, 4096, 16384];
        
        for size in test_sizes {
            let data = vec![0xAA; size];
            let iterations = 10000;
            
            let start_time = Instant::now();
            
            for _ in 0..iterations {
                let _checksum = calc_checksum12(&data);
            }
            
            let elapsed = start_time.elapsed();
            let avg_time = elapsed / iterations;
            let throughput = (size as f64 * iterations as f64) / elapsed.as_secs_f64();
            
            println!("Size {} bytes: {:?} avg, {:.2} MB/s", size, avg_time, throughput / (1024.0 * 1024.0));
            
            // Performance requirements
            assert!(avg_time < Duration::from_micros(100), "Checksum calculation too slow for {} bytes", size);
        }
    }

    #[test]
    fn benchmark_checksum_verification() {
        println!("\n=== Checksum Verification Benchmark ===");
        
        let test_sizes = vec![16, 64, 256, 1024, 4096];
        
        for size in test_sizes {
            let mut data = vec![0x55; size];
            embed_checksum12_le(&mut data);
            
            let iterations = 10000;
            let start_time = Instant::now();
            
            for _ in 0..iterations {
                let _result = verify_checksum12(&data);
            }
            
            let elapsed = start_time.elapsed();
            let avg_time = elapsed / iterations;
            
            println!("Size {} bytes: {:?} avg", size, avg_time);
            
            assert!(avg_time < Duration::from_micros(150), "Checksum verification too slow for {} bytes", size);
        }
    }

    #[test]
    fn benchmark_bit_operations() {
        println!("\n=== Bit Operations Benchmark ===");
        
        let data = 0x123456789ABCDEF0123456789ABCDEF0_u128;
        let iterations = 100000;
        
        // Benchmark bit extraction
        let start_time = Instant::now();
        for i in 0..iterations {
            let _result = extract_bits(data, (i % 120) as usize, 8);
        }
        let extract_time = start_time.elapsed();
        
        // Benchmark bit setting
        let mut test_data = data;
        let start_time = Instant::now();
        for i in 0..iterations {
            set_bits(&mut test_data, (i % 120) as usize, 8, i % 256);
        }
        let set_time = start_time.elapsed();
        
        let extract_avg = extract_time / iterations;
        let set_avg = set_time / iterations;
        
        println!("Bit extraction: {:?} avg ({:.2} ops/sec)", extract_avg, 1.0 / extract_avg.as_secs_f64());
        println!("Bit setting: {:?} avg ({:.2} ops/sec)", set_avg, 1.0 / set_avg.as_secs_f64());
        
        assert!(extract_avg < Duration::from_nanos(100), "Bit extraction too slow");
        assert!(set_avg < Duration::from_nanos(200), "Bit setting too slow");
    }

    // ============================================================================
    // Packet Operations Benchmarks
    // ============================================================================

    #[test]
    fn benchmark_packet_creation() {
        println!("\n=== Packet Creation Benchmark ===");
        
        let iterations = 10000;
        
        // LocationRequest creation
        let start_time = Instant::now();
        for _ in 0..iterations {
            let _packet = LocationRequest::new();
        }
        let location_time = start_time.elapsed();
        
        // QueryRequest creation
        let start_time = Instant::now();
        for _ in 0..iterations {
            let _packet = QueryRequest::new();
        }
        let query_time = start_time.elapsed();
        
        // ReportRequest creation
        let start_time = Instant::now();
        for _ in 0..iterations {
            let _packet = ReportRequest::new();
        }
        let report_time = start_time.elapsed();
        
        let location_avg = location_time / iterations;
        let query_avg = query_time / iterations;
        let report_avg = report_time / iterations;
        
        println!("LocationRequest: {:?} avg", location_avg);
        println!("QueryRequest: {:?} avg", query_avg);
        println!("ReportRequest: {:?} avg", report_avg);
        
        assert!(location_avg < Duration::from_micros(10), "LocationRequest creation too slow");
        assert!(query_avg < Duration::from_micros(10), "QueryRequest creation too slow");
        assert!(report_avg < Duration::from_micros(10), "ReportRequest creation too slow");
    }

    #[test]
    fn benchmark_packet_serialization() {
        println!("\n=== Packet Serialization Benchmark ===");
        
        let mut location_request = LocationRequest::new();
        location_request.set_latitude(35.6812);
        location_request.set_longitude(139.7671);
        location_request.set_weather_flag(true);
        location_request.set_temperature_flag(true);
        
        let mut query_request = QueryRequest::new();
        query_request.set_query_type("weather_status".to_string());
        query_request.set_parameters("region=tokyo&day=0&format=json".to_string());
        
        let mut report_request = ReportRequest::new();
        report_request.set_disaster_type("earthquake".to_string());
        report_request.set_severity(7);
        report_request.set_description("Strong earthquake detected in Tokyo area with significant shaking reported across multiple districts".to_string());
        
        let iterations = 5000;
        
        // Benchmark LocationRequest serialization
        let start_time = Instant::now();
        for _ in 0..iterations {
            let _bytes = location_request.to_bytes();
        }
        let location_time = start_time.elapsed();
        
        // Benchmark QueryRequest serialization
        let start_time = Instant::now();
        for _ in 0..iterations {
            let _bytes = query_request.to_bytes();
        }
        let query_time = start_time.elapsed();
        
        // Benchmark ReportRequest serialization
        let start_time = Instant::now();
        for _ in 0..iterations {
            let _bytes = report_request.to_bytes();
        }
        let report_time = start_time.elapsed();
        
        let location_avg = location_time / iterations;
        let query_avg = query_time / iterations;
        let report_avg = report_time / iterations;
        
        println!("LocationRequest serialization: {:?} avg", location_avg);
        println!("QueryRequest serialization: {:?} avg", query_avg);
        println!("ReportRequest serialization: {:?} avg", report_avg);
        
        assert!(location_avg < Duration::from_micros(50), "LocationRequest serialization too slow");
        assert!(query_avg < Duration::from_micros(100), "QueryRequest serialization too slow");
        assert!(report_avg < Duration::from_micros(150), "ReportRequest serialization too slow");
    }

    #[test]
    fn benchmark_packet_field_operations() {
        println!("\n=== Packet Field Operations Benchmark ===");
        
        let mut packet = LocationRequest::new();
        let iterations = 50000;
        
        // Benchmark field setting
        let start_time = Instant::now();
        for i in 0..iterations {
            packet.set_latitude(35.0 + (i as f64 * 0.0001));
            packet.set_longitude(139.0 + (i as f64 * 0.0001));
            packet.set_weather_flag(i % 2 == 0);
            packet.set_temperature_flag(i % 3 == 0);
        }
        let set_time = start_time.elapsed();
        
        // Benchmark field getting
        let start_time = Instant::now();
        for _ in 0..iterations {
            let _lat = packet.get_latitude();
            let _lng = packet.get_longitude();
            let _weather = packet.get_weather_flag();
            let _temp = packet.get_temperature_flag();
        }
        let get_time = start_time.elapsed();
        
        let set_avg = set_time / iterations;
        let get_avg = get_time / iterations;
        
        println!("Field setting: {:?} avg per packet", set_avg);
        println!("Field getting: {:?} avg per packet", get_avg);
        
        assert!(set_avg < Duration::from_nanos(500), "Field setting too slow");
        assert!(get_avg < Duration::from_nanos(200), "Field getting too slow");
    }

    // ============================================================================
    // Memory and Resource Usage Benchmarks
    // ============================================================================

    #[test]
    fn benchmark_memory_allocation_patterns() {
        println!("\n=== Memory Allocation Patterns Benchmark ===");
        
        let iterations = 1000;
        
        // Test rapid packet creation and destruction
        let start_time = Instant::now();
        for _ in 0..iterations {
            let packets: Vec<Box<dyn PacketFormat>> = vec![
                Box::new(LocationRequest::new()),
                Box::new(LocationResponse::new()),
                Box::new(QueryRequest::new()),
                Box::new(QueryResponse::new()),
                Box::new(ReportRequest::new()),
                Box::new(ReportResponse::new()),
            ];
            
            // Use the packets to prevent optimization
            let _total_bytes: usize = packets.iter().map(|p| p.to_bytes().len()).sum();
        }
        let allocation_time = start_time.elapsed();
        
        let avg_time = allocation_time / iterations;
        println!("Mixed packet allocation: {:?} avg per batch (6 packets)", avg_time);
        
        assert!(avg_time < Duration::from_micros(100), "Memory allocation pattern too slow");
    }

    #[test]
    fn benchmark_large_data_handling() {
        println!("\n=== Large Data Handling Benchmark ===");
        
        let mut query_request = QueryRequest::new();
        let mut report_request = ReportRequest::new();
        
        // Test with large data payloads
        let large_query = "weather_data=".to_string() + &"A".repeat(10000);
        let large_description = "Detailed disaster report: ".to_string() + &"B".repeat(5000);
        
        let iterations = 100;
        
        // Benchmark large query handling
        let start_time = Instant::now();
        for _ in 0..iterations {
            query_request.set_parameters(large_query.clone());
            let _bytes = query_request.to_bytes();
        }
        let query_time = start_time.elapsed();
        
        // Benchmark large report handling
        let start_time = Instant::now();
        for _ in 0..iterations {
            report_request.set_description(large_description.clone());
            let _bytes = report_request.to_bytes();
        }
        let report_time = start_time.elapsed();
        
        let query_avg = query_time / iterations;
        let report_avg = report_time / iterations;
        
        println!("Large query handling ({} chars): {:?} avg", large_query.len(), query_avg);
        println!("Large report handling ({} chars): {:?} avg", large_description.len(), report_avg);
        
        assert!(query_avg < Duration::from_millis(1), "Large query handling too slow");
        assert!(report_avg < Duration::from_millis(1), "Large report handling too slow");
    }

    // ============================================================================
    // Comparative Performance Tests
    // ============================================================================

    #[test]
    fn benchmark_packet_type_comparison() {
        println!("\n=== Packet Type Performance Comparison ===");
        
        let iterations = 1000;
        
        // Create representative instances of each packet type
        let mut location_req = LocationRequest::new();
        location_req.set_latitude(35.6812);
        location_req.set_longitude(139.7671);
        
        let mut query_req = QueryRequest::new();
        query_req.set_query_type("weather".to_string());
        query_req.set_parameters("area=130010".to_string());
        
        let mut report_req = ReportRequest::new();
        report_req.set_disaster_type("earthquake".to_string());
        report_req.set_severity(5);
        report_req.set_description("Test report".to_string());
        
        let packets: Vec<(&str, Box<dyn PacketFormat>)> = vec![
            ("LocationRequest", Box::new(location_req)),
            ("QueryRequest", Box::new(query_req)),
            ("ReportRequest", Box::new(report_req)),
        ];
        
        for (packet_type, packet) in packets {
            let start_time = Instant::now();
            
            for _ in 0..iterations {
                let _bytes = packet.to_bytes();
            }
            
            let elapsed = start_time.elapsed();
            let avg_time = elapsed / iterations;
            
            println!("{}: {:?} avg serialization time", packet_type, avg_time);
            
            assert!(avg_time < Duration::from_micros(200), 
                   "{} serialization too slow: {:?}", packet_type, avg_time);
        }
    }

    #[test]
    fn benchmark_checksum_vs_data_size() {
        println!("\n=== Checksum Performance vs Data Size ===");
        
        let size_multipliers = vec![1, 2, 4, 8, 16, 32, 64];
        let base_size = 64;
        let iterations_per_size = 1000;
        
        for multiplier in size_multipliers {
            let size = base_size * multiplier;
            let data = vec![0x42; size];
            
            let start_time = Instant::now();
            
            for _ in 0..iterations_per_size {
                let _checksum = calc_checksum12(&data);
            }
            
            let elapsed = start_time.elapsed();
            let avg_time = elapsed / iterations_per_size;
            let bytes_per_second = (size as f64 * iterations_per_size as f64) / elapsed.as_secs_f64();
            
            println!("Size {}: {:?} avg, {:.2} MB/s", size, avg_time, bytes_per_second / (1024.0 * 1024.0));
            
            // Performance should scale reasonably with data size
            let expected_max_time = Duration::from_nanos(100 * multiplier as u64);
            assert!(avg_time < expected_max_time, 
                   "Checksum performance doesn't scale well for size {}", size);
        }
    }

    // ============================================================================
    // Real-world Scenario Benchmarks
    // ============================================================================

    #[test]
    fn benchmark_typical_workflow() {
        println!("\n=== Typical Workflow Benchmark ===");
        
        let iterations = 100;
        let start_time = Instant::now();
        
        for i in 0..iterations {
            // Simulate typical weather lookup workflow
            
            // 1. Create location request
            let mut location_req = LocationRequest::new();
            location_req.set_latitude(35.6812 + (i as f64 * 0.001));
            location_req.set_longitude(139.7671 + (i as f64 * 0.001));
            location_req.set_weather_flag(true);
            location_req.set_temperature_flag(true);
            
            // 2. Serialize location request
            let _location_bytes = location_req.to_bytes();
            
            // 3. Create and serialize location response
            let mut location_resp = LocationResponse::new();
            location_resp.set_area_code(130010 + (i % 1000));
            location_resp.set_region_name(format!("Region_{}", i));
            let _location_resp_bytes = location_resp.to_bytes();
            
            // 4. Create and serialize query request
            let mut query_req = QueryRequest::new();
            query_req.set_query_type("weather_status".to_string());
            query_req.set_parameters(format!("area_code={}&day=0", 130010 + (i % 1000)));
            let _query_bytes = query_req.to_bytes();
            
            // 5. Create and serialize query response
            let mut query_resp = QueryResponse::new();
            query_resp.set_result_count(1);
            query_resp.set_data(format!("{{\"temperature\": {}, \"humidity\": {}}}", 20 + (i % 15), 50 + (i % 40)));
            let _query_resp_bytes = query_resp.to_bytes();
        }
        
        let elapsed = start_time.elapsed();
        let avg_workflow_time = elapsed / iterations;
        
        println!("Typical workflow: {:?} avg per complete cycle", avg_workflow_time);
        println!("Workflow throughput: {:.2} cycles/sec", 1.0 / avg_workflow_time.as_secs_f64());
        
        assert!(avg_workflow_time < Duration::from_millis(1), 
               "Typical workflow too slow: {:?}", avg_workflow_time);
    }

    #[test]
    fn benchmark_concurrent_operation_overhead() {
        use std::sync::{Arc, Mutex};
        use std::thread;
        
        println!("\n=== Concurrent Operation Overhead Benchmark ===");
        
        let thread_count = 4;
        let operations_per_thread = 500;
        
        let shared_counter = Arc::new(Mutex::new(0));
        
        let start_time = Instant::now();
        
        let handles: Vec<_> = (0..thread_count).map(|thread_id| {
            let counter = Arc::clone(&shared_counter);
            
            thread::spawn(move || {
                for i in 0..operations_per_thread {
                    let mut location_req = LocationRequest::new();
                    location_req.set_latitude(35.0 + (thread_id as f64 * 0.1) + (i as f64 * 0.001));
                    location_req.set_longitude(139.0 + (thread_id as f64 * 0.1) + (i as f64 * 0.001));
                    
                    let _bytes = location_req.to_bytes();
                    
                    let mut counter_lock = counter.lock().unwrap();
                    *counter_lock += 1;
                }
            })
        }).collect();
        
        for handle in handles {
            handle.join().unwrap();
        }
        
        let elapsed = start_time.elapsed();
        let total_operations = thread_count * operations_per_thread;
        let avg_operation_time = elapsed / total_operations;
        
        println!("Concurrent operations ({} threads): {:?} avg per operation", thread_count, avg_operation_time);
        println!("Concurrent throughput: {:.2} ops/sec", total_operations as f64 / elapsed.as_secs_f64());
        
        assert!(avg_operation_time < Duration::from_micros(100), 
               "Concurrent operation overhead too high: {:?}", avg_operation_time);
    }
}

// ============================================================================
// Benchmark Utilities
// ============================================================================

#[allow(dead_code)]
struct BenchmarkResult {
    operation_name: String,
    iterations: u32,
    total_time: Duration,
    average_time: Duration,
    throughput_ops_per_sec: f64,
}

#[allow(dead_code)]
impl BenchmarkResult {
    fn new(name: &str, iterations: u32, total_time: Duration) -> Self {
        let average_time = total_time / iterations;
        let throughput = if total_time.as_secs_f64() > 0.0 {
            iterations as f64 / total_time.as_secs_f64()
        } else {
            0.0
        };
        
        Self {
            operation_name: name.to_string(),
            iterations,
            total_time,
            average_time,
            throughput_ops_per_sec: throughput,
        }
    }
    
    fn print(&self) {
        println!("{}: {} iterations in {:?} (avg: {:?}, {:.2} ops/sec)", 
                self.operation_name, 
                self.iterations, 
                self.total_time, 
                self.average_time, 
                self.throughput_ops_per_sec);
    }
}