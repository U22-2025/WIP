use wip_rust::wip_common_rs::packet::types::report_packet::ReportRequest;

fn main() {
    println!("Testing auth field addition in ReportRequest");
    
    // Create a ReportRequest
    let mut request = ReportRequest::create_sensor_data_report(
        "011000",
        Some(100),
        Some(20.5),
        Some(30),
        None,
        None,
        1,
        123,
    );
    
    println!("Initial request created");
    
    // Enable auth
    request.enable_auth("wip");
    println!("Auth enabled");
    
    // Set auth flags
    request.set_auth_flags();
    println!("Auth flags set");
    
    // Generate packet
    let packet = request.to_bytes();
    println!("Packet generated with length: {} bytes", packet.len());
    println!("Full packet hex dump:");
    for (i, chunk) in packet.chunks(16).enumerate() {
        print!("{:04X}: ", i * 16);
        for byte in chunk {
            print!("{:02X} ", byte);
        }
        // Pad with spaces if less than 16 bytes
        for _ in chunk.len()..16 {
            print!("   ");
        }
        print!(" | ");
        for byte in chunk {
            let ch = if *byte >= 32 && *byte <= 126 { *byte as char } else { '.' };
            print!("{}", ch);
        }
        println!();
    }
    
    // Show basic packet structure
    if packet.len() >= 20 {
        println!("\n=== Basic Packet Structure (first 20 bytes) ===");
        println!("Header: {:02X?}", &packet[0..20]);
        
        if packet.len() > 20 {
            println!("Extension fields: {:02X?}", &packet[20..]);
        }
    }
}