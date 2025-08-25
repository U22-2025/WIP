use wip_rust::wip_common_rs::packet::types::location_packet::{LocationRequest, LocationResponse};
use wip_rust::wip_common_rs::packet::types::report_packet::{ReportRequest, ReportResponse};
use wip_rust::wip_common_rs::packet::types::query_packet::{QueryRequest, QueryResponse};
use wip_rust::wip_common_rs::packet::types::error_response::ErrorResponse;
use wip_rust::wip_common_rs::packet::core::checksum::verify_checksum12;
use wip_rust::wip_common_rs::packet::core::PacketFormat;

/// Comprehensive test suite for all packet types
/// Covers creation, serialization, validation, edge cases, and error handling

#[cfg(test)]
mod comprehensive_packet_tests {
    use super::*;

    // ============================================================================
    // LocationRequest Tests
    // ============================================================================

    #[test]
    fn test_location_request_default_creation() {
        let request = LocationRequest::new();
        
        // Test default values
        assert_eq!(request.get_version(), 1);
        assert_eq!(request.get_packet_type(), 0); // Location request type
        assert!(request.get_packet_id() > 0); // Should generate random ID
        assert_eq!(request.get_latitude(), 0.0);
        assert_eq!(request.get_longitude(), 0.0);
    }

    #[test]
    fn test_location_request_coordinate_setting() {
        let mut request = LocationRequest::new();
        
        // Test Tokyo coordinates
        let tokyo_lat = 35.6812;
        let tokyo_lng = 139.7671;
        
        request.set_latitude(tokyo_lat);
        request.set_longitude(tokyo_lng);
        
        assert_eq!(request.get_latitude(), tokyo_lat);
        assert_eq!(request.get_longitude(), tokyo_lng);
    }

    #[test]
    fn test_location_request_flag_settings() {
        let mut request = LocationRequest::new();
        
        // Test individual flag settings
        request.set_weather_flag(true);
        request.set_temperature_flag(true);
        request.set_precipitation_flag(true);
        request.set_alert_flag(true);
        request.set_disaster_flag(true);
        
        assert!(request.get_weather_flag());
        assert!(request.get_temperature_flag());
        assert!(request.get_precipitation_flag());
        assert!(request.get_alert_flag());
        assert!(request.get_disaster_flag());
    }

    #[test]
    fn test_location_request_coordinate_lookup_factory() {
        let lat = 35.6812;
        let lng = 139.7671;
        let packet_id = 12345;
        
        let request = LocationRequest::create_coordinate_lookup(
            lat, lng, packet_id, true, true, false, false, false, 0
        );
        
        assert_eq!(request.get_latitude(), lat);
        assert_eq!(request.get_longitude(), lng);
        assert_eq!(request.get_packet_id(), packet_id);
        assert!(request.get_weather_flag());
        assert!(request.get_temperature_flag());
        assert!(!request.get_precipitation_flag());
        assert!(!request.get_alert_flag());
        assert!(!request.get_disaster_flag());
    }

    #[test]
    fn test_location_request_serialization() {
        let mut request = LocationRequest::new();
        request.set_latitude(35.6812);
        request.set_longitude(139.7671);
        request.set_weather_flag(true);
        
        let bytes = request.to_bytes();
        
        // Basic sanity checks
        assert!(!bytes.is_empty());
        assert!(bytes.len() >= 16); // Minimum packet size
        
        // Verify checksum is valid
        assert!(verify_checksum12(&bytes).is_ok());
    }

    #[test]
    fn test_location_request_extreme_coordinates() {
        let mut request = LocationRequest::new();
        
        // Test extreme coordinate values
        let test_cases = vec![
            (-90.0, -180.0),   // South Pole, Date Line West
            (90.0, 180.0),     // North Pole, Date Line East
            (0.0, 0.0),        // Equator, Prime Meridian
            (-85.05, -179.99), // Near extreme south-west
            (85.05, 179.99),   // Near extreme north-east
        ];
        
        for (lat, lng) in test_cases {
            request.set_latitude(lat);
            request.set_longitude(lng);
            
            assert_eq!(request.get_latitude(), lat);
            assert_eq!(request.get_longitude(), lng);
            
            // Should be able to serialize extreme coordinates
            let bytes = request.to_bytes();
            assert!(!bytes.is_empty());
            assert!(verify_checksum12(&bytes).is_ok());
        }
    }

