use wip_rust::wip_common_rs::packet::core::bit_utils::{
    extract_bits, set_bits, PacketFields, bytes_to_u128_le, u128_to_bytes_le
};

#[test]
fn test_extract_bits_basic() {
    let data = 0b11010110_u8; // 214 in decimal
    
    // Extract first 4 bits (should be 0110 = 6)
    let result = extract_bits(data as u128, 0, 4);
    assert_eq!(result, 6);
    
    // Extract last 4 bits (should be 1101 = 13)
    let result = extract_bits(data as u128, 4, 4);
    assert_eq!(result, 13);
}

#[test]
fn test_extract_bits_edge_cases() {
    let data = 0xFFFFFFFF_u32;
    
    // Extract single bit
    let result = extract_bits(data as u128, 0, 1);
    assert_eq!(result, 1);
    
    // Extract all bits
    let result = extract_bits(data as u128, 0, 32);
    assert_eq!(result, 0xFFFFFFFF);
    
    // Extract zero bits
    let result = extract_bits(data as u128, 0, 0);
    assert_eq!(result, 0);
}

#[test]
fn test_set_bits_basic() {
    let mut data = 0_u128;
    
    // Set first 4 bits to 0xF
    set_bits(&mut data, 0, 4, 0xF);
    assert_eq!(data & 0xF, 0xF);
    
    // Set next 4 bits to 0xA
    set_bits(&mut data, 4, 4, 0xA);
    assert_eq!((data >> 4) & 0xF, 0xA);
    assert_eq!(data & 0xFF, 0xAF);
}

#[test]
fn test_set_bits_overwrite() {
    let mut data = 0xFFFFFFFF_u128;
    
    // Overwrite middle bits
    set_bits(&mut data, 8, 8, 0x00);
    
    // Check that middle 8 bits are now 0
    let middle_bits = extract_bits(data, 8, 8);
    assert_eq!(middle_bits, 0x00);
    
    // Check that other bits are still 1
    let lower_bits = extract_bits(data, 0, 8);
    let upper_bits = extract_bits(data, 16, 16);
    assert_eq!(lower_bits, 0xFF);
    assert_eq!(upper_bits, 0xFFFF);
}

#[test]
fn test_bytes_to_u128_le() {
    let bytes = vec![0x12, 0x34, 0x56, 0x78];
    let result = bytes_to_u128_le(&bytes);
    
    // Little endian: 0x78563412
    let expected = 0x78563412_u128;
    assert_eq!(result, expected);
}

#[test]
fn test_bytes_to_u128_le_single_byte() {
    let bytes = vec![0xFF];
    let result = bytes_to_u128_le(&bytes);
    assert_eq!(result, 0xFF);
}

#[test]
fn test_bytes_to_u128_le_empty() {
    let bytes = vec![];
    let result = bytes_to_u128_le(&bytes);
    assert_eq!(result, 0);
}

#[test]
fn test_u128_to_bytes_le() {
    let value = 0x12345678_u128;
    let bytes = u128_to_bytes_le(value);
    
    // Should produce little-endian bytes
    let expected = vec![0x78, 0x56, 0x34, 0x12];
    assert_eq!(bytes, expected);
}

#[test]
fn test_u128_to_bytes_le_zero() {
    let value = 0_u128;
    let bytes = u128_to_bytes_le(value);
    assert_eq!(bytes, vec![0]);
}

#[test]
fn test_u128_to_bytes_le_single_byte() {
    let value = 0xFF_u128;
    let bytes = u128_to_bytes_le(value);
    assert_eq!(bytes, vec![0xFF]);
}

#[test]
fn test_round_trip_bytes_conversion() {
    let original_bytes = vec![0x12, 0x34, 0x56, 0x78, 0x9A, 0xBC, 0xDE, 0xF0];
    
    // Convert to u128 and back
    let value = bytes_to_u128_le(&original_bytes);
    let converted_bytes = u128_to_bytes_le(value);
    
    assert_eq!(original_bytes, converted_bytes);
}

#[test]
fn test_packet_fields_creation() {
    let mut fields = PacketFields::new();
    
    // Test field operations
    fields.set_field("latitude", 0, 32, 0x12345678);
    fields.set_field("longitude", 32, 32, 0x87654321);
    
    // Verify field values
    assert_eq!(fields.get_field("latitude"), Some(0x12345678));
    assert_eq!(fields.get_field("longitude"), Some(0x87654321));
}

#[test]
fn test_packet_fields_bit_extraction() {
    let mut fields = PacketFields::new();
    
    // Set overlapping fields to test bit extraction
    fields.set_field("field1", 0, 16, 0xABCD);
    fields.set_field("field2", 8, 16, 0x1234);
    
    // field1 should be in lower 16 bits
    assert_eq!(fields.get_field("field1"), Some(0xABCD));
    
    // field2 should overlap with field1
    assert_eq!(fields.get_field("field2"), Some(0x1234));
}

#[test]
fn test_bit_manipulation_edge_cases() {
    // Test maximum bit positions
    let mut data = 0_u128;
    
    // Set the highest bit
    set_bits(&mut data, 127, 1, 1);
    assert_eq!(extract_bits(data, 127, 1), 1);
    
    // Set multiple high bits
    set_bits(&mut data, 120, 8, 0xFF);
    assert_eq!(extract_bits(data, 120, 8), 0xFF);
}

#[test]
fn test_bit_field_consistency() {
    let mut fields = PacketFields::new();
    
    // Test that setting and getting fields is consistent
    let test_cases = vec![
        ("field1", 0, 8, 0xFF),
        ("field2", 8, 16, 0x1234),
        ("field3", 24, 12, 0xABC),
        ("field4", 36, 20, 0x12345),
    ];
    
    for (name, offset, width, value) in &test_cases {
        fields.set_field(name, *offset, *width, *value);
    }
    
    for (name, _offset, _width, expected_value) in test_cases {
        assert_eq!(fields.get_field(&name), Some(expected_value));
    }
}

#[test]
fn test_large_bit_operations() {
    // Test with large values to ensure no overflow
    let mut data = 0_u128;
    let large_value = 0xFFFFFFFFFFFFFFF_u128; // 60 bits of 1s
    
    set_bits(&mut data, 0, 60, large_value);
    let extracted = extract_bits(data, 0, 60);
    
    assert_eq!(extracted, large_value);
}