use criterion::{black_box, criterion_group, criterion_main, Criterion, BenchmarkId};
use wip_rust::wip_common_rs::packet::types::location_packet::LocationRequest;
use wip_rust::wip_common_rs::packet::core::checksum::{calc_checksum12, verify_checksum12, embed_checksum12_le};

fn benchmark_location_request_creation(c: &mut Criterion) {
    c.bench_function("location_request_creation", |b| {
        b.iter(|| {
            let request = LocationRequest::create_coordinate_lookup(
                black_box(35.6812),    // Tokyo latitude
                black_box(139.7671),   // Tokyo longitude
                black_box(12345),      // packet_id
                black_box(true),       // weather
                black_box(false),      // temperature
                black_box(false),      // precipitation_prob
                black_box(false),      // alert
                black_box(false),      // disaster
                black_box(1),          // day
                black_box(1),          // version
            );
            black_box(request)
        });
    });
}

fn benchmark_location_request_serialization(c: &mut Criterion) {
    let request = LocationRequest::create_coordinate_lookup(
        35.6812, 139.7671, 12345, true, false, false, false, false, 1, 1
    );
    
    c.bench_function("location_request_serialization", |b| {
        b.iter(|| {
            black_box(request.to_bytes())
        });
    });
}

fn benchmark_checksum_calculation(c: &mut Criterion) {
    let mut group = c.benchmark_group("checksum_calculation");
    
    let sizes = vec![16, 64, 256, 1024];
    
    for size in sizes {
        let data: Vec<u8> = (0..size).map(|i| (i % 256) as u8).collect();
        
        group.bench_with_input(
            BenchmarkId::new("calc_checksum12", size),
            &data,
            |b, data| {
                b.iter(|| {
                    black_box(calc_checksum12(black_box(data)))
                });
            },
        );
    }
    
    group.finish();
}

fn benchmark_checksum_verification(c: &mut Criterion) {
    // Create a 16-byte header with embedded checksum
    let mut header = vec![0x12, 0x34, 0x56, 0x78, 0x9A, 0xBC, 0xDE, 0xF0, 
                         0x11, 0x22, 0x33, 0x44, 0x55, 0x66, 0x00, 0x00];
    embed_checksum12_le(&mut header);
    
    c.bench_function("checksum_verification", |b| {
        b.iter(|| {
            black_box(verify_checksum12(black_box(&header), black_box(116), black_box(12)))
        });
    });
}

fn benchmark_bulk_operations(c: &mut Criterion) {
    let mut group = c.benchmark_group("bulk_operations");
    
    let counts = vec![10, 50, 100];
    
    for count in counts {
        group.bench_with_input(
            BenchmarkId::new("bulk_location_requests", count),
            &count,
            |b, &count| {
                b.iter(|| {
                    let mut requests = Vec::new();
                    for i in 0..count {
                        let lat = 35.0 + (i as f64 * 0.001);
                        let lon = 139.0 + (i as f64 * 0.001);
                        let request = LocationRequest::create_coordinate_lookup(
                            black_box(lat), black_box(lon), black_box(i as u16),
                            black_box(true), black_box(false), black_box(false),
                            black_box(false), black_box(false), black_box(1), black_box(1)
                        );
                        requests.push(request.to_bytes());
                    }
                    black_box(requests)
                });
            },
        );
    }
    
    group.finish();
}

fn benchmark_coordinate_variations(c: &mut Criterion) {
    let coordinates = vec![
        (35.6812, 139.7671, "Tokyo"),
        (34.6937, 135.5023, "Osaka"),
        (43.0642, 141.3469, "Sapporo"),
        (33.5904, 130.4017, "Fukuoka"),
        (35.1815, 136.9066, "Nagoya"),
        (26.2123, 127.6792, "Naha"),
    ];
    
    c.bench_function("coordinate_variations", |b| {
        b.iter(|| {
            for (i, (lat, lon, _city)) in coordinates.iter().enumerate() {
                let request = LocationRequest::create_coordinate_lookup(
                    black_box(*lat), black_box(*lon), black_box(i as u16),
                    black_box(true), black_box(false), black_box(false),
                    black_box(false), black_box(false), black_box(1), black_box(1)
                );
                black_box(request.to_bytes());
            }
        });
    });
}

fn benchmark_memory_allocation(c: &mut Criterion) {
    c.bench_function("memory_allocation_pattern", |b| {
        b.iter(|| {
            // Test memory allocation patterns similar to real usage
            let mut packets = Vec::with_capacity(100);
            
            for i in 0..100 {
                let lat = 35.6812 + (i as f64 * 0.0001);
                let lon = 139.7671 + (i as f64 * 0.0001);
                
                let request = LocationRequest::create_coordinate_lookup(
                    lat, lon, i as u16, true, false, false, false, false, 1, 1
                );
                
                packets.push(request.to_bytes());
            }
            
            // Simulate processing
            let total_bytes: usize = packets.iter().map(|p| p.len()).sum();
            black_box(total_bytes);
            black_box(packets);
        });
    });
}

criterion_group!(
    benches,
    benchmark_location_request_creation,
    benchmark_location_request_serialization,
    benchmark_checksum_calculation,
    benchmark_checksum_verification,
    benchmark_bulk_operations,
    benchmark_coordinate_variations,
    benchmark_memory_allocation
);

criterion_main!(benches);