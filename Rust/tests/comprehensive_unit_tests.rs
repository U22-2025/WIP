/*!
 * 包括的単体テストスイート
 * Phase 5対応 - 全パケット型、チェックサム、ビット操作の完全テスト
 */

use std::time::{SystemTime, UNIX_EPOCH};
use wip_rust::wip_common_rs::packet::core::bit_utils::*;
use wip_rust::wip_common_rs::packet::core::checksum::*;
use wip_rust::wip_common_rs::packet::core::exceptions::*;
use wip_rust::wip_common_rs::packet::types::location_packet::*;
use wip_rust::wip_common_rs::packet::types::query_packet::*;
use wip_rust::wip_common_rs::packet::types::report_packet::*;
use wip_rust::wip_common_rs::packet::types::error_response::*;
use wip_rust::wip_common_rs::packet::core::extended_field::*;

/// チェックサム機能の包括的テスト
#[cfg(test)]
mod checksum_comprehensive_tests {
    use super::*;

    #[test]
    fn test_checksum_edge_cases() {
        // 空データ
        let empty_data = [];
        let checksum = calc_checksum12(&empty_data);
        assert_eq!(checksum, 0xFFF);

        // 全ゼロ
        let zero_data = [0x00; 16];
        let checksum = calc_checksum12(&zero_data);
        assert_eq!(checksum, 0xFFF);

        // 全1
        let full_data = [0xFF; 16];
        let checksum = calc_checksum12(&full_data);
        assert!(checksum <= 0xFFF);
    }

    #[test]
    fn test_checksum_carry_folding() {
        // 大きな値でキャリーフォールドをテスト
        let large_data = [0xFF; 32];
        let checksum = calc_checksum12(&large_data);
        assert!(checksum <= 0xFFF);
        assert!(checksum > 0);
    }

    #[test]
    fn test_checksum_embed_and_verify() {
        let mut packet = vec![0x12, 0x34, 0x56, 0x78, 0x9A, 0xBC, 0xDE, 0xF0,
                             0x11, 0x22, 0x33, 0x44, 0x55, 0x66, 0x77, 0x88];
        
        // チェックサムを埋め込み
        embed_checksum12_at(&mut packet, 116, 12);
        
        // 検証
        assert!(verify_checksum12(&packet, 116, 12));
    }

    #[test]
    fn test_variable_length_checksum() {
        let mut long_packet = vec![0u8; 64];
        for (i, byte) in long_packet.iter_mut().enumerate() {
            *byte = (i % 256) as u8;
        }

        // 異なる位置にチェックサムを埋め込み
        embed_checksum12_at(&mut long_packet, 200, 12);
        assert!(verify_checksum12(&long_packet, 200, 12));
    }
}

/// ビット操作機能の包括的テスト
#[cfg(test)]
mod bit_utils_comprehensive_tests {
    use super::*;

    #[test]
    fn test_extract_bits_boundary_conditions() {
        let data = 0x12345678u128;
        
        // 単一ビット抽出
        assert_eq!(extract_bits(data, 0, 1), 0);
        assert_eq!(extract_bits(data, 3, 1), 1);
        
        // 全ビット抽出
        assert_eq!(extract_bits(data, 0, 32), data);
        
        // バイト境界をまたぐ抽出
        assert_eq!(extract_bits(data, 4, 8), 0x67);
    }

    #[test]
    fn test_set_bits_boundary_conditions() {
        let mut data = 0u128;
        
        // 単一ビット設定
        set_bits(&mut data, 0, 1, 1);
        assert_eq!(data, 1);
        
        // バイト境界をまたぐ設定
        set_bits(&mut data, 4, 8, 0xAB);
        assert_eq!(extract_bits(data, 4, 8), 0xAB);
    }

    #[test]
    fn test_bytes_conversion_roundtrip() {
        let original_data = [0x12, 0x34, 0x56, 0x78, 0x9A, 0xBC, 0xDE, 0xF0,
                            0x11, 0x22, 0x33, 0x44, 0x55, 0x66, 0x77, 0x88];
        
        let as_u128 = bytes_to_u128_le(&original_data);
        let mut converted_back = [0u8; 16];
        u128_to_bytes_le(as_u128, &mut converted_back);
        
        assert_eq!(original_data, converted_back);
    }

    #[test]
    fn test_bit_field_operations() {
        let field = BitField::new("test", 0, 16);
        let mut data = 0u128;
        
        field.set(&mut data, 0xABCD);
        assert_eq!(field.extract(data), 0xABCD);
    }
}

/// LocationPacket の包括的テスト
#[cfg(test)]
mod location_packet_comprehensive_tests {
    use super::*;

    #[test]
    fn test_location_request_creation() {
        let req = LocationRequest::create_coordinate_lookup(
            35.6762, 139.6503, 0x123, true, true, false, false, false, 0, 1
        );
        
        assert_eq!(req.version, 1);
        assert_eq!(req.packet_id, 0x123);
        assert_eq!(req.latitude, 35.6762);
        assert_eq!(req.longitude, 139.6503);
        assert!(req.weather_flag);
        assert!(req.temperature_flag);
        assert!(!req.pop_flag);
    }

