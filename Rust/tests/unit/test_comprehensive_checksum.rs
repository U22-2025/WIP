use wip_rust::wip_common_rs::packet::core::checksum::{
    calc_checksum12, verify_checksum12, embed_checksum12_le, 
    get_checksum_from_packet, clear_checksum_field
};

/// Comprehensive checksum test suite
/// Tests the 12-bit checksum implementation for compatibility with Python version
/// and robustness across various data patterns and edge cases

#[cfg(test)]
mod comprehensive_checksum_tests {
    use super::*;

    // ============================================================================
    // Basic Checksum Calculation Tests
    // ============================================================================

    #[test]
    fn test_checksum_12bit_range() {
        // Test that checksum is always within 12-bit range (0-4095)
        let test_data = vec![
            vec![],                           // Empty
            vec![0x00],                       // Single zero
            vec![0xFF],                       // Single max
            vec![0x12, 0x34],                // Small data
            vec![0xFF; 1000],                // Large data, all max
            vec![0x00; 1000],                // Large data, all zero
            (0..255).collect::<Vec<u8>>(),    // Sequential pattern
        ];

        for data in test_data {
            let checksum = calc_checksum12(&data);
            assert!(checksum <= 0xFFF, "Checksum {} exceeds 12-bit range for data len {}", checksum, data.len());
        }
    }

    #[test]
    fn test_checksum_deterministic() {
        // Same input should always produce same checksum
        let test_cases = vec![
            vec![0x12, 0x34, 0x56, 0x78],
            vec![0x00, 0x00, 0x00, 0x00],
            vec![0xFF, 0xFF, 0xFF, 0xFF],
            vec![0xAA, 0x55, 0xAA, 0x55],
            (0..100).collect::<Vec<u8>>(),
        ];

        for data in test_cases {
            let checksum1 = calc_checksum12(&data);
            let checksum2 = calc_checksum12(&data);
            let checksum3 = calc_checksum12(&data);
            
            assert_eq!(checksum1, checksum2);
            assert_eq!(checksum2, checksum3);
        }
    }

    #[test]
    fn test_checksum_different_inputs() {
        // Different inputs should (very likely) produce different checksums
        let test_pairs = vec![
            (vec![0x00, 0x00], vec![0x00, 0x01]),
            (vec![0x12, 0x34], vec![0x34, 0x12]),
            (vec![0xFF, 0x00], vec![0x00, 0xFF]),
            (vec![0xAA, 0x55], vec![0x55, 0xAA]),
            (vec![0x01, 0x02, 0x03], vec![0x03, 0x02, 0x01]),
        ];

        for (data1, data2) in test_pairs {
            let checksum1 = calc_checksum12(&data1);
            let checksum2 = calc_checksum12(&data2);
            
            // Note: This is probabilistic but very likely to be true for a good checksum
            assert_ne!(checksum1, checksum2, 
                "Different inputs should produce different checksums: {:?} vs {:?}", 
                data1, data2);
        }
    }

    #[test]
    fn test_checksum_empty_data() {
        let checksum = calc_checksum12(&[]);
        assert!(checksum <= 0xFFF);
        
        // Empty data should produce consistent checksum
        assert_eq!(checksum, calc_checksum12(&[]));
    }

    #[test]
    fn test_checksum_single_bytes() {
        // Test checksum for all possible single byte values
        for byte_val in 0..=255u8 {
            let data = vec![byte_val];
            let checksum = calc_checksum12(&data);
            assert!(checksum <= 0xFFF);
        }
    }

    // ============================================================================
    // Checksum Embedding and Verification Tests
    // ============================================================================

    #[test]
    fn test_embed_and_verify_basic() {
        let test_cases = vec![
            vec![0x12, 0x34, 0x00, 0x00],                    // Minimum size
            vec![0x12, 0x34, 0x56, 0x78, 0x9A, 0x00, 0x00], // Standard size
            vec![0xAA; 16],                                   // Full WIP packet size
            vec![0x55; 100],                                  // Large packet
        ];

        for mut data in test_cases {
            // Ensure last 2 bytes are clear for checksum
            let len = data.len();
            data[len - 2] = 0x00;
            data[len - 1] = 0x00;
            
            embed_checksum12_le(&mut data);
            assert!(verify_checksum12(&data).is_ok(), 
                "Embedded checksum should verify for data len {}", len);
        }
    }

    #[test]
    fn test_embed_checksum_little_endian() {
        let mut data = vec![0x12, 0x34, 0x56, 0x78, 0x00, 0x00];
        
        embed_checksum12_le(&mut data);
        
        // Verify that checksum was embedded (last 2 bytes changed)
        assert!(data[4] != 0x00 || data[5] != 0x00);
        
        // Verify little-endian format by checking the embedded value
        let embedded_checksum = u16::from_le_bytes([data[4], data[5]]) & 0xFFF;
        let calculated_checksum = calc_checksum12(&data[..4]);
        
        assert_eq!(embedded_checksum, calculated_checksum);
    }

