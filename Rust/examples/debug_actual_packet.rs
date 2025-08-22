use wip_rust::wip_common_rs::packet::types::report_packet::ReportRequest;
use wip_rust::wip_common_rs::utils::auth::WIPAuth;

fn main() {
    println!("=== 実際のパケット内容デバッグ ===");
    
    // 実際のReportRequestを作成（unified_clientと同じパラメータ）
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
    
    println!("=== パケット作成後の状態 ===");
    println!("packet_id: {}", request.packet_id);
    println!("timestamp: {}", request.timestamp);
    println!("version: {}", request.version);
    
    // 認証を有効化
    request.enable_auth("wip");
    request.set_auth_flags();
    
    // パケットを生成
    let packet = request.to_bytes();
    
    println!("\n=== 生成されたパケット詳細 ===");
    println!("パケット長: {} bytes", packet.len());
    
    // パケットからタイムスタンプを読み取って確認
    if packet.len() >= 20 {
        use bitvec::prelude::*;
        let bits = BitSlice::<u8, bitvec::order::Lsb0>::from_slice(&packet[..20]);
        
        let extracted_version: u8 = bits[0..4].load();
        let extracted_packet_id: u16 = bits[4..16].load();
        let extracted_timestamp: u64 = bits[32..96].load();
        let extracted_area_code: u32 = bits[96..116].load();
        
        println!("パケット内容:");
        println!("  version: {}", extracted_version);
        println!("  packet_id: {}", extracted_packet_id);
        println!("  timestamp: {}", extracted_timestamp);
        println!("  area_code: {}", extracted_area_code);
        
        // 実際のパケット内のタイムスタンプを使って認証ハッシュを再計算
        println!("\n=== パケット内タイムスタンプでの認証ハッシュ ===");
        let packet_auth_hash = WIPAuth::calculate_auth_hash(
            extracted_packet_id,
            extracted_timestamp,
            "wip"
        );
        println!("認証データ: {}:{}:wip", extracted_packet_id, extracted_timestamp);
        println!("認証ハッシュ: {}", hex::encode(&packet_auth_hash));
        
        // 拡張フィールドから実際のauth_hashを確認
        if packet.len() > 20 {
            let ext_bytes = &packet[20..];
            println!("\n=== 拡張フィールド内容 ===");
            println!("拡張フィールド: {:02X?}", ext_bytes);
            
            // 拡張フィールドのauth_hashを抽出
            if ext_bytes.len() >= 34 { // 2バイトヘッダー + 32バイトハッシュ
                let auth_hash_in_packet = &ext_bytes[2..34];
                println!("パケット内auth_hash: {}", hex::encode(auth_hash_in_packet));
                println!("計算されたauth_hash: {}", hex::encode(&packet_auth_hash));
                println!("一致: {}", auth_hash_in_packet == packet_auth_hash.as_slice());
            }
        }
        
        // 構造体の値と実際のパケット内容の比較
        println!("\n=== 構造体 vs パケット内容 ===");
        println!("構造体timestamp: {} vs パケット内timestamp: {}", request.timestamp, extracted_timestamp);
        println!("構造体packet_id: {} vs パケット内packet_id: {}", request.packet_id, extracted_packet_id);
        
        // もし不一致があれば、構造体の値で計算した認証ハッシュも表示
        if request.timestamp != extracted_timestamp || request.packet_id != extracted_packet_id {
            println!("\n=== 構造体の値での認証ハッシュ ===");
            let struct_auth_hash = WIPAuth::calculate_auth_hash(
                request.packet_id,
                request.timestamp,
                "wip"
            );
            println!("認証データ: {}:{}:wip", request.packet_id, request.timestamp);
            println!("認証ハッシュ: {}", hex::encode(&struct_auth_hash));
        }
    }
}