    #[test]
    fn test_location_request_serialization() {
        let req = LocationRequest::create_coordinate_lookup(
            35.0, 139.0, 0x456, true, false, true, false, false, 0, 1
        );
        
        let bytes = req.to_bytes();
        assert!(bytes.len() >= 16);
        
        // チェックサム検証
        assert!(verify_checksum12(&bytes, 116, 12));
    }

    #[test]
    fn test_location_response_creation() {
        let resp = LocationResponse::success(0x789, 123456);
        
        assert_eq!(resp.packet_id, 0x789);
        assert_eq!(resp.area_code, 123456);
        assert!(resp.success);
        assert_eq!(resp.error_code, 0);
    }

    #[test]
    fn test_location_response_error() {
        let resp = LocationResponse::error(0x789, 1);
        
        assert_eq!(resp.packet_id, 0x789);
        assert!(!resp.success);
        assert_eq!(resp.error_code, 1);
    }
}

/// QueryPacket の包括的テスト
#[cfg(test)]
mod query_packet_comprehensive_tests {
    use super::*;

    #[test]
    fn test_query_request_creation() {
        let req = QueryRequest::new(0x234, 567890, true, false, true, 2);
        
        assert_eq!(req.packet_id, 0x234);
        assert_eq!(req.area_code, 567890);
        assert!(req.current_flag);
        assert!(!req.forecast_flag);
        assert!(req.alert_flag);
        assert_eq!(req.day, 2);
    }

    #[test]
    fn test_query_request_serialization() {
        let req = QueryRequest::new(0x345, 678901, true, true, false, 1);
        let bytes = req.to_bytes();
        
        assert_eq!(bytes.len(), 16);
        // パケット型がQueryRequest (Type=2) であることを確認
        // ビット16-18がType=2であることを確認する
        let as_u128 = bytes_to_u128_le(&bytes);
        let packet_type = extract_bits(as_u128, 16, 3);
        assert_eq!(packet_type, 2);
    }

    #[test]
    fn test_query_response_creation() {
        let resp = QueryResponse::success(0x456, 100, 25, 60);
        
        assert_eq!(resp.packet_id, 0x456);
        assert_eq!(resp.weather_code, 100);
        assert_eq!(resp.temperature, 25);
        assert_eq!(resp.precipitation_prob, 60);
        assert!(resp.success);
    }
}

/// ReportPacket の包括的テスト
#[cfg(test)]
mod report_packet_comprehensive_tests {
    use super::*;

    #[test]
    fn test_report_request_creation() {
        let data = vec![0x01, 0x02, 0x03, 0x04];
        let req = ReportRequest::new(0x567, data.clone(), 1);
        
        assert_eq!(req.packet_id, 0x567);
        assert_eq!(req.data, data);
        assert_eq!(req.data_type, 1);
    }

    #[test]
    fn test_report_request_serialization() {
        let data = vec![0xAA, 0xBB, 0xCC, 0xDD];
        let req = ReportRequest::new(0x678, data, 2);
        let bytes = req.to_bytes();
        
        assert!(bytes.len() >= 16);
        assert!(verify_checksum12(&bytes, 116, 12));
    }

    #[test]
    fn test_report_response_creation() {
        let resp = ReportResponse::success(0x789);
        
        assert_eq!(resp.packet_id, 0x789);
        assert!(resp.success);
        assert_eq!(resp.error_code, 0);
    }
}

/// ErrorResponse の包括的テスト
#[cfg(test)]
mod error_response_comprehensive_tests {
    use super::*;

    #[test]
    fn test_error_response_creation() {
        let resp = ErrorResponse::new(0x890, 404, "Not Found".to_string());
        
        assert_eq!(resp.packet_id, 0x890);
        assert_eq!(resp.error_code, 404);
        assert_eq!(resp.error_message, "Not Found");
    }

    #[test]
    fn test_error_response_serialization() {
        let resp = ErrorResponse::new(0x901, 500, "Internal Error".to_string());
        let bytes = resp.to_bytes();
        
        assert_eq!(bytes.len(), 16);
        
        // パケット型がErrorResponse (Type=7) であることを確認
        let as_u128 = bytes_to_u128_le(&bytes);
        let packet_type = extract_bits(as_u128, 16, 3);
        assert_eq!(packet_type, 7);
    }

    #[test]
    fn test_error_response_different_error_codes() {
        let errors = vec![
            (400, "Bad Request"),
            (401, "Unauthorized"), 
            (403, "Forbidden"),
            (404, "Not Found"),
            (500, "Internal Server Error"),
        ];

        for (code, message) in errors {
            let resp = ErrorResponse::new(0x100, code, message.to_string());
            assert_eq!(resp.error_code, code);
            assert_eq!(resp.error_message, message);
            
            let bytes = resp.to_bytes();
            assert_eq!(bytes.len(), 16);
        }
    }
}

