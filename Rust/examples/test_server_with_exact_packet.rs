use wip_rust::wip_common_rs::clients::weather_client::WeatherClient;
use wip_rust::wip_common_rs::packet::types::query_packet::QueryRequest;
use std::io;

fn main() -> io::Result<()> {
    // Create a client and test with exact Python packet
    let mut client = WeatherClient::new("127.0.0.1", 4111, true)?;
    
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
    
    println!("=== Testing exact Python packet format ===");
    println!("Sending packet: {:02X?}", packet_bytes);
    println!("Expected     : [11, 00, 0A, 00, DC, F1, A2, 68, 00, 00, 00, 00, F8, 2A, B0, BE]");
    
    // Send the raw packet
    match client.send_raw(&packet_bytes) {
        Ok(response) => {
            println!("✅ Success! Received response: {:02X?}", response);
            
            // Analyze the response
            if response.len() >= 3 {
                let packet_type = response[2] & 0x07;
                println!("Response type: {} (3=QueryResponse, 7=Error)", packet_type);
                
                if packet_type == 7 && response.len() >= 4 {
                    let error_code = response[3];
                    let error_message = match error_code {
                        1 => "Invalid packet format",
                        2 => "Checksum error", 
                        3 => "Unsupported version",
                        4 => "Unknown packet type",
                        5 => "Missing required data",
                        6 => "Server error",
                        7 => "Timeout",
                        _ => "Unknown error",
                    };
                    println!("❌ Error code: {} = {}", error_code, error_message);
                } else if packet_type == 3 {
                    println!("✅ Received valid QueryResponse!");
                    
                    // Parse extended data if available
                    if response.len() > 16 {
                        let extended_data = &response[16..];
                        println!("Extended data: {:02X?}", extended_data);
                        
                        if extended_data.len() >= 2 {
                            let weather_code = u16::from_le_bytes([extended_data[0], extended_data[1]]);
                            println!("Weather code: {} (0x{:04X})", weather_code, weather_code);
                        }
                    }
                }
            }
        }
        Err(e) => {
            println!("❌ Failed to communicate: {}", e);
        }
    }
    
    Ok(())
}