use crate::wip_common_rs::packet::types::query_packet::QueryRequest;

fn main() {
    // Use the exact timestamp from Python: 1755509212
    let python_timestamp = 1755509212u64;
    
    let request = QueryRequest::new_with_timestamp(
        11000,      // area_code
        1,          // packet_id  
        true,       // weather
        false,      // temperature
        false,      // precipitation_prob
        false,      // alert
        false,      // disaster
        0,          // day
        python_timestamp,
    );
    
    let packet_bytes = request.to_bytes();
    
    println!("=== Rust packet with Python timestamp ===");
    println!("Timestamp used: {}", python_timestamp);
    println!("Packet bytes: {:02X?}", packet_bytes);
    println!("Expected    : [11, 00, 0A, 00, DC, F1, A2, 68, 00, 00, 00, 00, F8, 2A, B0, BE]");
    println!("Actual      : {:02X?}", packet_bytes);
    
    // Check if they match
    let expected = [0x11u8, 0x00, 0x0A, 0x00, 0xDC, 0xF1, 0xA2, 0x68, 0x00, 0x00, 0x00, 0x00, 0xF8, 0x2A, 0xB0, 0xBE];
    let matches = packet_bytes == expected;
    println!("Exact match: {}", matches);
    
    if !matches {
        println!("\nDifferences:");
        for (i, (&expected_byte, &actual_byte)) in expected.iter().zip(packet_bytes.iter()).enumerate() {
            if expected_byte != actual_byte {
                println!("  Byte {}: expected 0x{:02X}, got 0x{:02X}", i, expected_byte, actual_byte);
            }
        }
    }
}