    // ============================================================================
    // LocationResponse Tests
    // ============================================================================

    #[test]
    fn test_location_response_creation() {
        let mut response = LocationResponse::new();
        response.set_area_code(130010); // Tokyo area code
        response.set_region_name("Tokyo".to_string());
        
        assert_eq!(response.get_area_code(), 130010);
        assert_eq!(response.get_region_name(), "Tokyo");
    }

    #[test]
    fn test_location_response_area_codes() {
        let mut response = LocationResponse::new();
        
        // Test various Japanese area codes
        let test_codes = vec![
            11000,  // Hokkaido
            40010,  // Miyagi
            130010, // Tokyo
            140010, // Kanagawa
            270000, // Osaka
            400010, // Fukuoka
        ];
        
        for code in test_codes {
            response.set_area_code(code);
            assert_eq!(response.get_area_code(), code);
            
            // Should serialize valid area codes
            let bytes = response.to_bytes();
            assert!(!bytes.is_empty());
            assert!(verify_checksum12(&bytes).is_ok());
        }
    }

    #[test]
    fn test_location_response_long_region_names() {
        let mut response = LocationResponse::new();
        
        // Test with very long region name
        let long_name = "A".repeat(500);
        response.set_region_name(long_name.clone());
        
        assert_eq!(response.get_region_name(), long_name);
        
        // Should handle long names in serialization
        let bytes = response.to_bytes();
        assert!(!bytes.is_empty());
        assert!(verify_checksum12(&bytes).is_ok());
    }

    // ============================================================================
    // ReportRequest Tests
    // ============================================================================

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
    fn test_report_request_disaster_types() {
        let mut request = ReportRequest::new();
        
        // Test various disaster types
        let disaster_types = vec![
            "earthquake",
            "tsunami",
            "typhoon",
            "heavy_rain",
            "landslide",
            "volcanic_eruption",
            "flood",
            "wildfire",
        ];
        
        for disaster_type in disaster_types {
            request.set_disaster_type(disaster_type.to_string());
            assert_eq!(request.get_disaster_type(), disaster_type);
            
            let bytes = request.to_bytes();
            assert!(!bytes.is_empty());
            assert!(verify_checksum12(&bytes).is_ok());
        }
    }

    #[test]
    fn test_report_request_severity_levels() {
        let mut request = ReportRequest::new();
        request.set_disaster_type("earthquake".to_string());
        
        // Test severity levels 1-10
        for severity in 1..=10 {
            request.set_severity(severity);
            assert_eq!(request.get_severity(), severity);
            
            let bytes = request.to_bytes();
            assert!(!bytes.is_empty());
            assert!(verify_checksum12(&bytes).is_ok());
        }
    }

    #[test]
    fn test_report_request_large_description() {
        let mut request = ReportRequest::new();
        request.set_disaster_type("earthquake".to_string());
        
        // Test with very large description
        let large_desc = "Detailed seismic activity report: ".repeat(100);
        request.set_description(large_desc.clone());
        
        assert_eq!(request.get_description(), large_desc);
        
        let bytes = request.to_bytes();
        assert!(!bytes.is_empty());
        assert!(verify_checksum12(&bytes).is_ok());
    }

    // ============================================================================
    // ReportResponse Tests
    // ============================================================================

    #[test]
    fn test_report_response_creation() {
        let mut response = ReportResponse::new();
        response.set_report_id(12345);
        response.set_status("accepted".to_string());
        
        assert_eq!(response.get_report_id(), 12345);
        assert_eq!(response.get_status(), "accepted");
    }

    #[test]
    fn test_report_response_status_values() {
        let mut response = ReportResponse::new();
        response.set_report_id(12345);
        
        let status_values = vec![
            "accepted",
            "rejected",
            "pending",
            "processed",
            "error",
            "invalid",
        ];
        
        for status in status_values {
            response.set_status(status.to_string());
            assert_eq!(response.get_status(), status);
            
            let bytes = response.to_bytes();
            assert!(!bytes.is_empty());
            assert!(verify_checksum12(&bytes).is_ok());
        }
    }

    // ============================================================================
    // QueryRequest Tests
    // ============================================================================

    #[test]
    fn test_query_request_creation() {
        let mut request = QueryRequest::new();
        request.set_query_type("weather_status".to_string());
        request.set_parameters("region=tokyo&day=0".to_string());
        
        assert_eq!(request.get_query_type(), "weather_status");
        assert_eq!(request.get_parameters(), "region=tokyo&day=0");
    }

