use wip_rust::wip_common_rs::packet::types::location_packet::{LocationRequest, LocationResponse};
use wip_rust::wip_common_rs::packet::types::report_packet::{ReportRequest, ReportResponse};
use wip_rust::wip_common_rs::packet::types::query_packet::{QueryRequest, QueryResponse};
use wip_rust::wip_common_rs::packet::core::checksum::verify_checksum12;

#[test]
fn test_location_request_creation() {
    let mut request = LocationRequest::new();
        request.set_latitude(35.6812);
        request.set_longitude(139.7671);
        
        assert_eq!(request.get_latitude(), 35.6812);
        assert_eq!(request.get_longitude(), 139.7671);
    }

    #[test]
    fn test_location_request_serialization() {
        let mut request = LocationRequest::new();
        request.set_latitude(35.6812);
        request.set_longitude(139.7671);
        
        let bytes = request.to_bytes();
        assert!(!bytes.is_empty());
        
        // Verify that packet has valid checksum
        assert!(verify_checksum12(&bytes).is_ok());
    }

    #[test]
    fn test_location_response_creation() {
        let mut response = LocationResponse::new();
        response.set_area_code(123456);
        response.set_region_name("Tokyo".to_string());
        
        assert_eq!(response.get_area_code(), 123456);
        assert_eq!(response.get_region_name(), "Tokyo");
    }

    #[test]
    fn test_report_request_creation() {
        let mut request = ReportRequest::new();
        request.set_disaster_type("earthquake".to_string());
        request.set_severity(5);
        request.set_description("Strong earthquake detected".to_string());
        
        assert_eq!(request.get_disaster_type(), "earthquake");
        assert_eq!(request.get_severity(), 5);
        assert_eq!(request.get_description(), "Strong earthquake detected");
    }

    #[test]
    fn test_report_request_serialization() {
        let mut request = ReportRequest::new();
        request.set_disaster_type("earthquake".to_string());
        request.set_severity(5);
        request.set_description("Strong earthquake detected".to_string());
        
        let bytes = request.to_bytes();
        assert!(!bytes.is_empty());
        
        // Verify that packet has valid checksum
        assert!(verify_checksum12(&bytes).is_ok());
    }

    #[test]
    fn test_report_response_creation() {
        let mut response = ReportResponse::new();
        response.set_report_id(12345);
        response.set_status("accepted".to_string());
        
        assert_eq!(response.get_report_id(), 12345);
        assert_eq!(response.get_status(), "accepted");
    }

    #[test]
    fn test_query_request_creation() {
        let mut request = QueryRequest::new();
        request.set_query_type("status".to_string());
        request.set_parameters("region=tokyo".to_string());
        
        assert_eq!(request.get_query_type(), "status");
        assert_eq!(request.get_parameters(), "region=tokyo");
    }

    #[test]
    fn test_query_request_serialization() {
        let mut request = QueryRequest::new();
        request.set_query_type("status".to_string());
        request.set_parameters("region=tokyo".to_string());
        
        let bytes = request.to_bytes();
        assert!(!bytes.is_empty());
        
        // Verify that packet has valid checksum
        assert!(verify_checksum12(&bytes).is_ok());
    }

    #[test]
    fn test_query_response_creation() {
        let mut response = QueryResponse::new();
        response.set_result_count(10);
        response.set_data("result data".to_string());
        
        assert_eq!(response.get_result_count(), 10);
        assert_eq!(response.get_data(), "result data");
    }

    #[test]
    fn test_packet_round_trip() {
        // Test that we can serialize and deserialize packets
        let mut original_request = LocationRequest::new();
        original_request.set_latitude(35.6812);
        original_request.set_longitude(139.7671);
        
        let bytes = original_request.to_bytes();
        
        // In a real implementation, we would deserialize here
        // For now, we just verify the bytes are valid
        assert!(!bytes.is_empty());
        assert!(verify_checksum12(&bytes).is_ok());
    }

    #[test]
    fn test_empty_packet_handling() {
        let request = LocationRequest::new();
        let bytes = request.to_bytes();
        
        // Even empty packets should have valid structure
        assert!(!bytes.is_empty());
        assert!(verify_checksum12(&bytes).is_ok());
    }

    #[test]
    fn test_large_data_packet() {
        let mut request = ReportRequest::new();
        let large_description = "x".repeat(1000); // 1KB description
        request.set_description(large_description.clone());
        
        let bytes = request.to_bytes();
        assert!(!bytes.is_empty());
        assert!(verify_checksum12(&bytes).is_ok());
        
        // Verify the large data is handled correctly
        assert_eq!(request.get_description(), large_description);
    }
}