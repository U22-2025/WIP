use wip_rust::wip_common_rs::packet::types::report_packet::ReportRequest;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    println!("Testing ReportRequest checksum generation...");
    
    // Create a test report request
    let report = ReportRequest::create_sensor_data_report(
        "011000",        // area_code
        Some(10),        // weather_code
        Some(22.0),      // temperature_c
        Some(30),        // precipitation_prob
        None,            // alert
        None,            // disaster
        1,               // version
        0x234,          // packet_id
    );
    
    // Generate packet bytes
    let bytes = report.to_bytes();
    println!("Generated packet ({} bytes): {:02X?}", bytes.len(), &bytes[..bytes.len().min(20)]);
    
    // Verify checksum by parsing the header
    use bitvec::prelude::*;
    if bytes.len() >= 16 {
        let bits = BitSlice::<u8, Lsb0>::from_slice(&bytes);
        let version: u8 = bits[0..4].load();
        let packet_id: u16 = bits[4..16].load();
        let packet_type: u8 = bits[16..19].load();
        let checksum: u16 = bits[116..128].load();
        let weather_code: u16 = bits[128..144].load();
        let temperature: u8 = bits[144..152].load();
        let pop: u8 = bits[152..160].load();
        
        println!("Packet fields:");
        println!("  Version: {}", version);
        println!("  Packet ID: 0x{:03X} ({})", packet_id, packet_id);
        println!("  Type: {}", packet_type);
        println!("  Checksum: 0x{:03X} ({})", checksum, checksum);
        println!("  Weather Code: {}", weather_code);
        println!("  Temperature: {} (+100 offset)", temperature);
        println!("  POP: {}", pop);
        
        // Test checksum calculations on different data ranges
        use wip_rust::wip_common_rs::packet::core::checksum::{calc_checksum12, verify_checksum12};
        
        println!("\nChecksum verification tests:");
        
        // Test 1: Verify using the built-in function
        let verify_result = verify_checksum12(&bytes, 116, 12);
        println!("  verify_checksum12: {}", if verify_result { "PASS" } else { "FAIL" });
        
        // Test 2: Calculate on full packet with checksum zeroed
        let mut test_bytes = bytes.clone();
        let test_bits = BitSlice::<u8, Lsb0>::from_slice_mut(&mut test_bytes);
        test_bits[116..128].store(0u16); // Zero out checksum field
        let calculated_full = calc_checksum12(&test_bytes);
        println!("  Full packet (checksum=0): 0x{:03X} - {}", calculated_full, 
                if calculated_full == checksum { "MATCH" } else { "MISMATCH" });
        
        // Test 3: Calculate on just first 16 bytes with checksum zeroed  
        let mut header_only = bytes[..16].to_vec();
        let header_bits = BitSlice::<u8, Lsb0>::from_slice_mut(&mut header_only);
        header_bits[116..128].store(0u16); // Zero out checksum field
        let calculated_header = calc_checksum12(&header_only);
        println!("  Header only (checksum=0): 0x{:03X} - {}", calculated_header,
                if calculated_header == checksum { "MATCH" } else { "MISMATCH" });
    }
    
    Ok(())
}