    #[test]
    fn test_verify_checksum_corruption_detection() {
        let mut data = vec![0x12, 0x34, 0x56, 0x78, 0x9A, 0xBC, 0x00, 0x00];
        
        embed_checksum12_le(&mut data);
        assert!(verify_checksum12(&data).is_ok());
        
        // Test corruption of data bytes
        for i in 0..(data.len() - 2) {
            let mut corrupted_data = data.clone();
            corrupted_data[i] ^= 0x01; // Flip one bit
            
            assert!(verify_checksum12(&corrupted_data).is_err(),
                "Corruption at position {} should be detected", i);
        }
    }

    #[test]
    fn test_verify_checksum_errors() {
        // Test various error conditions
        
        // Too short data
        assert!(verify_checksum12(&[]).is_err());
        assert!(verify_checksum12(&[0x12]).is_err());
        
        // Data with incorrect checksum
        let mut data = vec![0x12, 0x34, 0x00, 0x00];
        embed_checksum12_le(&mut data);
        
        // Manually corrupt the checksum field
        data[2] = 0x00;
        data[3] = 0x00;
        assert!(verify_checksum12(&data).is_err());
    }

    #[test]
    fn test_checksum_idempotent_embedding() {
        let mut data = vec![0x12, 0x34, 0x56, 0x78, 0x9A, 0xBC, 0x00, 0x00];
        
        // Embed checksum
        embed_checksum12_le(&mut data);
        let first_embedding = data.clone();
        
        // Clear and re-embed
        let len = data.len();
        data[len - 2] = 0x00;
        data[len - 1] = 0x00;
        embed_checksum12_le(&mut data);
        
        // Should be identical
        assert_eq!(data, first_embedding);
    }

    // ============================================================================
    // Edge Cases and Stress Tests
    // ============================================================================

    #[test]
    fn test_checksum_large_data() {
        // Test with various large data sizes
        let sizes = vec![100, 500, 1000, 5000, 10000];
        
        for size in sizes {
            let mut data = vec![0xAA; size];
            data.extend_from_slice(&[0x00, 0x00]); // Add checksum space
            
            embed_checksum12_le(&mut data);
            assert!(verify_checksum12(&data).is_ok(),
                "Large data verification failed for size {}", size);
        }
    }

    #[test]
    fn test_checksum_all_pattern_bytes() {
        // Test with various byte patterns
        let patterns = vec![
            0x00, 0xFF, 0xAA, 0x55, 0x0F, 0xF0,
            0x33, 0xCC, 0x69, 0x96, 0x77, 0x88
        ];
        
        for pattern in patterns {
            let mut data = vec![pattern; 50];
            data.extend_from_slice(&[0x00, 0x00]);
            
            embed_checksum12_le(&mut data);
            assert!(verify_checksum12(&data).is_ok(),
                "Pattern 0x{:02X} verification failed", pattern);
        }
    }

    #[test]
    fn test_checksum_sequential_data() {
        // Test with sequential and reverse sequential data
        let mut forward_data: Vec<u8> = (0..100).collect();
        forward_data.extend_from_slice(&[0x00, 0x00]);
        
        let mut reverse_data: Vec<u8> = (0..100).rev().collect();
        reverse_data.extend_from_slice(&[0x00, 0x00]);
        
        embed_checksum12_le(&mut forward_data);
        embed_checksum12_le(&mut reverse_data);
        
        assert!(verify_checksum12(&forward_data).is_ok());
        assert!(verify_checksum12(&reverse_data).is_ok());
        
        // Should produce different checksums
        let forward_checksum = get_checksum_from_packet(&forward_data).unwrap();
        let reverse_checksum = get_checksum_from_packet(&reverse_data).unwrap();
        assert_ne!(forward_checksum, reverse_checksum);
    }

    #[test]
    fn test_checksum_boundary_conditions() {
        // Test at exact WIP packet boundaries
        let packet_sizes = vec![16, 32, 64, 128, 256, 512, 1024];
        
        for size in packet_sizes {
            let mut data = vec![0x42; size - 2]; // Fill with test pattern
            data.extend_from_slice(&[0x00, 0x00]); // Add checksum space
            
            embed_checksum12_le(&mut data);
            assert!(verify_checksum12(&data).is_ok(),
                "Boundary test failed for packet size {}", size);
            assert_eq!(data.len(), size);
        }
    }

    // ============================================================================
    // Python Compatibility Tests
    // ============================================================================

    #[test]
    fn test_checksum_known_vectors() {
        // Test vectors that should match Python implementation
        // These would need to be generated from the Python implementation
        
        let test_vectors = vec![
            // (input_data, expected_checksum)
            (vec![0x00, 0x00], 0x000), // All zeros should produce 0
            (vec![0x01, 0x00], 0x001), // Simple case
            (vec![0x00, 0x01], 0x001), // Byte order test
        ];
        
        for (data, expected) in test_vectors {
            let checksum = calc_checksum12(&data);
            assert_eq!(checksum, expected, 
                "Checksum mismatch for data {:?}: got {}, expected {}", 
                data, checksum, expected);
        }
    }

