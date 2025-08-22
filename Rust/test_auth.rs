use std::collections::HashMap;
mod wip_common_rs;

use wip_common_rs::packet::types::report_packet::ReportRequest;

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
    println!("Packet bytes: {:02X?}", packet);
}