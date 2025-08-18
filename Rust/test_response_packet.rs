// レスポンスパケット分析

fn analyze_response_packet(packet: &[u8]) {
    println!("レスポンスパケット分析: {:02X?}", packet);
    println!("長さ: {} バイト", packet.len());
    
    if packet.len() >= 2 {
        let first_two = u16::from_le_bytes([packet[0], packet[1]]);
        println!("\n最初の2バイト: 0x{:04X} = {:016b}", first_two, first_two);
        
        // ビットフィールド解析
        let version = first_two & 0x0F;  // bit 0-3
        let packet_id = (first_two >> 4) & 0x0FFF;  // bit 4-15
        
        println!("  version (bit 0-3): {}", version);
        println!("  packet_id (bit 4-15): {}", packet_id);
        
        if packet.len() >= 3 {
            let third_byte = packet[2];
            let packet_type = third_byte & 0x07;  // bit 16-18
            
            println!("\n3バイト目: 0x{:02X} = {:08b}", third_byte, third_byte);
            println!("  packet_type (bit 16-18): {} (期待値: 3 for QueryResponse または 7 for Error)", packet_type);
        }
        
        // Error Response (Type 7) の場合
        if packet.len() >= 3 && (packet[2] & 0x07) == 7 {
            println!("\n=== Error Response (Type 7) ===");
            
            if packet.len() >= 4 {
                let error_code = packet[3];
                println!("Error Code: {}", error_code);
                
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
                println!("Error Message: {}", error_message);
            }
        }
        
        // QueryResponse (Type 3) の場合
        else if packet.len() >= 3 && (packet[2] & 0x07) == 3 {
            println!("\n=== Query Response (Type 3) ===");
            
            // 基本情報はヘッダの最初の16バイト
            if packet.len() >= 16 {
                // area_code (bit 96-115)
                let area_code_bytes = u32::from_le_bytes([packet[12], packet[13], packet[14], packet[15]]);
                let area_code = (area_code_bytes >> 0) & 0xFFFFF;  // 20ビット
                
                println!("Area Code: {} (0x{:05X})", area_code, area_code);
            }
            
            // 拡張データ（16バイト以降）
            if packet.len() > 16 {
                println!("\n拡張データ ({} バイト):", packet.len() - 16);
                let extended_data = &packet[16..];
                println!("  {:02X?}", extended_data);
                
                if extended_data.len() >= 2 {
                    let weather_code = u16::from_le_bytes([extended_data[0], extended_data[1]]);
                    println!("  weather_code: {} (0x{:04X})", weather_code, weather_code);
                }
                
                if extended_data.len() >= 3 {
                    let temp_raw = extended_data[2];
                    if temp_raw != 0 {
                        let temperature = (temp_raw as i16) - 100;
                        println!("  temperature: {}°C (raw: {})", temperature, temp_raw);
                    } else {
                        println!("  temperature: not available");
                    }
                }
                
                if extended_data.len() >= 4 {
                    let precipitation = extended_data[3];
                    if precipitation != 0 {
                        println!("  precipitation: {}%", precipitation);
                    } else {
                        println!("  precipitation: not available");
                    }
                }
            }
        }
    }
}

fn main() {
    // 実際に受信したレスポンス
    let response_packet = [
        0x11u8, 0x00, 0x07, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x50, 0xCA,
        0x03, 0x00, 0x00, 0x00, 0x07, 0xA0, 0xC7, 0x1C, 0xA8, 0x2C, 0x95, 0x1E, 0x2D
    ];
    
    println!("=== Pythonサーバーからの実際のレスポンス ===");
    analyze_response_packet(&response_packet);
}