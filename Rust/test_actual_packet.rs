// 実際に生成されたパケットの詳細分析

fn analyze_packet(packet: &[u8]) {
    println!("パケット分析: {:02X?}", packet);
    println!("長さ: {} バイト", packet.len());
    
    if packet.len() >= 2 {
        let first_two = u16::from_le_bytes([packet[0], packet[1]]);
        println!("\n最初の2バイト: 0x{:04X} = {:016b}", first_two, first_two);
        
        // ビットフィールド解析
        let version = first_two & 0x0F;  // bit 0-3
        let packet_id = (first_two >> 4) & 0x0FFF;  // bit 4-15
        
        println!("  version (bit 0-3): {} (期待値: 1)", version);
        println!("  packet_id (bit 4-15): {} (期待値: 低い値)", packet_id);
        
        if packet.len() >= 3 {
            let third_byte = packet[2];
            let packet_type = third_byte & 0x07;  // bit 16-18 (third byte の bit 0-2)
            
            println!("\n3バイト目: 0x{:02X} = {:08b}", third_byte, third_byte);
            println!("  packet_type (bit 16-18): {} (期待値: 2 for Query)", packet_type);
            
            // フラグ分析
            let weather_flag = (third_byte >> 3) & 0x01;  // bit 19
            let temperature_flag = (third_byte >> 4) & 0x01;  // bit 20
            let pop_flag = (third_byte >> 5) & 0x01;  // bit 21
            let alert_flag = (third_byte >> 6) & 0x01;  // bit 22
            let disaster_flag = (third_byte >> 7) & 0x01;  // bit 23
            
            println!("  weather_flag (bit 19): {}", weather_flag);
            println!("  temperature_flag (bit 20): {}", temperature_flag);
            println!("  pop_flag (bit 21): {}", pop_flag);
            println!("  alert_flag (bit 22): {}", alert_flag);
            println!("  disaster_flag (bit 23): {}", disaster_flag);
        }
        
        if packet.len() >= 4 {
            let fourth_byte = packet[3];
            let ex_flag = fourth_byte & 0x01;  // bit 24
            let request_auth = (fourth_byte >> 1) & 0x01;  // bit 25
            let response_auth = (fourth_byte >> 2) & 0x01;  // bit 26
            let day = (fourth_byte >> 3) & 0x07;  // bit 27-29
            let reserved = (fourth_byte >> 6) & 0x03;  // bit 30-31
            
            println!("\n4バイト目: 0x{:02X} = {:08b}", fourth_byte, fourth_byte);
            println!("  ex_flag (bit 24): {}", ex_flag);
            println!("  request_auth (bit 25): {}", request_auth);
            println!("  response_auth (bit 26): {}", response_auth);
            println!("  day (bit 27-29): {}", day);
            println!("  reserved (bit 30-31): {}", reserved);
        }
        
        if packet.len() >= 12 {
            // timestamp (bit 32-95 = byte 4-11)
            let mut timestamp_bytes = [0u8; 8];
            timestamp_bytes.copy_from_slice(&packet[4..12]);
            let timestamp = u64::from_le_bytes(timestamp_bytes);
            
            println!("\ntimestamp (bit 32-95): {} (0x{:016X})", timestamp, timestamp);
        }
        
        if packet.len() >= 14 {
            // area_code (bit 96-115 = byte 12-13の一部)
            let byte12_13 = u16::from_le_bytes([packet[12], packet[13]]);
            let area_code = byte12_13 as u32 & 0xFFFFF;  // 20ビット but only using 16 for now
            
            println!("\narea_code (bit 96-115): {} (0x{:05X})", area_code, area_code);
        }
        
        if packet.len() >= 16 {
            // checksum (bit 116-127)
            let byte14_15 = u16::from_le_bytes([packet[14], packet[15]]);
            let checksum = byte14_15 & 0x0FFF;  // 12ビット
            
            println!("\nchecksum (bit 116-127): {} (0x{:03X})", checksum, checksum);
        }
    }
}

fn main() {
    // 実際に出力されたパケット
    let actual_packet = [0x11u8, 0x00, 0x0A, 0x00, 0x7F, 0xEF, 0xA2, 0x68, 0x00, 0x00, 0x00, 0x00, 0xF8, 0x2A, 0xA0, 0xC4];
    
    println!("=== Rustクライアントが実際に送信したパケット ===");
    analyze_packet(&actual_packet);
    
    println!("\n=== 期待される内容 ===");
    println!("version: 1");
    println!("packet_id: 1 (or small value)");
    println!("type: 2 (Query)");
    println!("weather_flag: 1 (true)");
    println!("temperature_flag: 0 (false)");
    println!("area_code: 11000");
}