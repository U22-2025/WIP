use wip_rust::wip_common_rs::packet::core::bit_utils::{
    extract_bits, set_bits, PacketFields, bytes_to_u128_le, u128_to_bytes_le,
    BitField, create_bit_field
};

/// Comprehensive bit manipulation test suite
/// Tests all bit utilities for correctness, edge cases, and performance
/// Ensures compatibility with WIP packet format requirements

#[cfg(test)]
mod comprehensive_bit_utils_tests {
    use super::*;

    // ============================================================================
    // Basic Bit Extraction Tests
    // ============================================================================

    #[test]
    fn test_extract_bits_single_bit_all_positions() {
        // Test extracting single bits from all positions in a u128
        let test_value = 0xAAAAAAAAAAAAAAAA_u128; // Alternating pattern
        
        for position in 0..128 {
            let bit = extract_bits(test_value, position, 1);
            let expected = if position % 2 == 0 { 0 } else { 1 };
            assert_eq!(bit, expected, "Bit at position {} should be {}", position, expected);
        }
    }

    #[test]
    fn test_extract_bits_various_widths() {
        let data = 0x123456789ABCDEF0_u128;
        
        // Test various bit widths
        let test_cases = vec![
            (0, 4, 0x0),    // Lower 4 bits
            (4, 4, 0xF),    // Next 4 bits  
            (8, 8, 0xEF),   // Full byte
            (0, 16, 0xDEF0), // Lower 16 bits
            (16, 16, 0x9ABC), // Next 16 bits
            (0, 32, 0x9ABCDEF0), // Lower 32 bits
            (32, 32, 0x12345678), // Upper 32 bits
        ];
        
        for (start, width, expected) in test_cases {
            let result = extract_bits(data, start, width);
            assert_eq!(result, expected, 
                "extract_bits({:016X}, {}, {}) = {:X}, expected {:X}", 
                data, start, width, result, expected);
        }
    }

    #[test]
    fn test_extract_bits_full_range() {
        let data = 0x123456789ABCDEF0_u128;
        
        // Extract the full 128 bits
        let result = extract_bits(data, 0, 128);
        assert_eq!(result, data);
        
        // Extract all but one bit
        let result = extract_bits(data, 0, 127);
        assert_eq!(result, data & ((1_u128 << 127) - 1));
    }

    #[test]
    fn test_extract_bits_edge_cases() {
        let data = u128::MAX;
        
        // Extract 0 bits (should return 0)
        let result = extract_bits(data, 0, 0);
        assert_eq!(result, 0);
        
        // Extract from maximum position
        let result = extract_bits(data, 127, 1);
        assert_eq!(result, 1);
        
        // Extract maximum width from position 0
        let result = extract_bits(data, 0, 128);
        assert_eq!(result, u128::MAX);
    }

    #[test]
    fn test_extract_bits_boundary_conditions() {
        // Test at byte boundaries
        let data = 0x123456789ABCDEF0_u128;
        
        let byte_boundaries = vec![0, 8, 16, 24, 32, 40, 48, 56, 64, 72, 80, 88, 96, 104, 112, 120];
        
        for &boundary in &byte_boundaries {
            if boundary + 8 <= 128 {
                let result = extract_bits(data, boundary, 8);
                assert!(result <= 0xFF, "Byte extraction at boundary {} exceeded 8 bits", boundary);
            }
        }
    }

    // ============================================================================
    // Basic Bit Setting Tests
    // ============================================================================

    #[test]
    fn test_set_bits_single_bit_all_positions() {
        let mut data = 0_u128;
        
        // Set every other bit
        for position in (0..128).step_by(2) {
            set_bits(&mut data, position, 1, 1);
        }
        
        // Should result in alternating pattern
        assert_eq!(data, 0x55555555555555555555555555555555_u128);
    }

    #[test]
    fn test_set_bits_various_widths() {
        let mut data = 0_u128;
        
        // Set different width fields
        set_bits(&mut data, 0, 4, 0xF);      // Lower nibble
        set_bits(&mut data, 4, 4, 0xE);      // Next nibble
        set_bits(&mut data, 8, 8, 0xDC);     // Full byte
        set_bits(&mut data, 16, 16, 0xBA98); // 16-bit field
        
        // Verify each field
        assert_eq!(extract_bits(data, 0, 4), 0xF);
        assert_eq!(extract_bits(data, 4, 4), 0xE);
        assert_eq!(extract_bits(data, 8, 8), 0xDC);
        assert_eq!(extract_bits(data, 16, 16), 0xBA98);
    }

