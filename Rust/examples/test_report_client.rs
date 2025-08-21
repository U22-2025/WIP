use wip_rust::wip_common_rs::clients::report_client::{ReportClient, ReportClientImpl};
use wip_rust::wip_common_rs::packet::types::report_packet::ReportRequest;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
    println!("Testing ReportClient communication with server...");
    
    // Create report client
    let client = ReportClientImpl::new("127.0.0.1", 4112).await?;
    
    // Create a test report request
    let report = ReportRequest::create_sensor_data_report(
        "011000",        // area_code
        Some(10),        // weather_code
        Some(22.0),      // temperature_c
        Some(30),        // precipitation_prob
        None,            // alert
        None,            // disaster
        1,               // version
        0x100,          // packet_id (will be overridden)
    );
    
    println!("Sending report to server...");
    match client.send_report(report).await {
        Ok(response) => {
            println!("✅ Report sent successfully!");
            println!("Response packet ID: {}", response.packet_id);
            println!("Response area code: {}", response.area_code);
            if let Some(weather) = response.weather_code {
                println!("Response weather code: {}", weather);
            }
            if let Some(temp) = response.temperature_c {
                println!("Response temperature: {}°C", temp);
            }
            if let Some(pop) = response.pop {
                println!("Response precipitation: {}%", pop);
            }
        }
        Err(e) => {
            println!("❌ Failed to send report: {}", e);
            return Err(e);
        }
    }
    
    Ok(())
}