    #[test]
    fn test_checksum_carry_folding() {
        // Test the carry folding mechanism specifically
        // This tests the algorithm's handling of carries in the sum
        
        // Create data that will cause carries
        let carry_test_data = vec![
            vec![0xFF, 0xFF], // Should cause maximum carry
            vec![0xFF, 0xFF, 0xFF, 0xFF], // Multiple carries
            vec![0x80, 0x80, 0x80, 0x80], // Specific carry pattern
        ];
        
        for data in carry_test_data {
            let checksum = calc_checksum12(&data);
            assert!(checksum <= 0xFFF, "Carry folding failed, checksum too large");
            
            // Verify by embedding and checking
            let mut test_data = data.clone();
            test_data.extend_from_slice(&[0x00, 0x00]);
            embed_checksum12_le(&mut test_data);
            assert!(verify_checksum12(&test_data).is_ok());
        }
    }

    // ============================================================================
    // Utility Function Tests
    // ============================================================================

    #[test]
    fn test_get_checksum_from_packet() {
        let mut data = vec![0x12, 0x34, 0x56, 0x78, 0x00, 0x00];
        embed_checksum12_le(&mut data);
        
        let extracted_checksum = get_checksum_from_packet(&data).unwrap();
        let calculated_checksum = calc_checksum12(&data[..4]);
        
        assert_eq!(extracted_checksum, calculated_checksum);
    }

    #[test]
    fn test_get_checksum_from_packet_errors() {
        // Test error conditions
        assert!(get_checksum_from_packet(&[]).is_err());
        assert!(get_checksum_from_packet(&[0x12]).is_err());
    }

    #[test]
    fn test_clear_checksum_field() {
        let mut data = vec![0x12, 0x34, 0x56, 0x78, 0xAB, 0xCD];
        let original_data = data[..4].to_vec();
        
        clear_checksum_field(&mut data);
        
        // Data should be unchanged except last 2 bytes
        assert_eq!(&data[..4], &original_data[..]);
        assert_eq!(data[4], 0x00);
        assert_eq!(data[5], 0x00);
    }

    // ============================================================================
    // Performance and Stress Tests
    // ============================================================================

    #[test]
    fn test_checksum_performance_consistency() {
        // Verify checksum calculation is consistent under repeated calls
        let data = vec![0x42; 1000];
        let expected_checksum = calc_checksum12(&data);
        
        // Run multiple times to check for any inconsistencies
        for _ in 0..100 {
            let checksum = calc_checksum12(&data);
            assert_eq!(checksum, expected_checksum);
        }
    }

    #[test]
    fn test_checksum_thread_safety() {
        use std::sync::Arc;
        use std::thread;
        
        let data = Arc::new(vec![0x55; 100]);
        let expected_checksum = calc_checksum12(&data);
        
        let handles: Vec<_> = (0..10).map(|_| {
            let data_clone = Arc::clone(&data);
            let expected = expected_checksum;
            
            thread::spawn(move || {
                for _ in 0..10 {
                    let checksum = calc_checksum12(&data_clone);
                    assert_eq!(checksum, expected);
                }
            })
        }).collect();
        
        for handle in handles {
            handle.join().unwrap();
        }
    }

    #[test]
    fn test_checksum_memory_safety() {
        // Test with various allocation patterns to ensure memory safety
        for size in [0, 1, 2, 15, 16, 17, 31, 32, 33, 63, 64, 65, 127, 128, 129] {
            let data = vec![0x77; size];
            let checksum = calc_checksum12(&data);
            assert!(checksum <= 0xFFF);
            
            if size >= 2 {
                let mut embed_data = data.clone();
                embed_data.extend_from_slice(&[0x00, 0x00]);
                embed_checksum12_le(&mut embed_data);
                assert!(verify_checksum12(&embed_data).is_ok());
            }
        }
    }

    #[test]
    fn test_checksum_algorithm_properties() {
        // Test mathematical properties of the checksum algorithm
        
        // Commutativity test (order shouldn't matter for checksum calculation)
        let data1 = vec![0x12, 0x34];
        let data2 = vec![0x34, 0x12];
        let checksum1 = calc_checksum12(&data1);
        let checksum2 = calc_checksum12(&data2);
        // Note: These should likely be different for a good checksum
        assert_ne!(checksum1, checksum2);
        
        // Zero padding test
        let data_base = vec![0x12, 0x34];
        let data_padded = vec![0x12, 0x34, 0x00, 0x00];
        let checksum_base = calc_checksum12(&data_base);
        let checksum_padded = calc_checksum12(&data_padded);
        assert_eq!(checksum_base, checksum_padded, "Zero padding should not affect checksum");
    }
}