    #[test]
    fn test_set_bits_overwrite() {
        let mut data = u128::MAX; // Start with all bits set
        
        // Clear specific ranges
        set_bits(&mut data, 8, 8, 0x00);    // Clear a byte
        set_bits(&mut data, 32, 16, 0x0000); // Clear 16 bits
        set_bits(&mut data, 64, 32, 0x00000000); // Clear 32 bits
        
        // Verify the cleared ranges
        assert_eq!(extract_bits(data, 8, 8), 0x00);
        assert_eq!(extract_bits(data, 32, 16), 0x0000);
        assert_eq!(extract_bits(data, 64, 32), 0x00000000);
        
        // Verify other bits are still set
        assert_eq!(extract_bits(data, 0, 8), 0xFF);
        assert_eq!(extract_bits(data, 16, 16), 0xFFFF);
    }

    #[test]
    fn test_set_bits_edge_cases() {
        let mut data = 0_u128;
        
        // Set 0 bits (should do nothing)
        set_bits(&mut data, 0, 0, 0xFFFF);
        assert_eq!(data, 0);
        
        // Set maximum width
        set_bits(&mut data, 0, 128, u128::MAX);
        assert_eq!(data, u128::MAX);
        
        // Set single bit at maximum position
        let mut data = 0_u128;
        set_bits(&mut data, 127, 1, 1);
        assert_eq!(data, 1_u128 << 127);
    }

    // ============================================================================
    // Round-trip Tests (Extract-Set-Extract)
    // ============================================================================

    #[test]
    fn test_extract_set_roundtrip_comprehensive() {
        let test_patterns = vec![
            0x0000000000000000_u128,
            0xFFFFFFFFFFFFFFFF_u128,
            0xAAAAAAAAAAAAAAAA_u128,
            0x5555555555555555_u128,
            0x123456789ABCDEF0_u128,
            0xFEDCBA0987654321_u128,
        ];
        
        for pattern in test_patterns {
            let mut data = 0_u128;
            
            // Set the pattern in various positions and widths
            for start in (0..64).step_by(8) {
                for width in [4, 8, 16, 32] {
                    if start + width <= 128 {
                        let original_value = extract_bits(pattern, 0, width);
                        set_bits(&mut data, start, width, original_value);
                        let extracted_value = extract_bits(data, start, width);
                        
                        assert_eq!(extracted_value, original_value,
                            "Round-trip failed for pattern {:016X} at start={}, width={}",
                            pattern, start, width);
                    }
                }
            }
        }
    }

    #[test]
    fn test_extract_set_no_interference() {
        let mut data = 0x123456789ABCDEF0_u128;
        let original = data;
        
        // Extract a value, modify it, and set it back
        let extracted = extract_bits(data, 32, 16);
        let modified = extracted ^ 0xFFFF; // Flip all bits
        set_bits(&mut data, 32, 16, modified);
        
        // Verify the change occurred only in the target range
        assert_eq!(extract_bits(data, 32, 16), modified);
        
        // Verify other ranges are unchanged
        assert_eq!(extract_bits(data, 0, 32), extract_bits(original, 0, 32));
        assert_eq!(extract_bits(data, 48, 80), extract_bits(original, 48, 80));
    }

    // ============================================================================
    // PacketFields Tests
    // ============================================================================

    #[test]
    fn test_packet_fields_basic_operations() {
        let mut fields = PacketFields::new();
        
        // Test setting and getting various field types
        fields.set_field("version", 1);
        fields.set_field("packet_id", 12345);
        fields.set_field("timestamp", 1640995200); // Unix timestamp
        fields.set_field("area_code", 130010);
        
        assert_eq!(fields.get_field("version"), Some(1));
        assert_eq!(fields.get_field("packet_id"), Some(12345));
        assert_eq!(fields.get_field("timestamp"), Some(1640995200));
        assert_eq!(fields.get_field("area_code"), Some(130010));
        assert_eq!(fields.get_field("nonexistent"), None);
    }

    #[test]
    fn test_packet_fields_overwrite_and_clear() {
        let mut fields = PacketFields::new();
        
        fields.set_field("test_field", 100);
        assert_eq!(fields.get_field("test_field"), Some(100));
        
        // Overwrite with new value
        fields.set_field("test_field", 200);
        assert_eq!(fields.get_field("test_field"), Some(200));
        
        // Clear the field by removing it
        fields.remove_field("test_field");
        assert_eq!(fields.get_field("test_field"), None);
    }

