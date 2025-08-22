use wip_rust::wip_common_rs::packet::types::report_packet::ReportRequest;
use wip_rust::wip_common_rs::utils::auth::WIPAuth;
use std::env;

fn main() {
    println!("=== サーバー認証テスト ===");
    
    // 実際のReportRequestを作成（unified_clientと同様）
    let mut request = ReportRequest::create_sensor_data_report(
        "011000",  // area_code
        Some(100), // temperature_c  
        Some(20.5), // humidity_percent
        Some(30),   // pressure_hpa
        None,       // wind_speed_ms
        None,       // rainfall_mm
        1,          // packet_id
        123,        // timestamp - これは固定値として設定
    );
    
    println!("=== 作成されたパケット情報 ===");
    println!("packet_id: {}", request.packet_id);
    println!("timestamp: {}", request.timestamp);
    
    // 環境変数からパスフレーズを取得（サーバーと同じ）
    let passphrase = env::var("REPORT_SERVER_PASSPHRASE").unwrap_or_else(|_| "wip".to_string());
    println!("使用するpassphrase: '{}'", passphrase);
    
    // 認証を有効化
    request.enable_auth(&passphrase);
    request.set_auth_flags();
    
    println!("\n=== 期待される認証ハッシュ ===");
    let expected_hash = WIPAuth::calculate_auth_hash(
        request.packet_id,
        request.timestamp,
        &passphrase
    );
    println!("auth_data: {}:{}:{}", request.packet_id, request.timestamp, passphrase);
    println!("expected_hash: {}", hex::encode(&expected_hash));
    
    // パケットを生成して内容を確認
    let packet = request.to_bytes();
    println!("\n=== 生成されたパケット ===");
    println!("パケット長: {} bytes", packet.len());
    
    // 拡張フィールド部分を解析
    if packet.len() > 20 {
        let ext_bytes = &packet[20..];
        println!("拡張フィールド部分: {:02X?}", ext_bytes);
        
        // ヘッダー解析
        if ext_bytes.len() >= 2 {
            let len_bits = (ext_bytes[0] as u16) | ((ext_bytes[1] as u16 & 0x03) << 8);
            let id_bits = (ext_bytes[1] >> 2) & 0x3F;
            println!("拡張フィールドヘッダー:");
            println!("  長さ: {} bytes", len_bits);
            println!("  ID: {}", id_bits);
            
            if ext_bytes.len() > 2 {
                let auth_hash_bytes = &ext_bytes[2..];
                println!("  auth_hashバイト列: {:02X?}", auth_hash_bytes);
                println!("  auth_hash16進: {}", hex::encode(auth_hash_bytes));
                
                // 期待値との比較
                let expected_bytes = hex::decode(&hex::encode(&expected_hash)).unwrap();
                println!("  期待値と一致: {}", auth_hash_bytes == expected_bytes);
            }
        }
    }
    
    // 複数のパスフレーズでテスト
    println!("\n=== 複数パスフレーズテスト ===");
    let test_passphrases = vec!["wip", "test_passphrase", "", "default"];
    
    for test_pass in test_passphrases {
        let hash = WIPAuth::calculate_auth_hash(
            request.packet_id,
            request.timestamp,
            test_pass
        );
        println!("passphrase '{}': {}", test_pass, hex::encode(&hash));
    }
    
    // タイムスタンプのバリエーション
    println!("\n=== タイムスタンプバリエーション ===");
    let current_time = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap()
        .as_secs();
    
    let timestamps = vec![
        request.timestamp,
        current_time,
        current_time - 1,
        current_time + 1,
    ];
    
    for ts in timestamps {
        let hash = WIPAuth::calculate_auth_hash(
            request.packet_id,
            ts,
            &passphrase
        );
        println!("timestamp {}: {}", ts, hex::encode(&hash));
    }
}