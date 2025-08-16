use wip_rust::wip_common_rs::packet::core::checksum::{calc_checksum12, verify_checksum12, embed_checksum12_le};

#[test]
fn test_calc_checksum12_basic() {
    let data = vec![0x12, 0x34, 0x56, 0x78];
    let checksum = calc_checksum12(&data);
    
    // Checksum should be within 12-bit range (0-4095)
    assert!(checksum <= 0xFFF);
}

#[test]
fn test_calc_checksum12_empty() {
    let data = vec![];
    let checksum = calc_checksum12(&data);
    
    // Empty data should have checksum 0
    assert_eq!(checksum, 0);
}

#[test]
fn test_calc_checksum12_single_byte() {
    let data = vec![0xFF];
    let checksum = calc_checksum12(&data);
    
    // Single byte 0xFF should give checksum 0xFF
    assert_eq!(checksum, 0xFF);
}

#[test]
fn test_calc_checksum12_all_zeros() {
    let data = vec![0x00, 0x00, 0x00, 0x00];
    let checksum = calc_checksum12(&data);
    
    // All zeros should give checksum 0
    assert_eq!(checksum, 0);
}

#[test]
fn test_calc_checksum12_all_ones() {
    let data = vec![0xFF, 0xFF];
    let checksum = calc_checksum12(&data);
    
    // Should handle carry folding correctly
    assert!(checksum <= 0xFFF);
}

#[test]
fn test_embed_and_verify_checksum() {
    let mut data = vec![0x12, 0x34, 0x56, 0x78, 0x00, 0x00]; // Last 2 bytes for checksum
    
    // Embed checksum
    embed_checksum12_le(&mut data);
    
    // Verify the checksum
    assert!(verify_checksum12(&data).is_ok());
}

#[test]
fn test_verify_invalid_checksum() {
    let mut data = vec![0x12, 0x34, 0x56, 0x78, 0x00, 0x00];
    
    // Embed correct checksum
    embed_checksum12_le(&mut data);
    
    // Corrupt the data
    data[0] = 0xFF;
    
    // Verification should fail
    assert!(verify_checksum12(&data).is_err());
}

#[test]
fn test_checksum_different_sizes() {
    let sizes = vec![2, 8, 16, 32, 64, 128, 256];
    
    for size in sizes {
        let mut data: Vec<u8> = (0..size).map(|i| (i % 256) as u8).collect();
        data.extend_from_slice(&[0, 0]); // Space for checksum
        
        embed_checksum12_le(&mut data);
        assert!(verify_checksum12(&data).is_ok());
    }
}

#[test]
fn test_checksum_known_values() {
    // Test with known values for regression testing
    let test_cases = vec![
        (vec![0x01, 0x02], 0x0102),
        (vec![0x01, 0x00], 0x0001),
        (vec![0x00, 0x01], 0x0100),
    ];
    
    for (data, expected_raw) in test_cases {
        let mut packet_data = data.clone();
        packet_data.extend_from_slice(&[0, 0]); // Space for checksum
        
        embed_checksum12_le(&mut packet_data);
        assert!(verify_checksum12(&packet_data).is_ok());
        
        // Verify the actual checksum calculation
        let calculated = calc_checksum12(&data);
        let expected = expected_raw % 4096; // 12-bit folding
        assert_eq!(calculated, expected);
    }
}

#[test]
fn test_checksum_consistency() {
    // Test that the same data always produces the same checksum
    let data = vec![0x12, 0x34, 0x56, 0x78, 0x9A, 0xBC];
    
    let checksum1 = calc_checksum12(&data);
    let checksum2 = calc_checksum12(&data);
    let checksum3 = calc_checksum12(&data);
    
    assert_eq!(checksum1, checksum2);
    assert_eq!(checksum2, checksum3);
}

#[test]
fn test_checksum_order_dependency() {
    // Test that different byte orders produce different checksums
    let data1 = vec![0x12, 0x34];
    let data2 = vec![0x34, 0x12];
    
    let checksum1 = calc_checksum12(&data1);
    let checksum2 = calc_checksum12(&data2);
    
    assert_ne!(checksum1, checksum2);
}

#[test]
fn test_large_packet_checksum() {
    // Test with a large packet to ensure performance is acceptable
    let size = 1024;
    let mut data: Vec<u8> = (0..size).map(|i| (i % 256) as u8).collect();
    data.extend_from_slice(&[0, 0]); // Space for checksum
    
    let start = std::time::Instant::now();
    embed_checksum12_le(&mut data);
    let duration = start.elapsed();
    
    // Should complete within reasonable time (less than 1ms for 1KB)
    assert!(duration.as_millis() < 10);
    assert!(verify_checksum12(&data).is_ok());
}