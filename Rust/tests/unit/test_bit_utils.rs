use wip_rust::wip_common_rs::packet::core::bit_utils::{
    extract_bits, set_bits, PacketFields, bytes_to_u128_le, u128_to_bytes_le
};

mod bit_utils_tests {
    use super::*;

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
    fn test_extract_bits_single_bit() {
        let data = 0b10101010_u8;
        
        for i in 0..8 {
            let bit = extract_bits(data as u128, i, 1);
            let expected = if i % 2 == 0 { 0 } else { 1 };
            assert_eq!(bit, expected, "Bit {} should be {}", i, expected);
        }
    }

    #[test]
    fn test_extract_bits_full_byte() {
        let data = 0xAB_u8;
        let result = extract_bits(data as u128, 0, 8);
        assert_eq!(result, 0xAB);
    }

    #[test]
    fn test_extract_bits_cross_byte_boundary() {
        let data = 0x1234_u16;
        
        // Extract middle 8 bits (bits 4-11)
        let result = extract_bits(data as u128, 4, 8);
        // 0x1234 = 0001001000110100
        // bits 4-11: 00100011 = 0x23 = 35
        assert_eq!(result, 0x23);
    }

    #[test]
    fn test_set_bits_basic() {
        let mut data = 0u128;
        
        // Set bits 0-3 to 0xA (1010)
        set_bits(&mut data, 0, 4, 0xA);
        assert_eq!(data & 0xF, 0xA);
        
        // Set bits 4-7 to 0x5 (0101)
        set_bits(&mut data, 4, 4, 0x5);
        assert_eq!((data >> 4) & 0xF, 0x5);
        assert_eq!(data & 0xFF, 0x5A);
    }

    #[test]
    fn test_set_bits_full_byte() {
        let mut data = 0u128;
        set_bits(&mut data, 0, 8, 0xFF);
        assert_eq!(data & 0xFF, 0xFF);
    }

    #[test]
    fn test_set_bits_overwrite() {
        let mut data = 0xFFFFFFFF_u128;
        
        // Set middle 8 bits to 0
        set_bits(&mut data, 8, 8, 0);
        
        // Should have 0xFF00FFFF pattern in the lower 32 bits
        assert_eq!(data & 0xFFFFFFFF, 0xFF00FFFF);
    }

    #[test]
    fn test_extract_set_round_trip() {
        let mut data = 0u128;
        let test_value = 0b10110011;
        
        // Set some bits
        set_bits(&mut data, 8, 8, test_value);
        
        // Extract them back
        let extracted = extract_bits(data, 8, 8);
        assert_eq!(extracted, test_value);
    }

    #[test]
    fn test_packet_fields_basic() {
        let mut fields = PacketFields::new();
        
        // Test setting and getting basic fields
        fields.set_field("test_field", 42);
        assert_eq!(fields.get_field("test_field"), Some(42));
        
        // Test non-existent field
        assert_eq!(fields.get_field("nonexistent"), None);
    }

    #[test]
    fn test_packet_fields_multiple() {
        let mut fields = PacketFields::new();
        
        fields.set_field("field1", 100);
        fields.set_field("field2", 200);
        fields.set_field("field3", 300);
        
        assert_eq!(fields.get_field("field1"), Some(100));
        assert_eq!(fields.get_field("field2"), Some(200));
        assert_eq!(fields.get_field("field3"), Some(300));
    }

    #[test]
    fn test_packet_fields_overwrite() {
        let mut fields = PacketFields::new();
        
        fields.set_field("test", 42);
        assert_eq!(fields.get_field("test"), Some(42));
        
        fields.set_field("test", 84);
        assert_eq!(fields.get_field("test"), Some(84));
    }

    #[test]
    fn test_bytes_to_u128_le() {
        let bytes = vec![0x12, 0x34, 0x56, 0x78];
        let result = bytes_to_u128_le(&bytes);
        
        // Little-endian: 0x78563412
        let expected = 0x78563412_u128;
        assert_eq!(result, expected);
    }

    #[test]
    fn test_bytes_to_u128_le_full() {
        let bytes = vec![
            0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08,
            0x09, 0x0A, 0x0B, 0x0C, 0x0D, 0x0E, 0x0F, 0x10
        ];
        let result = bytes_to_u128_le(&bytes);
        
        // Should handle all 16 bytes correctly
        assert_ne!(result, 0);
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
        
        // Should get little-endian byte representation
        assert_eq!(bytes[0], 0x78);
        assert_eq!(bytes[1], 0x56);
        assert_eq!(bytes[2], 0x34);
        assert_eq!(bytes[3], 0x12);
        
        // Rest should be zero
        for i in 4..16 {
            assert_eq!(bytes[i], 0);
        }
    }

    #[test]
    fn test_u128_bytes_round_trip() {
        let original = 0x123456789ABCDEF0_u128;
        let bytes = u128_to_bytes_le(original);
        let recovered = bytes_to_u128_le(&bytes);
        assert_eq!(original, recovered);
    }

    #[test]
    fn test_u128_bytes_round_trip_max() {
        let original = u128::MAX;
        let bytes = u128_to_bytes_le(original);
        let recovered = bytes_to_u128_le(&bytes);
        assert_eq!(original, recovered);
    }

    #[test]
    fn test_bit_manipulation_edge_cases() {
        // Test with maximum values
        let mut data = u128::MAX;
        
        // Clear some bits
        set_bits(&mut data, 64, 32, 0);
        
        // Extract the cleared bits
        let result = extract_bits(data, 64, 32);
        assert_eq!(result, 0);
        
        // Extract non-cleared bits
        let result = extract_bits(data, 0, 32);
        assert_eq!(result, u32::MAX as u128);
    }

    #[test]
    fn test_bit_alignment() {
        let mut data = 0u128;
        
        // Test bit operations at various alignments
        for offset in [0, 1, 7, 8, 15, 16, 31, 32, 63, 64] {
            set_bits(&mut data, offset, 8, 0xAA);
            let extracted = extract_bits(data, offset, 8);
            assert_eq!(extracted, 0xAA, "Failed at offset {}", offset);
            
            // Clear for next test
            set_bits(&mut data, offset, 8, 0);
        }
    }

    #[test]
    fn test_large_bit_operations() {
        let mut data = 0u128;
        
        // Set 64 bits at once
        set_bits(&mut data, 0, 64, u64::MAX as u128);
        let extracted = extract_bits(data, 0, 64);
        assert_eq!(extracted, u64::MAX as u128);
        
        // Set another 64 bits
        set_bits(&mut data, 64, 64, 0x123456789ABCDEF0);
        let extracted = extract_bits(data, 64, 64);
        assert_eq!(extracted, 0x123456789ABCDEF0);
    }
}