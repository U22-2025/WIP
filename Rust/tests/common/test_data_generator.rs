use rand::Rng;
use std::collections::HashMap;
use wip_rust::wip_common_rs::packet::types::location_packet::{LocationRequest, LocationResponse};
use wip_rust::wip_common_rs::packet::types::report_packet::{ReportRequest, ReportResponse};
use wip_rust::wip_common_rs::packet::types::query_packet::{QueryRequest, QueryResponse};

/// Test data generator for WIP packet testing
pub struct TestDataGenerator {
    rng: rand::rngs::ThreadRng,
}

impl TestDataGenerator {
    pub fn new() -> Self {
        Self {
            rng: rand::thread_rng(),
        }
    }

    /// Generate random coordinates within valid Earth bounds
    pub fn random_coordinates(&mut self) -> (f64, f64) {
        let lat = self.rng.gen_range(-90.0..=90.0);
        let lon = self.rng.gen_range(-180.0..=180.0);
        (lat, lon)
    }

    /// Generate coordinates for major Japanese cities
    pub fn japanese_city_coordinates(&mut self) -> (f64, f64, &'static str) {
        let cities = vec![
            (35.6812, 139.7671, "Tokyo"),
            (34.6937, 135.5023, "Osaka"),
            (35.0116, 135.7681, "Kyoto"),
            (35.1815, 136.9066, "Nagoya"),
            (43.0642, 141.3469, "Sapporo"),
            (33.5904, 130.4017, "Fukuoka"),
            (34.3853, 132.4553, "Hiroshima"),
            (26.2123, 127.6792, "Naha"),
        ];
        
        let (lat, lon, city) = cities[self.rng.gen_range(0..cities.len())];
        (lat, lon, city)
    }