    #[test]
    fn test_packet_fields_large_values() {
        let mut fields = PacketFields::new();
        
        // Test with maximum values for different bit widths
        fields.set_field("4bit_max", 0xF);
        fields.set_field("8bit_max", 0xFF);
        fields.set_field("12bit_max", 0xFFF);
        fields.set_field("16bit_max", 0xFFFF);
        fields.set_field("32bit_max", 0xFFFFFFFF);
        fields.set_field("64bit_max", 0xFFFFFFFFFFFFFFFF);
        
        assert_eq!(fields.get_field("4bit_max"), Some(0xF));
        assert_eq!(fields.get_field("8bit_max"), Some(0xFF));
        assert_eq!(fields.get_field("12bit_max"), Some(0xFFF));
        assert_eq!(fields.get_field("16bit_max"), Some(0xFFFF));
        assert_eq!(fields.get_field("32bit_max"), Some(0xFFFFFFFF));
        assert_eq!(fields.get_field("64bit_max"), Some(0xFFFFFFFFFFFFFFFF));
    }

    #[test]
    fn test_packet_fields_many_fields() {
        let mut fields = PacketFields::new();
        
        // Add many fields to test capacity and performance
        for i in 0..1000 {
            fields.set_field(&format!("field_{}", i), i as u128);
        }
        
        // Verify all fields
        for i in 0..1000 {
            assert_eq!(fields.get_field(&format!("field_{}", i)), Some(i as u128));
        }
    }

    // ============================================================================
    // Byte Conversion Tests
    // ============================================================================

    #[test]
    fn test_bytes_to_u128_le_various_sizes() {
        let test_cases = vec![
            (vec![], 0_u128),
            (vec![0x12], 0x12_u128),
            (vec![0x12, 0x34], 0x3412_u128),
            (vec![0x12, 0x34, 0x56], 0x563412_u128),
            (vec![0x12, 0x34, 0x56, 0x78], 0x78563412_u128),
        ];
        
        for (bytes, expected) in test_cases {
            let result = bytes_to_u128_le(&bytes);
            assert_eq!(result, expected, 
                "bytes_to_u128_le({:?}) = {:X}, expected {:X}", 
                bytes, result, expected);
        }
    }

    #[test]
    fn test_bytes_to_u128_le_full_width() {
        let bytes = vec![
            0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08,
            0x09, 0x0A, 0x0B, 0x0C, 0x0D, 0x0E, 0x0F, 0x10
        ];
        
        let result = bytes_to_u128_le(&bytes);
        
        // Verify by converting back
        let back_to_bytes = u128_to_bytes_le(result);
        assert_eq!(bytes, back_to_bytes);
    }

    #[test]
    fn test_u128_to_bytes_le_various_values() {
        let test_cases = vec![
            (0_u128, vec![0; 16]),
            (0xFF_u128, {
                let mut v = vec![0xFF];
                v.extend_from_slice(&[0; 15]);
                v
            }),
            (0xFFFF_u128, {
                let mut v = vec![0xFF, 0xFF];
                v.extend_from_slice(&[0; 14]);
                v
            }),
            (u128::MAX, vec![0xFF; 16]),
        ];
        
        for (value, expected) in test_cases {
            let result = u128_to_bytes_le(value);
            assert_eq!(result, expected, 
                "u128_to_bytes_le({:X}) = {:?}, expected {:?}", 
                value, result, expected);
        }
    }

    #[test]
    fn test_byte_conversion_roundtrip() {
        let test_values = vec![
            0_u128,
            1_u128,
            0xFF_u128,
            0xFFFF_u128,
            0xFFFFFFFF_u128,
            0xFFFFFFFFFFFFFFFF_u128,
            u128::MAX,
            0x123456789ABCDEF0FEDCBA0987654321_u128,
        ];
        
        for value in test_values {
            let bytes = u128_to_bytes_le(value);
            let recovered = bytes_to_u128_le(&bytes);
            assert_eq!(value, recovered, "Round-trip failed for value {:X}", value);
        }
    }

    #[test]
    fn test_byte_conversion_truncation() {
        // Test with more than 16 bytes (should truncate)
        let long_bytes = vec![0x12; 20];
        let result = bytes_to_u128_le(&long_bytes);
        
        // Should only use first 16 bytes
        let expected_bytes = vec![0x12; 16];
        let expected = bytes_to_u128_le(&expected_bytes);
        assert_eq!(result, expected);
    }

    // ============================================================================
    // BitField Tests
    // ============================================================================

    #[test]
    fn test_bit_field_creation() {
        let field = create_bit_field("test_field", 0, 8);
        
        assert_eq!(field.name, "test_field");
        assert_eq!(field.start_bit, 0);
        assert_eq!(field.bit_width, 8);
    }

    #[test]
    fn test_bit_field_extraction() {
        let field = create_bit_field("test_field", 8, 8);
        let data = 0x12345678_u128;
        
        let value = field.extract(data);
        assert_eq!(value, 0x56); // Byte at position 8-15
    }

    #[test]
    fn test_bit_field_setting() {
        let field = create_bit_field("test_field", 8, 8);
        let mut data = 0_u128;
        
        field.set(&mut data, 0xAB);
        assert_eq!(extract_bits(data, 8, 8), 0xAB);
        assert_eq!(extract_bits(data, 0, 8), 0x00); // Other bits unchanged
    }

