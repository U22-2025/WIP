use wip_rust::wip_common_rs::packet::types::location_packet::LocationRequest;
use wip_rust::wip_common_rs::packet::core::checksum::{calc_checksum12, verify_checksum12, embed_checksum12_le};

#[test]
fn test_location_request_creation() {
    let request = LocationRequest::create_coordinate_lookup(
        35.6812,  // Tokyo latitude
        139.7671, // Tokyo longitude
        12345,    // packet_id
        true,     // weather
        false,    // temperature
        false,    // precipitation_prob
        false,    // alert
        false,    // disaster
        1,        // day
        1,        // version
    );
    
    assert_eq!(request.latitude, 35.6812);
    assert_eq!(request.longitude, 139.7671);
    assert_eq!(request.packet_id, 12345);
    assert_eq!(request.version, 1);
}

#[test]
fn test_location_request_serialization() {
    let request = LocationRequest::create_coordinate_lookup(
        35.6812, 139.7671, 12345, true, false, false, false, false, 1, 1
    );
    
    let bytes = request.to_bytes();
    assert!(!bytes.is_empty());
    assert!(bytes.len() >= 16); // Should have at least header
}

#[test]
fn test_checksum_calculation() {
    let data = vec![0x12, 0x34, 0x56, 0x78];
    let checksum = calc_checksum12(&data);
    
    // Checksum should be within 12-bit range (0-4095)
    assert!(checksum <= 0xFFF);
}

#[test]
fn test_checksum_empty_data() {
    let data = vec![];
    let checksum = calc_checksum12(&data);
    
    // Empty data should have checksum 0xFFF (1's complement of 0)
    assert_eq!(checksum, 0xFFF);
}

#[test]
fn test_checksum_verification() {
    // Create a 16-byte header packet (minimum for embed_checksum12_le)
    let mut header = vec![0x12, 0x34, 0x56, 0x78, 0x9A, 0xBC, 0xDE, 0xF0, 
                         0x11, 0x22, 0x33, 0x44, 0x55, 0x66, 0x00, 0x00];
    
    // Embed checksum at fixed position (116..128 bit range)
    embed_checksum12_le(&mut header);
    
    // Verify checksum at bit position 116, length 12
    let is_valid = verify_checksum12(&header, 116, 12);
    assert!(is_valid);
}

#[test]
fn test_checksum_invalid_data() {
    let mut header = vec![0x12, 0x34, 0x56, 0x78, 0x9A, 0xBC, 0xDE, 0xF0, 
                         0x11, 0x22, 0x33, 0x44, 0x55, 0x66, 0x00, 0x00];
    
    // Embed correct checksum
    embed_checksum12_le(&mut header);
    
    // Corrupt the data
    header[0] = 0xFF;
    
    // Verification should fail
    let is_valid = verify_checksum12(&header, 116, 12);
    assert!(!is_valid);
}

#[test]
fn test_multiple_location_requests() {
    let coordinates = vec![
        (35.6812, 139.7671, "Tokyo"),
        (34.6937, 135.5023, "Osaka"),
        (43.0642, 141.3469, "Sapporo"),
        (33.5904, 130.4017, "Fukuoka"),
    ];
    
    for (i, (lat, lon, _city)) in coordinates.iter().enumerate() {
        let request = LocationRequest::create_coordinate_lookup(
            *lat, *lon, i as u16, true, false, false, false, false, 1, 1
        );
        
        assert_eq!(request.latitude, *lat);
        assert_eq!(request.longitude, *lon);
        assert_eq!(request.packet_id, i as u16);
        
        let bytes = request.to_bytes();
        assert!(!bytes.is_empty());
    }
}

#[test]
fn test_checksum_consistency() {
    let data = vec![0x12, 0x34, 0x56, 0x78, 0x9A, 0xBC];
    
    let checksum1 = calc_checksum12(&data);
    let checksum2 = calc_checksum12(&data);
    let checksum3 = calc_checksum12(&data);
    
    assert_eq!(checksum1, checksum2);
    assert_eq!(checksum2, checksum3);
}

#[test]
fn test_checksum_known_values() {
    // Test with known simple values
    let test_cases = vec![
        (vec![0x00], 0xFFF), // ~0 & 0xFFF = 0xFFF
        (vec![0x01], 0xFFE), // ~1 & 0xFFF = 0xFFE
        (vec![0xFF], 0xF00), // ~255 & 0xFFF = 0xF00
    ];
    
    for (data, expected) in test_cases {
        let calculated = calc_checksum12(&data);
        assert_eq!(calculated, expected);
    }
}

#[test]
fn test_large_packet_performance() {
    // Test with a larger packet to ensure performance is reasonable
    let size = 1024;
    let data: Vec<u8> = (0..size).map(|i| (i % 256) as u8).collect();
    
    let start = std::time::Instant::now();
    let _checksum = calc_checksum12(&data);
    let duration = start.elapsed();
    
    // Should complete within reasonable time (less than 10ms for 1KB)
    assert!(duration.as_millis() < 10);
}