    /// Generate random disaster types
    pub fn random_disaster_type(&mut self) -> &'static str {
        let disasters = vec![
            "earthquake",
            "tsunami",
            "typhoon",
            "flood",
            "landslide",
            "volcanic_eruption",
            "fire",
            "explosion",
            "accident",
            "terrorism",
        ];
        disasters[self.rng.gen_range(0..disasters.len())]
    }

    /// Generate random severity level (1-10)
    pub fn random_severity(&mut self) -> u8 {
        self.rng.gen_range(1..=10)
    }

    /// Generate random disaster description
    pub fn random_disaster_description(&mut self, disaster_type: &str) -> String {
        let templates = match disaster_type {
            "earthquake" => vec![
                "Strong earthquake detected with magnitude {severity}",
                "Seismic activity reported in the area, intensity {severity}",
                "Ground shaking observed, estimated magnitude {severity}",
            ],
            "tsunami" => vec![
                "Tsunami warning issued, wave height {severity}m expected",
                "Large waves approaching coastline, height {severity}m",
                "Tsunami alert level {severity} activated",
            ],
            "typhoon" => vec![
                "Typhoon approaching with wind speed {severity}0 km/h",
                "Strong winds and heavy rain, category {severity}",
                "Tropical storm intensity {severity} reported",
            ],
            "flood" => vec![
                "Flooding reported with water level {severity}m",
                "River overflow detected, flood level {severity}",
                "Heavy rainfall causing flood, severity level {severity}",
            ],
            _ => vec![
                "{disaster_type} reported with severity level {severity}",
                "Emergency situation: {disaster_type}, intensity {severity}",
                "{disaster_type} incident confirmed, level {severity}",
            ],
        };

        let template = templates[self.rng.gen_range(0..templates.len())];
        template
            .replace("{disaster_type}", disaster_type)
            .replace("{severity}", &self.random_severity().to_string())
    }

    /// Generate a complete LocationRequest packet
    pub fn location_request(&mut self) -> LocationRequest {
        let mut request = LocationRequest::new();
        let (lat, lon) = self.random_coordinates();
        request.set_latitude(lat);
        request.set_longitude(lon);
        request
    }

    /// Generate a LocationRequest for a specific Japanese city
    pub fn japanese_city_location_request(&mut self) -> (LocationRequest, &'static str) {
        let mut request = LocationRequest::new();
        let (lat, lon, city) = self.japanese_city_coordinates();
        request.set_latitude(lat);
        request.set_longitude(lon);
        (request, city)
    }

    /// Generate a LocationResponse packet
    pub fn location_response(&mut self) -> LocationResponse {
        let mut response = LocationResponse::new();
        response.set_area_code(self.rng.gen_range(100000..999999));
        
        let regions = vec![
            "Tokyo", "Osaka", "Kyoto", "Nagoya", "Sapporo", 
            "Fukuoka", "Hiroshima", "Sendai", "Yokohama", "Kobe"
        ];
        let region = regions[self.rng.gen_range(0..regions.len())];
        response.set_region_name(region.to_string());
        
        response
    }

    /// Generate a ReportRequest packet
    pub fn report_request(&mut self) -> ReportRequest {
        let mut request = ReportRequest::new();
        let disaster_type = self.random_disaster_type();
        let severity = self.random_severity();
        
        request.set_disaster_type(disaster_type.to_string());
        request.set_severity(severity);
        request.set_description(self.random_disaster_description(disaster_type));
        
        request
    }

    /// Generate a realistic ReportRequest for a specific location
    pub fn location_specific_report_request(&mut self, lat: f64, lon: f64, city: &str) -> ReportRequest {
        let mut request = ReportRequest::new();
        let disaster_type = self.random_disaster_type();
        let severity = self.random_severity();
        
        request.set_disaster_type(disaster_type.to_string());
        request.set_severity(severity);
        request.set_description(
            format!("{} in {} area (lat: {:.4}, lon: {:.4}), severity: {}", 
                    disaster_type, city, lat, lon, severity)
        );
        
        request
    }

    /// Generate a ReportResponse packet
    pub fn report_response(&mut self) -> ReportResponse {
        let mut response = ReportResponse::new();
        response.set_report_id(self.rng.gen_range(10000..99999));
        
        let statuses = vec!["accepted", "pending", "processing", "completed", "rejected"];
        let status = statuses[self.rng.gen_range(0..statuses.len())];
        response.set_status(status.to_string());
        
        response
    }

    /// Generate a QueryRequest packet
    pub fn query_request(&mut self) -> QueryRequest {
        let mut request = QueryRequest::new();
        
        let query_types = vec![
            "status", "weather", "alerts", "reports", "statistics", 
            "history", "forecast", "evacuation", "resources", "contact"
        ];
        let query_type = query_types[self.rng.gen_range(0..query_types.len())];
        request.set_query_type(query_type.to_string());
        
        // Generate appropriate parameters for each query type
        let parameters = match query_type {
            "status" => format!("region=tokyo&type=current"),
            "weather" => format!("location=tokyo&period=24h"),
            "alerts" => format!("severity=high&region=kanto"),
            "reports" => format!("type=earthquake&date={}", self.random_date()),
            "statistics" => format!("period=monthly&area=tokyo"),
            "history" => format!("from={}&to={}", self.random_date(), self.random_date()),
            "forecast" => format!("location=osaka&hours=48"),
            "evacuation" => format!("area=tokyo&type=route"),
            "resources" => format!("type=shelter&radius=5km"),
            "contact" => format!("service=emergency&location=tokyo"),
            _ => format!("query={}&limit=100", query_type),
        };
        
        request.set_parameters(parameters);
        request
    }

    /// Generate a QueryResponse packet
    pub fn query_response(&mut self) -> QueryResponse {
        let mut response = QueryResponse::new();
        response.set_result_count(self.rng.gen_range(0..1000));
        
        // Generate sample JSON data
        let sample_data = format!(
            r#"{{"timestamp": "{}", "status": "ok", "data": ["item1", "item2", "item3"]}}"#,
            chrono::Utc::now().format("%Y-%m-%dT%H:%M:%SZ")
        );
        response.set_data(sample_data);
        
        response
    }

    /// Generate a random date string
    fn random_date(&mut self) -> String {
        let year = self.rng.gen_range(2020..=2024);
        let month = self.rng.gen_range(1..=12);
        let day = self.rng.gen_range(1..=28); // Safe day range for all months
        format!("{:04}-{:02}-{:02}", year, month, day)
    }

    /// Generate edge case coordinates
    pub fn edge_case_coordinates(&mut self) -> Vec<(f64, f64, &'static str)> {
        vec![
            (0.0, 0.0, "Equator_PrimeMeridian"),
            (90.0, 0.0, "NorthPole"),
            (-90.0, 0.0, "SouthPole"),
            (0.0, 180.0, "Equator_DateLine"),
            (0.0, -180.0, "Equator_DateLineWest"),
            (85.0, 179.0, "NearPole_NearDateLine"),
            (-85.0, -179.0, "NearSouthPole_NearDateLineWest"),
        ]
    }

    /// Generate invalid coordinates for error testing
    pub fn invalid_coordinates(&mut self) -> Vec<(f64, f64, &'static str)> {
        vec![
            (91.0, 0.0, "LatitudeToHigh"),
            (-91.0, 0.0, "LatitudeTooLow"),
            (0.0, 181.0, "LongitudeTooHigh"),
            (0.0, -181.0, "LongitudeTooLow"),
            (f64::NAN, 0.0, "LatitudeNaN"),
            (0.0, f64::NAN, "LongitudeNaN"),
            (f64::INFINITY, 0.0, "LatitudeInfinity"),
            (0.0, f64::INFINITY, "LongitudeInfinity"),
            (f64::NEG_INFINITY, 0.0, "LatitudeNegInfinity"),
            (0.0, f64::NEG_INFINITY, "LongitudeNegInfinity"),
        ]
    }

    /// Generate test scenario data sets
    pub fn disaster_scenarios(&mut self) -> Vec<TestScenario> {
        vec![
            TestScenario {
                name: "Tokyo_Earthquake".to_string(),
                disaster_type: "earthquake".to_string(),
                severity: 7,
                latitude: 35.6812,
                longitude: 139.7671,
                description: "Major earthquake in Tokyo metropolitan area".to_string(),
            },
            TestScenario {
                name: "Osaka_Typhoon".to_string(),
                disaster_type: "typhoon".to_string(),
                severity: 5,
                latitude: 34.6937,
                longitude: 135.5023,
                description: "Typhoon approaching Osaka Bay area".to_string(),
            },
            TestScenario {
                name: "Sendai_Tsunami".to_string(),
                disaster_type: "tsunami".to_string(),
                severity: 9,
                latitude: 38.2682,
                longitude: 140.8694,
                description: "Tsunami warning for Sendai coastal area".to_string(),
            },
            TestScenario {
                name: "Kyushu_Volcanic".to_string(),
                disaster_type: "volcanic_eruption".to_string(),
                severity: 6,
                latitude: 32.7503,
                longitude: 129.8779,
                description: "Volcanic activity in Kyushu region".to_string(),
            },
            TestScenario {
                name: "Hokkaido_Flood".to_string(),
                disaster_type: "flood".to_string(),
                severity: 4,
                latitude: 43.0642,
                longitude: 141.3469,
                description: "Heavy rainfall causing floods in Hokkaido".to_string(),
            },
        ]
    }

    /// Generate performance test data
    pub fn performance_test_data(&mut self, count: usize) -> Vec<LocationRequest> {
        (0..count)
            .map(|_| self.location_request())
            .collect()
    }

    /// Generate stress test data with varying sizes
    pub fn stress_test_packets(&mut self, count: usize) -> Vec<Vec<u8>> {
        let mut packets = Vec::new();
        
        for _ in 0..count {
            match self.rng.gen_range(0..3) {
                0 => packets.push(self.location_request().to_bytes()),
                1 => packets.push(self.report_request().to_bytes()),
                2 => packets.push(self.query_request().to_bytes()),
                _ => unreachable!(),
            }
        }
        
        packets
    }
}

