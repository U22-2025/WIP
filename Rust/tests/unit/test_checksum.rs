use wip_rust::wip_common_rs::packet::core::checksum::{calc_checksum12, verify_checksum12, embed_checksum12_le};

mod checksum_tests {
    use super::*;

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
        
        // Empty data should still produce valid checksum
        assert!(checksum <= 0xFFF);
    }

    #[test]
    fn test_calc_checksum12_deterministic() {
        let data = vec![0x12, 0x34, 0x56, 0x78];
        let checksum1 = calc_checksum12(&data);
        let checksum2 = calc_checksum12(&data);
        
        // Same data should produce same checksum
        assert_eq!(checksum1, checksum2);
    }

    #[test]
    fn test_calc_checksum12_different_data() {
        let data1 = vec![0x12, 0x34, 0x56, 0x78];
        let data2 = vec![0x87, 0x65, 0x43, 0x21];
        
        let checksum1 = calc_checksum12(&data1);
        let checksum2 = calc_checksum12(&data2);
        
        // Different data should (likely) produce different checksums
        // Note: This is probabilistic, but very likely to be true
        assert_ne!(checksum1, checksum2);
    }

    #[test]
    fn test_embed_and_verify_checksum12() {
        let mut data = vec![0x12, 0x34, 0x56, 0x78, 0x00, 0x00]; // Last 2 bytes for checksum
        
        // Embed checksum
        embed_checksum12_le(&mut data);
        
        // Verify checksum
        assert!(verify_checksum12(&data).is_ok());
    }

    #[test]
    fn test_verify_checksum12_invalid() {
        let mut data = vec![0x12, 0x34, 0x56, 0x78, 0x00, 0x00];
        
        // Embed valid checksum
        embed_checksum12_le(&mut data);
        
        // Corrupt the data
        data[0] = 0xFF;
        
        // Verify should fail
        assert!(verify_checksum12(&data).is_err());
    }

    #[test]
    fn test_verify_checksum12_short_data() {
        let data = vec![0x12]; // Too short for checksum
        
        // Should handle gracefully
        let result = verify_checksum12(&data);
        assert!(result.is_err());
    }

    #[test]
    fn test_checksum12_large_data() {
        let mut data = vec![0xAA; 1000]; // 1KB of data
        data.extend_from_slice(&[0x00, 0x00]); // Space for checksum
        
        embed_checksum12_le(&mut data);
        assert!(verify_checksum12(&data).is_ok());
    }

    #[test]
    fn test_checksum12_edge_cases() {
        // Test with all zeros
        let mut data = vec![0x00; 10];
        embed_checksum12_le(&mut data);
        assert!(verify_checksum12(&data).is_ok());
        
        // Test with all 0xFF
        let mut data = vec![0xFF; 8];
        data.extend_from_slice(&[0x00, 0x00]);
        embed_checksum12_le(&mut data);
        assert!(verify_checksum12(&data).is_ok());
    }

    #[test]
    fn test_checksum12_known_values() {
        // Test with known input/output for regression testing
        let test_cases = vec![
            (vec![0x01, 0x02, 0x00, 0x00], true),  // Simple case
            (vec![0xFF, 0xFF, 0x00, 0x00], true),  // High values
            (vec![0x00, 0x00, 0x00, 0x00], true),  // All zeros
        ];
        
        for (mut data, should_pass) in test_cases {
            embed_checksum12_le(&mut data);
            let result = verify_checksum12(&data);
            assert_eq!(result.is_ok(), should_pass);
        }
    }

    #[test]
    fn test_checksum12_byte_order() {
        // Test that little-endian embedding works correctly
        let mut data = vec![0x12, 0x34, 0x00, 0x00];
        embed_checksum12_le(&mut data);
        
        // The checksum should be embedded in the last 2 bytes in little-endian format
        // We don't test specific values since the checksum algorithm may vary,
        // but we ensure it validates correctly
        assert!(verify_checksum12(&data).is_ok());
        
        // Test that corrupting the checksum bytes fails validation
        data[data.len() - 1] ^= 0x01; // Flip one bit
        assert!(verify_checksum12(&data).is_err());
    }

    #[test]
    fn test_checksum12_multiple_operations() {
        let mut data = vec![0x12, 0x34, 0x56, 0x78, 0x9A, 0xBC, 0x00, 0x00];
        
        // Embed checksum multiple times - should be idempotent when done correctly
        embed_checksum12_le(&mut data);
        let first_checksum = data.clone();
        
        // Clear checksum area and re-embed
        let data_len = data.len();
        data[data_len - 2] = 0x00;
        data[data_len - 1] = 0x00;
        embed_checksum12_le(&mut data);
        
        assert_eq!(data, first_checksum);
        assert!(verify_checksum12(&data).is_ok());
    }
}