use wip_rust::wip_common_rs::utils::auth::WIPAuth;

fn main() {
    println!("=== 認証ハッシュ計算の比較テスト ===");
    
    // テストケース1: 基本的なパラメータ
    let packet_id1 = 1u16;
    let timestamp1 = 1634567890u64;  // 固定のタイムスタンプ
    let passphrase1 = "wip";
    
    let hash1 = WIPAuth::calculate_auth_hash(packet_id1, timestamp1, passphrase1);
    println!("テストケース1:");
    println!("  packet_id: {}", packet_id1);
    println!("  timestamp: {}", timestamp1);
    println!("  passphrase: {}", passphrase1);
    println!("  auth_data: {}:{}:{}", packet_id1, timestamp1, passphrase1);
    println!("  Rust計算結果: {}", hex::encode(&hash1));
    println!();
    
    // テストケース2: 現在のタイムスタンプ（test_auth_packet.rsと同じ条件）
    let packet_id2 = 1u16;
    let timestamp2 = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap()
        .as_secs();
    let passphrase2 = "wip";
    
    let hash2 = WIPAuth::calculate_auth_hash(packet_id2, timestamp2, passphrase2);
    println!("テストケース2（現在時刻）:");
    println!("  packet_id: {}", packet_id2);
    println!("  timestamp: {}", timestamp2);
    println!("  passphrase: {}", passphrase2);
    println!("  auth_data: {}:{}:{}", packet_id2, timestamp2, passphrase2);
    println!("  Rust計算結果: {}", hex::encode(&hash2));
    println!();
    
    // テストケース3: データ型の境界値
    let packet_id3 = 65535u16;  // u16のmax値
    let timestamp3 = 4294967295u64;  // u32のmax値
    let passphrase3 = "complex_pass!@#$%";
    
    let hash3 = WIPAuth::calculate_auth_hash(packet_id3, timestamp3, passphrase3);
    println!("テストケース3（境界値）:");
    println!("  packet_id: {}", packet_id3);
    println!("  timestamp: {}", timestamp3);
    println!("  passphrase: {}", passphrase3);
    println!("  auth_data: {}:{}:{}", packet_id3, timestamp3, passphrase3);
    println!("  Rust計算結果: {}", hex::encode(&hash3));
    println!();
    
    // 手動でPython版の計算をエミュレート
    println!("=== Python版エミュレーション ===");
    let auth_data_bytes = format!("{}:{}:{}", packet_id1, timestamp1, passphrase1);
    println!("auth_data文字列: '{}'", auth_data_bytes);
    println!("auth_data bytes: {:?}", auth_data_bytes.as_bytes());
    println!("passphrase bytes: {:?}", passphrase1.as_bytes());
    
    // HMACの詳細を確認
    use hmac::{Hmac, Mac};
    use sha2::Sha256;
    type HmacSha256 = Hmac<Sha256>;
    
    let mut mac = HmacSha256::new_from_slice(passphrase1.as_bytes()).unwrap();
    mac.update(auth_data_bytes.as_bytes());
    let result = mac.finalize().into_bytes();
    
    println!("手動HMAC計算結果: {}", hex::encode(&result));
    println!("元の計算結果:     {}", hex::encode(&hash1));
    println!("一致: {}", hex::encode(&result) == hex::encode(&hash1));
}