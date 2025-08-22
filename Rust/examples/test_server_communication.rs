use wip_rust::wip_common_rs::packet::types::report_packet::ReportRequest;
use std::net::UdpSocket;
use std::time::Duration;

fn main() {
    println!("=== サーバー通信テスト ===");
    
    // 実際のReportRequestを作成
    let mut request = ReportRequest::create_sensor_data_report(
        "011000",
        Some(100),
        Some(20.5), 
        Some(30),
        None,
        None,
        1,    // version
        123,  // packet_id
    );
    
    println!("=== パケット送信前 ===");
    println!("packet_id: {}", request.packet_id);
    println!("timestamp: {}", request.timestamp);
    
    // 認証を有効化
    request.enable_auth("wip");
    request.set_auth_flags();
    
    // パケットを生成
    let packet = request.to_bytes();
    
    println!("パケット長: {} bytes", packet.len());
    println!("パケット内容（最初の50バイト）: {:02X?}", &packet[..50.min(packet.len())]);
    
    // サーバーに送信
    println!("\n=== サーバーに送信中 ===");
    let socket = UdpSocket::bind("0.0.0.0:0").expect("Failed to bind socket");
    socket.set_read_timeout(Some(Duration::from_secs(5))).expect("Failed to set timeout");
    
    // Report Server（port 4112）に送信
    let server_addr = "localhost:4112";
    match socket.send_to(&packet, server_addr) {
        Ok(bytes_sent) => {
            println!("送信成功: {} bytes to {}", bytes_sent, server_addr);
            
            // レスポンス受信
            let mut response_buffer = [0u8; 1024];
            match socket.recv_from(&mut response_buffer) {
                Ok((bytes_received, from_addr)) => {
                    println!("レスポンス受信: {} bytes from {}", bytes_received, from_addr);
                    let response_data = &response_buffer[..bytes_received];
                    println!("レスポンスデータ: {:02X?}", response_data);
                    
                    // レスポンスパケットの解析
                    if bytes_received >= 20 {
                        use bitvec::prelude::*;
                        let bits = BitSlice::<u8, bitvec::order::Lsb0>::from_slice(&response_data[..20]);
                        
                        let response_version: u8 = bits[0..4].load();
                        let response_packet_id: u16 = bits[4..16].load();
                        let response_type: u8 = bits[16..19].load();
                        
                        println!("\n=== レスポンス解析 ===");
                        println!("version: {}", response_version);
                        println!("packet_id: {}", response_packet_id);
                        println!("type: {}", response_type);
                        
                        // エラーパケットかどうか確認
                        if response_type == 6 {
                            println!("⚠️  エラーレスポンス受信");
                            
                            // エラーの詳細を解析
                            if bytes_received > 20 {
                                println!("拡張フィールド: {:02X?}", &response_data[20..]);
                            }
                        } else {
                            println!("✅ 正常レスポンス受信");
                        }
                    }
                }
                Err(e) => {
                    println!("❌ レスポンス受信エラー: {}", e);
                }
            }
        }
        Err(e) => {
            println!("❌ 送信エラー: {}", e);
        }
    }
    
    println!("\n=== サーバーログの確認指示 ===");
    println!("サーバー側のログを確認して以下を調べてください:");
    println!("1. 受信したパケットのpacket_id: {}", request.packet_id);
    println!("2. 受信したパケットのtimestamp: {}", request.timestamp);
    println!("3. サーバー側で使用されているpassphrase");
    println!("4. サーバー側で計算された認証ハッシュ");
    println!("5. 比較に使用された受信認証ハッシュ");
}