    #[test]
    fn test_bit_field_wip_packet_fields() {
        // Test BitFields for actual WIP packet structure
        let version_field = create_bit_field("version", 0, 4);
        let packet_id_field = create_bit_field("packet_id", 4, 12);
        let type_field = create_bit_field("type", 16, 3);
        let flags_field = create_bit_field("flags", 19, 8);
        
        let mut data = 0_u128;
        
        // Set WIP packet header fields
        version_field.set(&mut data, 1);
        packet_id_field.set(&mut data, 2048);
        type_field.set(&mut data, 2);
        flags_field.set(&mut data, 0b10101010);
        
        // Verify extraction
        assert_eq!(version_field.extract(data), 1);
        assert_eq!(packet_id_field.extract(data), 2048);
        assert_eq!(type_field.extract(data), 2);
        assert_eq!(flags_field.extract(data), 0b10101010);
    }

    // ============================================================================
    // Performance and Stress Tests
    // ============================================================================

    #[test]
    fn test_bit_operations_performance() {
        let mut data = 0x123456789ABCDEF0_u128;
        
        // Perform many bit operations
        for i in 0..1000 {
            let pos = i % 120;
            let width = (i % 8) + 1;
            let value = i % (1 << width);
            
            set_bits(&mut data, pos, width, value as u128);
            let extracted = extract_bits(data, pos, width);
            assert_eq!(extracted, value as u128);
        }
    }

    #[test]
    fn test_packet_fields_performance() {
        let mut fields = PacketFields::new();
        
        // Add many fields quickly
        for i in 0..10000 {
            fields.set_field(&format!("field_{}", i), i as u128);
        }
        
        // Access fields quickly
        for i in 0..10000 {
            assert_eq!(fields.get_field(&format!("field_{}", i)), Some(i as u128));
        }
    }

    #[test]
    fn test_bit_manipulation_thread_safety() {
        use std::sync::Arc;
        use std::sync::atomic::{AtomicU128, Ordering};
        use std::thread;
        
        let counter = Arc::new(AtomicU128::new(0));
        let handles: Vec<_> = (0..4).map(|thread_id| {
            let counter_clone = Arc::clone(&counter);
            
            thread::spawn(move || {
                for i in 0..100 {
                    let value = (thread_id * 100 + i) as u128;
                    
                    // Perform bit operations
                    let mut local_data = value;
                    set_bits(&mut local_data, 8, 8, 0xAA);
                    let extracted = extract_bits(local_data, 8, 8);
                    assert_eq!(extracted, 0xAA);
                    
                    counter_clone.fetch_add(1, Ordering::SeqCst);
                }
            })
        }).collect();
        
        for handle in handles {
            handle.join().unwrap();
        }
        
        assert_eq!(counter.load(Ordering::SeqCst), 400);
    }

    // ============================================================================
    // Error Handling and Edge Cases
    // ============================================================================

    #[test]
    fn test_bit_operations_overflow_protection() {
        let mut data = 0_u128;
        
        // Attempt to set a value larger than the field width allows
        set_bits(&mut data, 0, 4, 0xFFFF); // 16-bit value in 4-bit field
        
        // Should only set the lower 4 bits
        let result = extract_bits(data, 0, 4);
        assert_eq!(result, 0xF); // 0xFFFF & 0xF = 0xF
    }

    #[test]
    fn test_bit_field_validation() {
        // Test BitField with extreme values
        let field = create_bit_field("test", 120, 8); // Near the end of u128
        let mut data = 0_u128;
        
        field.set(&mut data, 0xFF);
        assert_eq!(field.extract(data), 0xFF);
    }

    #[test]
    fn test_byte_conversion_edge_cases() {
        // Test with exact 16-byte input
        let bytes = (0..16).collect::<Vec<u8>>();
        let value = bytes_to_u128_le(&bytes);
        let back_bytes = u128_to_bytes_le(value);
        assert_eq!(bytes, back_bytes);
        
        // Test with empty input
        let empty_bytes = vec![];
        let value = bytes_to_u128_le(&empty_bytes);
        assert_eq!(value, 0);
    }

    #[test]
    fn test_bit_operations_mathematical_properties() {
        let data = 0x123456789ABCDEF0_u128;
        
        // Test that extracting and setting the same range preserves data
        for start in (0..64).step_by(8) {
            for width in [4, 8, 16] {
                if start + width <= 128 {
                    let original = extract_bits(data, start, width);
                    let mut modified = data;
                    set_bits(&mut modified, start, width, original);
                    assert_eq!(modified, data, 
                        "Identity operation failed at start={}, width={}", start, width);
                }
            }
        }
    }
}