/// Test scenario structure for comprehensive testing
#[derive(Debug, Clone)]
pub struct TestScenario {
    pub name: String,
    pub disaster_type: String,
    pub severity: u8,
    pub latitude: f64,
    pub longitude: f64,
    pub description: String,
}

impl TestScenario {
    pub fn to_location_request(&self) -> LocationRequest {
        let mut request = LocationRequest::new();
        request.set_latitude(self.latitude);
        request.set_longitude(self.longitude);
        request
    }
    
    pub fn to_report_request(&self) -> ReportRequest {
        let mut request = ReportRequest::new();
        request.set_disaster_type(self.disaster_type.clone());
        request.set_severity(self.severity);
        request.set_description(self.description.clone());
        request
    }
}

/// Test data validator for ensuring data quality
pub struct TestDataValidator;

impl TestDataValidator {
    /// Validate coordinates are within Earth bounds
    pub fn validate_coordinates(lat: f64, lon: f64) -> bool {
        lat >= -90.0 && lat <= 90.0 && lon >= -180.0 && lon <= 180.0 &&
        !lat.is_nan() && !lon.is_nan() && lat.is_finite() && lon.is_finite()
    }
    
    /// Validate severity is in valid range
    pub fn validate_severity(severity: u8) -> bool {
        severity >= 1 && severity <= 10
    }
    