    #[test]
    fn test_query_request_types() {
        let mut request = QueryRequest::new();
        
        let query_types = vec![
            "weather_status",
            "forecast",
            "alerts",
            "historical",
            "statistics",
            "health_check",
        ];
        
        for query_type in query_types {
            request.set_query_type(query_type.to_string());
            assert_eq!(request.get_query_type(), query_type);
            
            let bytes = request.to_bytes();
            assert!(!bytes.is_empty());
            assert!(verify_checksum12(&bytes).is_ok());
        }
    }

    #[test]
    fn test_query_request_complex_parameters() {
        let mut request = QueryRequest::new();
        request.set_query_type("weather_status".to_string());
        
        // Test complex parameter strings
        let complex_params = vec![
            "region=tokyo&day=0&format=json",
            "lat=35.6812&lng=139.7671&radius=10&units=metric",
            "start_date=2024-01-01&end_date=2024-12-31&data_type=temperature",
            "area_codes=130010,140010,270000&include_alerts=true&lang=ja",
        ];
        
        for params in complex_params {
            request.set_parameters(params.to_string());
            assert_eq!(request.get_parameters(), params);
            
            let bytes = request.to_bytes();
            assert!(!bytes.is_empty());
            assert!(verify_checksum12(&bytes).is_ok());
        }
    }

    // ============================================================================
    // QueryResponse Tests
    // ============================================================================

    #[test]
    fn test_query_response_creation() {
        let mut response = QueryResponse::new();
        response.set_result_count(10);
        response.set_data("weather data payload".to_string());
        
        assert_eq!(response.get_result_count(), 10);
        assert_eq!(response.get_data(), "weather data payload");
    }

    #[test]
    fn test_query_response_large_data() {
        let mut response = QueryResponse::new();
        response.set_result_count(1000);
        
        // Test with large JSON-like data
        let large_data = serde_json::json!({
            "weather": {
                "temperature": 25.5,
                "humidity": 60,
                "pressure": 1013.25,
                "conditions": "partly_cloudy"
            },
            "forecast": [
                {"day": 0, "temp_high": 28, "temp_low": 18, "precipitation": 0},
                {"day": 1, "temp_high": 26, "temp_low": 16, "precipitation": 20},
                {"day": 2, "temp_high": 24, "temp_low": 14, "precipitation": 60}
            ],
            "alerts": [
                {"type": "heavy_rain", "severity": "warning", "area": "tokyo"}
            ]
        }).to_string();
        
        response.set_data(large_data.clone());
        assert_eq!(response.get_data(), large_data);
        
        let bytes = response.to_bytes();
        assert!(!bytes.is_empty());
        assert!(verify_checksum12(&bytes).is_ok());
    }

    // ============================================================================
    // ErrorResponse Tests
    // ============================================================================

    #[test]
    fn test_error_response_creation() {
        let mut error = ErrorResponse::new();
        error.set_error_code(404);
        error.set_error_message("Not found".to_string());
        
        assert_eq!(error.get_error_code(), 404);
        assert_eq!(error.get_error_message(), "Not found");
    }

    #[test]
    fn test_error_response_common_codes() {
        let mut error = ErrorResponse::new();
        
        let error_cases = vec![
            (400, "Bad Request"),
            (401, "Unauthorized"),
            (403, "Forbidden"),
            (404, "Not Found"),
            (500, "Internal Server Error"),
            (502, "Bad Gateway"),
            (503, "Service Unavailable"),
            (504, "Gateway Timeout"),
        ];
        
        for (code, message) in error_cases {
            error.set_error_code(code);
            error.set_error_message(message.to_string());
            
            assert_eq!(error.get_error_code(), code);
            assert_eq!(error.get_error_message(), message);
            
            let bytes = error.to_bytes();
            assert!(!bytes.is_empty());
            assert!(verify_checksum12(&bytes).is_ok());
        }
    }

    // ============================================================================
    // Cross-Packet Tests
    // ============================================================================