/// 拡張フィールドの包括的テスト
#[cfg(test)]
mod extended_field_comprehensive_tests {
    use super::*;
    use std::collections::HashMap;

    #[test]
    fn test_field_value_serialization() {
        let values = vec![
            FieldValue::String("test".to_string()),
            FieldValue::F64(123.456),
            FieldValue::U32(789),
            FieldValue::Bool(true),
        ];

        for value in values {
            let serialized = value.to_bytes();
            assert!(!serialized.is_empty());
        }
    }

    #[test]
    fn test_extended_field_packing() {
        let mut fields = HashMap::new();
        fields.insert("latitude".to_string(), FieldValue::F64(35.0));
        fields.insert("longitude".to_string(), FieldValue::F64(139.0));
        
        let packed = pack_ext_fields(&fields);
        assert!(!packed.is_empty());
        
        let unpacked = unpack_ext_fields(&packed).unwrap();
        assert_eq!(unpacked.len(), 2);
    }

    #[test]
    fn test_complex_field_combinations() {
        let mut fields = HashMap::new();
        fields.insert("alert".to_string(), FieldValue::String("Warning".to_string()));
        fields.insert("temperature".to_string(), FieldValue::F64(25.5));
        fields.insert("active".to_string(), FieldValue::Bool(true));
        fields.insert("count".to_string(), FieldValue::U32(42));
        
        let packed = pack_ext_fields(&fields);
        let unpacked = unpack_ext_fields(&packed).unwrap();
        
        assert_eq!(unpacked.len(), 4);
        assert!(unpacked.contains_key("alert"));
        assert!(unpacked.contains_key("temperature"));
        assert!(unpacked.contains_key("active"));
        assert!(unpacked.contains_key("count"));
    }
}

/// 統合的なパケット処理テスト
#[cfg(test)]
mod packet_integration_tests {
    use super::*;

    #[test]
    fn test_full_packet_lifecycle() {
        // LocationRequest作成
        let req = LocationRequest::create_coordinate_lookup(
            35.6762, 139.6503, 0x123, true, true, true, false, false, 0, 1
        );
        
        // シリアライズ
        let req_bytes = req.to_bytes();
        assert!(verify_checksum12(&req_bytes, 116, 12));
        
        // LocationResponse作成
        let resp = LocationResponse::success(0x123, 130010);
        let resp_bytes = resp.to_bytes();
        
        // 基本チェック
        assert_eq!(resp_bytes.len(), 16);
        
        // QueryRequest作成
        let query = QueryRequest::new(0x124, 130010, true, true, false, 0);
        let query_bytes = query.to_bytes();
        assert_eq!(query_bytes.len(), 16);
        
        // QueryResponse作成  
        let query_resp = QueryResponse::success(0x124, 100, 25, 30);
        let query_resp_bytes = query_resp.to_bytes();
        assert_eq!(query_resp_bytes.len(), 16);
    }

    #[test]
    fn test_error_handling_flow() {
        // 異常系のテスト
        let error_resp = ErrorResponse::new(0x999, 404, "Location not found".to_string());
        let error_bytes = error_resp.to_bytes();
        
        assert_eq!(error_bytes.len(), 16);
        
        // パケット型確認
        let as_u128 = bytes_to_u128_le(&error_bytes);
        let packet_type = extract_bits(as_u128, 16, 3);
        assert_eq!(packet_type, 7); // ErrorResponse
    }

    #[test]
    fn test_large_data_handling() {
        // 大きなデータを持つReportRequest
        let large_data = vec![0x42; 1000];
        let report = ReportRequest::new(0x555, large_data.clone(), 3);
        let report_bytes = report.to_bytes();
        
        assert!(report_bytes.len() > 16);
        assert!(verify_checksum12(&report_bytes, 116, 12));
    }
}

/// パフォーマンステスト
#[cfg(test)]
mod performance_tests {
    use super::*;
    use std::time::Instant;

    #[test]
    fn test_checksum_performance() {
        let data = vec![0x42; 1024];
        let start = Instant::now();
        
        for _ in 0..1000 {
            calc_checksum12(&data);
        }
        
        let duration = start.elapsed();
        println!("Checksum calculation time for 1000 iterations: {:?}", duration);
        assert!(duration.as_millis() < 100); // 100ms以内であることを確認
    }

    #[test]
    fn test_packet_creation_performance() {
        let start = Instant::now();
        
        for i in 0..1000 {
            let req = LocationRequest::create_coordinate_lookup(
                35.0 + (i as f64) * 0.001,
                139.0 + (i as f64) * 0.001,
                i as u16,
                true, true, false, false, false,
                0, 1
            );
            let _bytes = req.to_bytes();
        }
        
        let duration = start.elapsed();
        println!("Packet creation time for 1000 iterations: {:?}", duration);
        assert!(duration.as_millis() < 500); // 500ms以内であることを確認
    }
}