    /// Validate disaster type is known
    pub fn validate_disaster_type(disaster_type: &str) -> bool {
        let valid_types = vec![
            "earthquake", "tsunami", "typhoon", "flood", "landslide",
            "volcanic_eruption", "fire", "explosion", "accident", "terrorism"
        ];
        valid_types.contains(&disaster_type)
    }
    
    /// Validate packet has minimum required size
    pub fn validate_packet_size(packet_data: &[u8]) -> bool {
        packet_data.len() >= 4 // Minimum size for a valid packet
    }
}

#[cfg(test)]
mod test_data_generator_tests {
    use super::*;

    #[test]
    fn test_coordinate_generation() {
        let mut generator = TestDataGenerator::new();
        
        for _ in 0..100 {
            let (lat, lon) = generator.random_coordinates();
            assert!(TestDataValidator::validate_coordinates(lat, lon));
        }
    }

    #[test]
    fn test_japanese_cities() {
        let mut generator = TestDataGenerator::new();
        
        for _ in 0..10 {
            let (lat, lon, city) = generator.japanese_city_coordinates();
            assert!(TestDataValidator::validate_coordinates(lat, lon));
            assert!(!city.is_empty());
        }
    }

    #[test]
    fn test_packet_generation() {
        let mut generator = TestDataGenerator::new();
        
        // Test location packet generation
        let location_req = generator.location_request();
        let location_bytes = location_req.to_bytes();
        assert!(TestDataValidator::validate_packet_size(&location_bytes));
        
        // Test report packet generation
        let report_req = generator.report_request();
        let report_bytes = report_req.to_bytes();
        assert!(TestDataValidator::validate_packet_size(&report_bytes));
        
        // Test query packet generation
        let query_req = generator.query_request();
        let query_bytes = query_req.to_bytes();
        assert!(TestDataValidator::validate_packet_size(&query_bytes));
    }

    #[test]
    fn test_disaster_scenarios() {
        let mut generator = TestDataGenerator::new();
        let scenarios = generator.disaster_scenarios();
        
        assert_eq!(scenarios.len(), 5);
        
        for scenario in scenarios {
            assert!(TestDataValidator::validate_coordinates(scenario.latitude, scenario.longitude));
            assert!(TestDataValidator::validate_severity(scenario.severity));
            assert!(TestDataValidator::validate_disaster_type(&scenario.disaster_type));
            assert!(!scenario.name.is_empty());
            assert!(!scenario.description.is_empty());
        }
    }

    #[test]
    fn test_edge_cases() {
        let mut generator = TestDataGenerator::new();
        let edge_cases = generator.edge_case_coordinates();
        
        for (lat, lon, _name) in edge_cases {
            assert!(TestDataValidator::validate_coordinates(lat, lon));
        }
    }

    #[test]
    fn test_invalid_coordinates() {
        let mut generator = TestDataGenerator::new();
        let invalid_coords = generator.invalid_coordinates();
        
        for (lat, lon, _name) in invalid_coords {
            assert!(!TestDataValidator::validate_coordinates(lat, lon));
        }
    }
}