    #[test]
    fn test_packet_id_uniqueness() {
        // Create multiple packets and verify they have different IDs
        let request1 = LocationRequest::new();
        let request2 = LocationRequest::new();
        let request3 = QueryRequest::new();
        let request4 = ReportRequest::new();
        
        let ids = vec![
            request1.get_packet_id(),
            request2.get_packet_id(),
            request3.get_packet_id(),
            request4.get_packet_id(),
        ];
        
        // Check that all IDs are unique (very high probability)
        for i in 0..ids.len() {
            for j in (i + 1)..ids.len() {
                assert_ne!(ids[i], ids[j], "Packet IDs should be unique");
            }
        }
    }

    #[test]
    fn test_packet_timestamps() {
        let request1 = LocationRequest::new();
        std::thread::sleep(std::time::Duration::from_millis(10));
        let request2 = LocationRequest::new();
        
        // Timestamps should be different (and second should be later)
        assert!(request2.get_timestamp() >= request1.get_timestamp());
    }

    #[test]
    fn test_packet_version_consistency() {
        // All packets should use version 1
        let location_req = LocationRequest::new();
        let location_resp = LocationResponse::new();
        let query_req = QueryRequest::new();
        let query_resp = QueryResponse::new();
        let report_req = ReportRequest::new();
        let report_resp = ReportResponse::new();
        let error_resp = ErrorResponse::new();
        
        assert_eq!(location_req.get_version(), 1);
        assert_eq!(location_resp.get_version(), 1);
        assert_eq!(query_req.get_version(), 1);
        assert_eq!(query_resp.get_version(), 1);
        assert_eq!(report_req.get_version(), 1);
        assert_eq!(report_resp.get_version(), 1);
        assert_eq!(error_resp.get_version(), 1);
    }

    #[test]
    fn test_packet_type_values() {
        // Verify packet types are correctly set
        let location_req = LocationRequest::new();
        let location_resp = LocationResponse::new();
        let query_req = QueryRequest::new();
        let query_resp = QueryResponse::new();
        let report_req = ReportRequest::new();
        let report_resp = ReportResponse::new();
        
        assert_eq!(location_req.get_packet_type(), 0);  // Location request
        assert_eq!(location_resp.get_packet_type(), 1); // Location response
        assert_eq!(query_req.get_packet_type(), 2);     // Query request
        assert_eq!(query_resp.get_packet_type(), 3);    // Query response
        assert_eq!(report_req.get_packet_type(), 4);    // Report request
        assert_eq!(report_resp.get_packet_type(), 5);   // Report response
    }

    // ============================================================================
    // Serialization Integrity Tests
    // ============================================================================

    #[test]
    fn test_empty_packets_serialization() {
        // All packet types should be able to serialize even when empty
        let packets: Vec<Box<dyn PacketFormat>> = vec![
            Box::new(LocationRequest::new()),
            Box::new(LocationResponse::new()),
            Box::new(QueryRequest::new()),
            Box::new(QueryResponse::new()),
            Box::new(ReportRequest::new()),
            Box::new(ReportResponse::new()),
            Box::new(ErrorResponse::new()),
        ];
        
        for packet in packets {
            let bytes = packet.to_bytes();
            assert!(!bytes.is_empty(), "Empty packet should still serialize");
            assert!(verify_checksum12(&bytes).is_ok(), "Empty packet should have valid checksum");
        }
    }

    #[test]
    fn test_packet_minimum_size() {
        // All packets should have at least the minimum WIP packet size (16 bytes)
        let packets: Vec<Box<dyn PacketFormat>> = vec![
            Box::new(LocationRequest::new()),
            Box::new(LocationResponse::new()),
            Box::new(QueryRequest::new()),
            Box::new(QueryResponse::new()),
            Box::new(ReportRequest::new()),
            Box::new(ReportResponse::new()),
            Box::new(ErrorResponse::new()),
        ];
        
        for packet in packets {
            let bytes = packet.to_bytes();
            assert!(bytes.len() >= 16, "Packet should be at least 16 bytes (WIP minimum)");
        }
    }

    #[test]
    fn test_checksum_corruption_detection() {
        let mut request = LocationRequest::new();
        request.set_latitude(35.6812);
        request.set_longitude(139.7671);
        
        let mut bytes = request.to_bytes();
        assert!(verify_checksum12(&bytes).is_ok());
        
        // Corrupt a data byte (not checksum)
        if bytes.len() > 4 {
            bytes[2] ^= 0x01; // Flip one bit
            assert!(verify_checksum12(&bytes).is_err(), "Corrupted packet should fail checksum");
        }
    }
}