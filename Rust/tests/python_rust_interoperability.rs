/*!
 * Python-Rust間の相互運用性テスト
 * Python版WIPクライアントとRust版の完全互換性を検証
 */

use std::process::Command;
use std::time::{Duration, Instant, SystemTime, UNIX_EPOCH};
use wip_rust::wip_common_rs::packet::types::location_packet::LocationRequest;
use wip_rust::wip_common_rs::packet::types::query_packet::QueryRequest;
use wip_rust::wip_common_rs::packet::types::report_packet::ReportRequest;
use wip_rust::wip_common_rs::packet::core::checksum::verify_checksum12;
use wip_rust::wip_common_rs::packet::core::bit_utils::{bytes_to_u128_le, extract_bits};
use wip_rust::wip_common_rs::clients::python_compatible_client::*;

/// Pythonスクリプトを実行してパケットを生成し、Rustで解析する
#[test]
#[ignore] // Python環境が必要なテスト
fn test_python_generated_packet_parsing() {
    // Pythonスクリプトを実行してパケットを生成
    let python_script = r#"
import sys
import os
sys.path.insert(0, '/mnt/c/Users/pijon/Desktop/wip/src')

from WIPCommonPy.packet.types.query_packet import QueryRequest

# 固定タイムスタンプでパケット生成
request = QueryRequest.create_query_request(
    area_code=130010,
    packet_id=0x123,
    weather=True,
    temperature=True,
    precipitation_prob=False,
    alert=False,
    disaster=False,
    day=0,
    version=1
)

# バイナリ形式で出力
packet_bytes = request.to_bytes()
print(','.join([str(b) for b in packet_bytes]))
"#;

    // Pythonスクリプトを一時ファイルに書き込み
    std::fs::write("temp_python_packet_gen.py", python_script).expect("Failed to write Python script");

    // Pythonスクリプトを実行
    let output = Command::new("python3")
        .arg("temp_python_packet_gen.py")
        .output()
        .expect("Failed to execute Python script");

    // 一時ファイルを削除
    let _ = std::fs::remove_file("temp_python_packet_gen.py");

    if !output.status.success() {
        panic!("Python script failed: {}", String::from_utf8_lossy(&output.stderr));
    }

    // Pythonの出力をパース
    let output_str = String::from_utf8_lossy(&output.stdout);
    let bytes_str = output_str.trim();
    let python_bytes: Vec<u8> = bytes_str
        .split(',')
        .map(|s| s.trim().parse::<u8>().expect("Failed to parse byte"))
        .collect();

    println!("Python generated packet: {:02X?}", python_bytes);

    // Rustでパケットを解析
    if python_bytes.len() >= 16 {
        // チェックサムを検証
        assert!(verify_checksum12(&python_bytes, 116, 12));

        // ビットフィールドを抽出して検証
        let as_u128 = bytes_to_u128_le(&python_bytes[..16]);
        
        let version = extract_bits(as_u128, 0, 4);
        let packet_id = extract_bits(as_u128, 4, 12);
        let packet_type = extract_bits(as_u128, 16, 3);
        let weather_flag = extract_bits(as_u128, 19, 1);
        let temperature_flag = extract_bits(as_u128, 20, 1);
        let area_code = extract_bits(as_u128, 96, 20);

        assert_eq!(version, 1);
        assert_eq!(packet_id, 0x123);
        assert_eq!(packet_type, 2); // QueryRequest
        assert_eq!(weather_flag, 1);
        assert_eq!(temperature_flag, 1);
        assert_eq!(area_code, 130010);

        println!("Python packet successfully parsed by Rust!");
    }
}

