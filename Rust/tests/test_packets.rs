use wip_rust::wip_common_rs::packet::types::location_packet::{LocationRequest, LocationResponse};
use wip_rust::wip_common_rs::packet::types::report_packet::{ReportRequest, ReportResponse};
use wip_rust::wip_common_rs::packet::types::query_packet::{QueryRequest, QueryResponse};
use wip_rust::wip_common_rs::packet::core::checksum::verify_checksum12;

#[test]
fn test_location_request_creation() {
    let request = LocationRequest::create_coordinate_lookup(35.6812, 139.7671, 1, true, true, false, false, false, 0, 1);
    
    assert_eq!(request.latitude, 35.6812);
    assert_eq!(request.longitude, 139.7671);
    assert_eq!(request.packet_id, 1);
    assert!(request.weather_flag);
    assert!(request.temperature_flag);
}

#[test]
fn test_location_request_serialization() {
    let request = LocationRequest::create_coordinate_lookup(35.6812, 139.7671, 1, true, true, false, false, false, 0, 1);
    
    let bytes = request.to_bytes();
    assert!(!bytes.is_empty());
    assert!(bytes.len() >= 16); // Base packet size
    
    // Verify checksum at standard position
    assert!(verify_checksum12(&bytes, 116, 12));
}

#[test]
fn test_location_response_creation() {
    let response = LocationResponse::create_response(1, "123456", Some(25.5), Some(70), 100);
    
    assert_eq!(response.packet_id, 1);
    // Check area code (stored as u32 internally)
    assert!(response.area_code > 0);
}

#[test]
fn test_report_request_creation() {
    let request = ReportRequest::create_sensor_data_report(
        "123456",
        Some(200),
        Some(25.5),
        Some(70),
        None,
        None,
        1,
        1001
    );
    
    assert_eq!(request.packet_id, 1001);
    assert_eq!(request.area_code, 123456);
    assert!(request.weather_flag);
    assert!(request.temperature_flag);
    assert!(request.pop_flag);
}

#[test]
fn test_report_request_serialization() {
    let request = ReportRequest::create_sensor_data_report(
        "123456",
        Some(200),
        Some(25.5),
        Some(70),
        None,
        None,
        1,
        1001
    );
    
    let bytes = request.to_bytes();
    assert!(!bytes.is_empty());
    assert!(bytes.len() >= 16);
    
    // Verify checksum
    assert!(verify_checksum12(&bytes, 116, 12).unwrap_or(false));
}

#[test]
fn test_query_request_creation() {
    let request = QueryRequest::create_status_query("status", "region=tokyo", 1);
    
    assert_eq!(request.packet_id, 1);
    // Additional query-specific checks can be added here
}

#[test]
fn test_query_request_serialization() {
    let request = QueryRequest::create_status_query("weather", "location=tokyo&period=24h", 1);
    
    let bytes = request.to_bytes();
    assert!(!bytes.is_empty());
    assert!(bytes.len() >= 16);
    
    // Verify checksum
    assert!(verify_checksum12(&bytes, 116, 12).unwrap_or(false));
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
        let request = LocationRequest::create_coordinate_lookup(lat, lon, 1, false, false, false, false, false, 0);
        
        assert_eq!(request.latitude, lat);
        assert_eq!(request.longitude, lon);
        
        let bytes = request.to_bytes();
        assert!(!bytes.is_empty());
        assert!(verify_checksum12(&bytes, 116, 12).unwrap_or(false));
    }
}

#[test]
fn test_area_code_handling() {
    let test_codes = vec!["123456", "000001", "999999", "12345", "1"];
    
    for area_code in test_codes {
        let request = ReportRequest::create_sensor_data_report(
            area_code,
            None,
            None,
            None,
            None,
            None,
            1,
            1
        );
        
        // All area codes should be normalized to valid 6-digit format
        assert!(request.area_code <= 999999);
        
        let bytes = request.to_bytes();
        assert!(!bytes.is_empty());
        assert!(verify_checksum12(&bytes, 116, 12).unwrap_or(false));
    }
}

#[test]
fn test_temperature_encoding() {
    // Test temperature encoding with +100 offset
    let temperatures = vec![-30.0, 0.0, 25.5, 40.0];
    
    for temp in temperatures {
        let request = ReportRequest::create_sensor_data_report(
            "123456",
            None,
            Some(temp),
            None,
            None,
            None,
            1,
            1
        );
        
        // Temperature should be encoded with +100 offset
        let encoded_temp = (temp + 100.0) as u8;
        assert_eq!(request.temperature, encoded_temp);
        
        let bytes = request.to_bytes();
        assert!(!bytes.is_empty());
        assert!(verify_checksum12(&bytes, 116, 12).unwrap_or(false));
    }
}