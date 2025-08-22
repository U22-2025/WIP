use wip_rust::wip_common_rs::packet::types::report_packet::ReportRequest;
use wip_rust::wip_common_rs::utils::auth::WIPAuth;
use wip_rust::wip_common_rs::packet::core::extended_field::{unpack_ext_fields};

fn main() {
    println!("=== 詳細な認証情報デバッグ ===");
    
    // ReportRequestを作成
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
    
    println!("=== 1. パケット初期情報 ===");
    println!("packet_id: {}", request.packet_id);
    println!("timestamp: {}", request.timestamp);
    
    // 認証を有効化
    request.enable_auth("wip");
    println!("\n=== 2. 認証有効化後 ===");
    println!("認証が有効化されました");
    
    // 認証フラグを設定
    request.set_auth_flags();
    println!("\n=== 3. 認証フラグ設定後 ===");
    println!("request_auth: {}", request.request_auth);
    println!("response_auth: {}", request.response_auth);
    println!("ex_flag: {}", request.ex_flag);
    
    // 期待される認証ハッシュを手動計算
    let expected_hash = WIPAuth::calculate_auth_hash(
        request.packet_id,
        request.timestamp,
        "wip"
    );
    println!("\n=== 4. 期待される認証ハッシュ ===");
    println!("auth_data: {}:{}:wip", request.packet_id, request.timestamp);
    println!("expected_hash: {}", hex::encode(&expected_hash));
    
    // 拡張フィールドから実際のauth_hashを取得
    if let Some(ref ext) = request.ext {
        if let Some(auth_hash_value) = ext.get_value("auth_hash") {
            println!("\n=== 5. 拡張フィールドのauth_hash ===");
            println!("auth_hash in ext field: {:?}", auth_hash_value);
        } else {
            println!("\n=== 5. 拡張フィールドエラー ===");
            println!("auth_hash not found in extension field!");
        }
        
        // 拡張フィールドの全ての値を表示
        println!("\n=== 6. 全拡張フィールド ===");
        for (key, value) in ext.get_all_values() {
            println!("  {}: {:?}", key, value);
        }
    } else {
        println!("\n=== 5. 拡張フィールドエラー ===");
        println!("Extension field is None!");
    }
    
    // パケットを生成
    let packet = request.to_bytes();
    println!("\n=== 7. 生成されたパケット ===");
    println!("パケット長: {} bytes", packet.len());
    
    // ヘッダー部分（最初の20バイト）
    if packet.len() >= 20 {
        println!("ヘッダー部分: {:02X?}", &packet[0..20]);
        
        // 拡張フィールド部分（20バイト以降）
        if packet.len() > 20 {
            let ext_bytes = &packet[20..];
            println!("拡張フィールド部分: {:02X?}", ext_bytes);
            
            // 拡張フィールドをunpackして確認
            let unpacked = unpack_ext_fields(ext_bytes);
            println!("\n=== 8. unpackされた拡張フィールド ===");
            for (key, value) in unpacked {
                println!("  {}: {:?}", key, value);
                if key == "auth_hash" {
                    if let wip_rust::wip_common_rs::packet::core::extended_field::FieldValue::String(hash_str) = value {
                        println!("    -> バイト列: {:02X?}", hex::decode(&hash_str).unwrap_or_default());
                        println!("    -> 期待値と一致: {}", hex::encode(&expected_hash) == hash_str);
                    }
                }
            }
        }
    }
    
    println!("\n=== 9. 完全な16進ダンプ ===");
    for (i, chunk) in packet.chunks(16).enumerate() {
        print!("{:04X}: ", i * 16);
        for byte in chunk {
            print!("{:02X} ", byte);
        }
        // 16バイト未満の場合はスペースで埋める
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
}