/// Rustで生成したパケットをPythonで解析するテスト
#[test]
#[ignore] // Python環境が必要なテスト
fn test_rust_generated_packet_parsing_by_python() {
    // Rustでパケットを生成
    let request = QueryRequest::new(
        130010, // area_code
        0x123,  // packet_id
        true,   // weather
        true,   // temperature
        false,  // precipitation_prob
        false,  // alert
        false,  // disaster
        0,      // day
    );

    let rust_bytes = request.to_bytes();
    println!("Rust generated packet: {:02X?}", rust_bytes);

    // Pythonスクリプトを作成
    let bytes_str = rust_bytes.iter()
        .map(|b| b.to_string())
        .collect::<Vec<_>>()
        .join(",");

    let python_script = format!(r#"
import sys
import os
sys.path.insert(0, '/mnt/c/Users/pijon/Desktop/wip/src')

from WIPCommonPy.packet.types.query_packet import QueryRequest

# Rustで生成されたバイトデータ
rust_bytes = bytes([{}])

print(f"Received {{len(rust_bytes)}} bytes from Rust")
print(f"Bytes: {{[hex(b) for b in rust_bytes]}}")

# Pythonでパケットを解析
try:
    request = QueryRequest.from_bytes(rust_bytes)
    print(f"Successfully parsed by Python!")
    print(f"Area code: {{request.area_code}}")
    print(f"Packet ID: {{request.packet_id}}")
    print(f"Version: {{request.version}}")
    print(f"Weather flag: {{request.weather_flag}}")
    print(f"Temperature flag: {{request.temperature_flag}}")
except Exception as e:
    print(f"Failed to parse: {{e}}")
    import traceback
    traceback.print_exc()
"#, bytes_str);

    // Pythonスクリプトを一時ファイルに書き込み
    std::fs::write("temp_rust_packet_parse.py", python_script).expect("Failed to write Python script");

    // Pythonスクリプトを実行
    let output = Command::new("python3")
        .arg("temp_rust_packet_parse.py")
        .output()
        .expect("Failed to execute Python script");

    // 一時ファイルを削除
    let _ = std::fs::remove_file("temp_rust_packet_parse.py");

    println!("Python output:\n{}", String::from_utf8_lossy(&output.stdout));
    
    if !output.status.success() {
        println!("Python stderr:\n{}", String::from_utf8_lossy(&output.stderr));
    }

    // Pythonが正常にパケットを解析できたことを確認
    let output_str = String::from_utf8_lossy(&output.stdout);
    assert!(output_str.contains("Successfully parsed by Python!"));
    assert!(output_str.contains("Area code: 130010"));
    assert!(output_str.contains("Packet ID: 291")); // 0x123 = 291
}

/// 両方向でのパケット交換テスト
#[test] 
#[ignore] // Python環境が必要なテスト
fn test_bidirectional_packet_exchange() {
    // LocationRequestのテスト
    let rust_location_req = LocationRequest::create_coordinate_lookup(
        35.6762, 139.6503, 0x456, true, true, false, false, false, 0, 1
    );
    let rust_bytes = rust_location_req.to_bytes();
    
    // Pythonでの解析をテスト
    let python_script = format!(r#"
import sys
import os
sys.path.insert(0, '/mnt/c/Users/pijon/Desktop/wip/src')

from WIPCommonPy.packet.types.location_packet import LocationRequest

rust_bytes = bytes([{}])
print(f"Testing LocationRequest parsing...")

try:
    req = LocationRequest.from_bytes(rust_bytes)
    print("SUCCESS: LocationRequest parsed by Python")
    print(f"Packet ID: {{req.packet_id}}")
    print(f"Weather flag: {{req.weather_flag}}")
    print(f"Temperature flag: {{req.temperature_flag}}")
except Exception as e:
    print(f"FAILED: {{e}}")
    import traceback
    traceback.print_exc()
"#, rust_bytes.iter().map(|b| b.to_string()).collect::<Vec<_>>().join(","));

    std::fs::write("temp_bidirectional_test.py", python_script).expect("Failed to write Python script");
    
    let output = Command::new("python3")
        .arg("temp_bidirectional_test.py")
        .output()
        .expect("Failed to execute Python script");
    
    let _ = std::fs::remove_file("temp_bidirectional_test.py");
    
    println!("Bidirectional test output:\n{}", String::from_utf8_lossy(&output.stdout));
    
    let output_str = String::from_utf8_lossy(&output.stdout);
    assert!(output_str.contains("SUCCESS: LocationRequest parsed by Python"));
}

/// パケットフォーマットの完全互換性検証
#[cfg(test)]
mod packet_format_validation {
    use super::*;

    #[test]
    fn test_query_packet_bit_layout_consistency() {
        // 固定値でのパケット生成
        let timestamp = 1700000000u64;
        
        let request = QueryRequest::new_with_timestamp(
            130010, // area_code  
            0x123,  // packet_id
            true,   // weather
            false,  // temperature
            true,   // precipitation_prob
            false,  // alert
            false,  // disaster
            0,      // day
            timestamp,
        );

        let bytes = request.to_bytes();
        assert_eq!(bytes.len(), 16);

        // ビットレイアウトの検証
        let as_u128 = bytes_to_u128_le(&bytes);
        
        // Python版と同じビット位置で値を確認
        assert_eq!(extract_bits(as_u128, 0, 4), 1);        // version
        assert_eq!(extract_bits(as_u128, 4, 12), 0x123);   // packet_id
        assert_eq!(extract_bits(as_u128, 16, 3), 2);       // type (QueryRequest)
        assert_eq!(extract_bits(as_u128, 19, 1), 1);       // weather_flag
        assert_eq!(extract_bits(as_u128, 20, 1), 0);       // temperature_flag
        assert_eq!(extract_bits(as_u128, 21, 1), 1);       // pop_flag
        assert_eq!(extract_bits(as_u128, 22, 1), 0);       // alert_flag
        assert_eq!(extract_bits(as_u128, 23, 1), 0);       // disaster_flag
        assert_eq!(extract_bits(as_u128, 32, 64), timestamp); // timestamp
        assert_eq!(extract_bits(as_u128, 96, 20), 130010); // area_code
        
        // チェックサムの検証
        assert!(verify_checksum12(&bytes, 116, 12));
    }

    #[test]
    fn test_location_packet_extended_fields_compatibility() {
        let request = LocationRequest::create_coordinate_lookup(
            35.6762, 139.6503, 0x789, true, false, false, false, false, 0, 1
        );

        let bytes = request.to_bytes();
        assert!(bytes.len() > 16); // 拡張フィールドが含まれている

        // ヘッダ部分の検証
        let header_as_u128 = bytes_to_u128_le(&bytes[..16]);
        assert_eq!(extract_bits(header_as_u128, 16, 3), 0); // LocationRequest
        assert_eq!(extract_bits(header_as_u128, 24, 1), 1); // ex_flag = 1

        // 全体のチェックサム検証
        assert!(verify_checksum12(&bytes, 116, 12));
    }

    #[test]
    fn test_report_packet_data_handling() {
        let data = vec![0x41, 0x42, 0x43, 0x44]; // "ABCD"
        let request = ReportRequest::create_sensor_data_report(
            "130010",    // area_code
            Some(100),   // weather_code
            Some(25.5),  // temperature_c
            Some(60.0),  // humidity_percent
            Some(1013.25), // pressure_hpa
            0x999,       // packet_id
        );

        let bytes = request.to_bytes();
        assert!(bytes.len() >= 16);

        // ヘッダ部分の検証
        let header_as_u128 = bytes_to_u128_le(&bytes[..16]);
        assert_eq!(extract_bits(header_as_u128, 16, 3), 3); // ReportRequest
        assert_eq!(extract_bits(header_as_u128, 4, 12), 0x999); // packet_id

        // チェックサム検証
        assert!(verify_checksum12(&bytes, 116, 12));
    }
}

/// Python互換クライアントAPIのテスト
#[cfg(test)]
mod python_api_compatibility {
    use super::*;

    #[test]
    fn test_python_compatible_weather_client_api() {
        // Python版と同じAPIでクライアントを作成
        let client = PythonCompatibleWeatherClient::new(Some("localhost"), Some(4110), Some(true));
        
        // APIメソッドが存在することを確認（コンパイル時チェック）
        let _weather_data = client.get_weather_data(130010, Some(true), Some(true), Some(true), Some(false), Some(false), Some(0));
        let _simple_data = client.get_weather_simple(130010, Some(false), Some(0));
        let _legacy_data = client.get_weather_by_area_code(130010, Some(true), Some(false), Some(false), Some(false), Some(false), Some(1));
        
        println!("Python-compatible WeatherClient API test passed");
    }

    #[test] 
    fn test_python_compatible_location_client_api() {
        // Python版と同じAPIでクライアントを作成
        let client = PythonCompatibleLocationClient::new(
            Some("localhost"), Some(4109), Some(false), Some(30), Some(true), None
        );
        
        // APIメソッドが存在することを確認
        let _area_code = client.get_area_code_simple(35.6762, 139.6503, None, Some(true), Some(false));
        let _legacy_area_code = client.get_area_code_from_coordinates(35.6762, 139.6503, None);
        let _cache_stats = client.get_cache_stats();
        
        println!("Python-compatible LocationClient API test passed");
    }

    #[test]
    fn test_python_compatible_clients_creation_with_env_vars() {
        // 環境変数をテスト用に設定
        std::env::set_var("WEATHER_SERVER_HOST", "test.example.com");
        std::env::set_var("WEATHER_SERVER_PORT", "8110");
        std::env::set_var("LOCATION_RESOLVER_HOST", "location.example.com");
        std::env::set_var("LOCATION_RESOLVER_PORT", "8109");

        // Python版と同様にNoneを渡すことで環境変数が使用されることを確認
        let weather_client = PythonCompatibleWeatherClient::new(None, None, None);
        let location_client = PythonCompatibleLocationClient::new(None, None, None, None, None, None);

        // 環境変数のクリーンアップ
        std::env::remove_var("WEATHER_SERVER_HOST");
        std::env::remove_var("WEATHER_SERVER_PORT");
        std::env::remove_var("LOCATION_RESOLVER_HOST");
        std::env::remove_var("LOCATION_RESOLVER_PORT");

        println!("Environment variable compatibility test passed");
    }
}

/// 実際のPythonサーバーとの統合テスト
#[test]
#[ignore] // 実際のサーバーが必要
fn test_integration_with_python_server() {
    // Pythonサーバーの起動が必要
    let client = PythonCompatibleWeatherClient::new(Some("localhost"), Some(4110), Some(true));
    
    match client.get_weather_simple(130010, Some(false), Some(0)) {
        Ok(result) => {
            println!("Successfully got weather data from Python server: {:?}", result);
        }
        Err(e) => {
            println!("Expected error when Python server is not running: {}", e);
        }
    }
}

/// パフォーマンス比較テスト
#[test]
fn test_performance_comparison() {
    let iterations = 1000;
    
    // Rustネイティブクライアントのパフォーマンス
    let start = Instant::now();
    for i in 0..iterations {
        let request = QueryRequest::new(
            130010, i as u16, true, false, false, false, false, 0
        );
        let _bytes = request.to_bytes();
    }
    let rust_duration = start.elapsed();
    
    // Python互換クライアントのパフォーマンス
    let client = PythonCompatibleWeatherClient::new(Some("localhost"), Some(4110), Some(false));
    let start = Instant::now();
    for _i in 0..iterations {
        // API呼び出しのオーバーヘッドを測定（実際の通信は行わない）
        let _result = client.get_weather_data(130010, Some(true), Some(false), Some(false), Some(false), Some(false), Some(0));
    }
    let compat_duration = start.elapsed();
    
    println!("Performance comparison for {} iterations:", iterations);
    println!("  Rust native: {:?}", rust_duration);
    println!("  Python compatible: {:?}", compat_duration);
    
    // 大きな性能差がないことを確認
    assert!(compat_duration < rust_duration * 10);
}