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
    request.set_severity(8);
    request.set_description("Major earthquake in Tokyo area".to_string());
    
    let bytes = request.to_bytes();
    assert!(!bytes.is_empty());
    
    // Verify that packet has valid checksum
    assert!(verify_checksum12(&bytes).is_ok());
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
    request.set_query_type("weather".to_string());
    request.set_parameters("location=tokyo&period=24h".to_string());
    
    let bytes = request.to_bytes();
    assert!(!bytes.is_empty());
    
    // Verify that packet has valid checksum
    assert!(verify_checksum12(&bytes).is_ok());
}

#[test]
fn test_edge_case_coordinates() {
    // Test boundary values
    let test_cases = vec![
        (90.0, 180.0),   // North-East boundary
        (-90.0, -180.0), // South-West boundary
        (0.0, 0.0),      // Origin
        (35.6812, 139.7671), // Tokyo
    ];
    
    for (lat, lon) in test_cases {
        let mut request = LocationRequest::new();
        request.set_latitude(lat);
        request.set_longitude(lon);
        
        assert_eq!(request.get_latitude(), lat);
        assert_eq!(request.get_longitude(), lon);
        
        let bytes = request.to_bytes();
        assert!(!bytes.is_empty());
        assert!(verify_checksum12(&bytes).is_ok());
    }
}

#[test]
fn test_severity_levels() {
    // Test all severity levels 1-10
    for severity in 1..=10 {
        let mut request = ReportRequest::new();
        request.set_disaster_type("test".to_string());
        request.set_severity(severity);
        request.set_description(format!("Test severity {}", severity));
        
        assert_eq!(request.get_severity(), severity);
        
        let bytes = request.to_bytes();
        assert!(!bytes.is_empty());
        assert!(verify_checksum12(&bytes).is_ok());
    }
}

#[test]
fn test_disaster_types() {
    let disaster_types = vec![
        "earthquake", "tsunami", "typhoon", "flood", 
        "landslide", "volcanic_eruption", "fire", "explosion"
    ];
    
    for disaster_type in disaster_types {
        let mut request = ReportRequest::new();
        request.set_disaster_type(disaster_type.to_string());
        request.set_severity(5);
        request.set_description(format!("Test {}", disaster_type));
        
        assert_eq!(request.get_disaster_type(), disaster_type);
        
        let bytes = request.to_bytes();
        assert!(!bytes.is_empty());
        assert!(verify_checksum12(&bytes).is_ok());
    }
}