use wip_rust::wip_common_rs::utils::auth::WIPAuth;
use hmac::{Hmac, Mac};
use sha2::Sha256;

type HmacSha256 = Hmac<Sha256>;

fn main() {
    println!("=== Rust版詳細認証ハッシュ比較 ===");
    
    // Python版と同じテストケース
    let test_cases = vec![
        ("テストケース1（固定値）", 1u16, 1634567890u64, "wip"),
        ("テストケース2（debug_auth_details相当）", 123u16, 1755828175u64, "wip"),
    ];
    
    for (name, packet_id, timestamp, passphrase) in test_cases {
        println!("\n{}:", name);
        println!("  packet_id: {} (型: u16)", packet_id);
        println!("  timestamp: {} (型: u64)", timestamp);
        println!("  passphrase: '{}' (型: &str)", passphrase);
        
        // 認証データの構築
        let auth_data_str = format!("{}:{}:{}", packet_id, timestamp, passphrase);
        println!("  auth_data文字列: '{}'", auth_data_str);
        println!("  auth_data長: {} 文字", auth_data_str.len());
        
        // バイト列への変換
        let auth_data_bytes = auth_data_str.as_bytes();
        let passphrase_bytes = passphrase.as_bytes();
        
        println!("  auth_data_bytes: {:?}", auth_data_bytes);
        println!("  auth_data_bytes長: {} バイト", auth_data_bytes.len());
        println!("  passphrase_bytes: {:?}", passphrase_bytes);
        println!("  passphrase_bytes長: {} バイト", passphrase_bytes.len());
        
        // WIPAuth::calculate_auth_hash()を使用
        let hash_result = WIPAuth::calculate_auth_hash(packet_id, timestamp, passphrase);
        println!("  WIPAuth結果: {}", hex::encode(&hash_result));
        println!("  WIPAuth結果長: {} バイト", hash_result.len());
        
        // 手動HMAC計算
        let mut mac = HmacSha256::new_from_slice(passphrase_bytes).unwrap();
        mac.update(auth_data_bytes);
        let manual_hmac = mac.finalize().into_bytes();
        
        println!("  手動HMAC結果: {}", hex::encode(&manual_hmac));
        println!("  手動HMAC結果長: {} バイト", manual_hmac.len());
        
        // 一致確認
        let matches = hash_result == manual_hmac.to_vec();
        println!("  一致: {}", matches);
        
        // バイト単位での比較
        if !matches {
            println!("  【不一致詳細】");
            for (i, (a, b)) in hash_result.iter().zip(manual_hmac.iter()).enumerate() {
                if a != b {
                    println!("    バイト{}: WIPAuth={:02x}, 手動={:02x}", i, a, b);
                }
            }
        }
    }
    
    // データ型の影響をテスト
    println!("\n=== データ型による影響テスト ===");
    
    let packet_id = 123u16;
    let timestamp = 1755828175u64;
    let passphrase = "wip";
    
    // 異なる形式でauth_dataを構築
    let formats = vec![
        ("u16:u64形式", format!("{}:{}:{}", packet_id, timestamp, passphrase)),
        ("強制的にi32:i64", format!("{}:{}:{}", packet_id as i32, timestamp as i64, passphrase)),
        ("文字列化後再構築", {
            let pid_str = packet_id.to_string();
            let ts_str = timestamp.to_string();
            format!("{}:{}:{}", pid_str, ts_str, passphrase)
        }),
    ];
    
    for (name, auth_data) in formats {
        println!("\n{}:", name);
        println!("  auth_data: '{}'", auth_data);
        
        let mut mac = HmacSha256::new_from_slice(passphrase.as_bytes()).unwrap();
        mac.update(auth_data.as_bytes());
        let result = mac.finalize().into_bytes();
        println!("  結果: {}", hex::encode(&result));
    }
    
    // バイト表現の詳細
    println!("\n=== バイト表現詳細 ===");
    let auth_data = format!("{}:{}:{}", 123u16, 1755828175u64, "wip");
    println!("文字列: '{}'", auth_data);
    println!("UTF-8バイト:");
    for (i, &byte) in auth_data.as_bytes().iter().enumerate() {
        println!("  [{:2}]: 0x{:02x} = {} ('{}')", i, byte, byte, 
                if byte >= 32 && byte <= 126 { byte as char } else { '?' });
    }
}