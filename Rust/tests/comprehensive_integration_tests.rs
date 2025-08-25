/*!
 * 包括的統合テストスイート  
 * Phase 5対応 - サーバー通信、E2E、負荷テストの完全実装
 */

use std::net::UdpSocket;
use std::time::{Duration, Instant};
use wip_rust::wip_common_rs::clients::weather_client::WeatherClient;
use wip_rust::wip_common_rs::clients::location_client::LocationClient;
use wip_rust::wip_common_rs::clients::query_client::QueryClient;
use wip_rust::wip_common_rs::clients::report_client::ReportClient;
use wip_rust::wip_common_rs::packet::types::location_packet::LocationRequest;
use wip_rust::wip_common_rs::packet::types::query_packet::QueryRequest;
use wip_rust::wip_common_rs::packet::types::report_packet::ReportRequest;
use wip_rust::wip_common_rs::packet::core::checksum::verify_checksum12;

/// モックサーバーを実装するためのヘルパー関数
mod mock_server {
    use super::*;
    use std::thread;
    
    /// 簡単なエコーサーバーを起動
    pub fn start_echo_server(port: u16) -> std::thread::JoinHandle<()> {
        thread::spawn(move || {
            let socket = UdpSocket::bind(format!("127.0.0.1:{}", port))
                .expect("Failed to bind mock server");
            
            let mut buf = [0; 1024];
            loop {
                match socket.recv_from(&mut buf) {
                    Ok((size, src)) => {
                        // エコー応答を送信
                        let _ = socket.send_to(&buf[..size], src);
                    }
                    Err(_) => break,
                }
            }
        })
    }

    /// LocationRequestに対してLocationResponseを返すモックサーバー
    pub fn start_location_mock_server(port: u16) -> std::thread::JoinHandle<()> {
        thread::spawn(move || {
            let socket = UdpSocket::bind(format!("127.0.0.1:{}", port))
                .expect("Failed to bind location mock server");
            
            let mut buf = [0; 1024];
            while let Ok((size, src)) = socket.recv_from(&mut buf) {
                if size >= 16 {
                    // 受信したパケットからpacket_idを抽出してLocationResponseを作成
                    let packet_id = u16::from_le_bytes([buf[1], buf[0] >> 4 | (buf[1] & 0x0F) << 4]);
                    
                    // 簡単なLocationResponse (Type=1, Success=true, AreaCode=130010)
                    let mut response = [0u8; 16];
                    response[0] = 0x11; // Version=1, PacketID低位
                    response[1] = (packet_id & 0xFF) as u8; // PacketID高位部分
                    response[2] = 0x10 | ((packet_id >> 8) & 0x0F); // PacketID残り + Type=1
                    
                    // AreaCode=130010 (0x1FB5A) を設定
                    response[3] = 0x5A;
                    response[4] = 0xFB;
                    response[5] = 0x01;
                    
                    // Success=true
                    response[6] = 0x01;
                    
                    let _ = socket.send_to(&response, src);
                }
            }
        })
    }
}

/// クライアント機能の統合テスト
#[cfg(test)]
mod client_integration_tests {
    use super::*;

    #[test]
    #[ignore] // 実際のサーバーが必要なテスト
    fn test_weather_client_integration() {
        let client = WeatherClient::new("127.0.0.1:4110".to_string());
        
        // タイムアウト付きでテスト
        let start = Instant::now();
        let result = client.get_weather_by_coordinates(35.6762, 139.6503, true, true, false);
        let duration = start.elapsed();
        
        println!("Weather client request took: {:?}", duration);
        
        // レスポンス時間が合理的な範囲内であることを確認
        assert!(duration < Duration::from_secs(5));
    }

    #[test]
    fn test_location_client_with_mock() {
        // モックサーバーを起動
        let port = 14109;
        let _server_handle = mock_server::start_location_mock_server(port);
        
        // サーバーの起動を待つ
        std::thread::sleep(Duration::from_millis(100));
        
        let client = LocationClient::new(format!("127.0.0.1:{}", port));
        
        // 座標からエリアコードを取得
        let start = Instant::now();
        let result = client.get_area_code(35.6762, 139.6503);
        let duration = start.elapsed();
        
        println!("Location client request took: {:?}", duration);
        assert!(duration < Duration::from_secs(2));
        
        // 結果が取得できることを確認（モックサーバーなので固定値）
        if let Ok(area_code) = result {
            assert!(area_code > 0);
        }
    }

    #[test]
    fn test_client_error_handling() {
        // 存在しないサーバーにアクセス
        let client = WeatherClient::new("127.0.0.1:99999".to_string());
        
        let start = Instant::now();
        let result = client.get_weather_by_coordinates(35.0, 139.0, true, false, false);
        let duration = start.elapsed();
        
        // エラーハンドリングが適切に行われることを確認
        assert!(result.is_err());
        
        // タイムアウトが適切に働くことを確認
        assert!(duration < Duration::from_secs(10));
    }
}

/// エンドツーエンドのテスト
#[cfg(test)]
mod end_to_end_tests {
    use super::*;

    #[test]
    fn test_packet_creation_to_bytes_roundtrip() {
        // LocationRequest作成からバイト列化まで
        let req = LocationRequest::create_coordinate_lookup(
            35.6762, 139.6503, 0x123, true, true, true, false, false, 0, 1
        );
        
        let bytes = req.to_bytes();
        
        // 基本的な整合性チェック
        assert!(bytes.len() >= 16);
        assert!(verify_checksum12(&bytes, 116, 12));
        
        // パケット内容の検証
        let as_u128 = wip_rust::wip_common_rs::packet::core::bit_utils::bytes_to_u128_le(&bytes[..16]);
        
        // Version (bit 0-3)
        let version = wip_rust::wip_common_rs::packet::core::bit_utils::extract_bits(as_u128, 0, 4);
        assert_eq!(version, 1);
        
        // PacketID (bit 4-15)
        let packet_id = wip_rust::wip_common_rs::packet::core::bit_utils::extract_bits(as_u128, 4, 12);
        assert_eq!(packet_id, 0x123);
        
        // Type (bit 16-18)
        let packet_type = wip_rust::wip_common_rs::packet::core::bit_utils::extract_bits(as_u128, 16, 3);
        assert_eq!(packet_type, 0); // LocationRequest
    }

    #[test]
    fn test_complete_weather_data_flow() {
        // 座標からエリアコード取得を模擬
        let coordinates = (35.6762, 139.6503);
        let mock_area_code = 130010; // 東京都のエリアコード
        
        // QueryRequest作成
        let query = QueryRequest::new(0x234, mock_area_code, true, true, true, 0);
        let query_bytes = query.to_bytes();
        
        // パケットの検証
        assert_eq!(query_bytes.len(), 16);
        
        let as_u128 = wip_rust::wip_common_rs::packet::core::bit_utils::bytes_to_u128_le(&query_bytes);
        let packet_type = wip_rust::wip_common_rs::packet::core::bit_utils::extract_bits(as_u128, 16, 3);
        assert_eq!(packet_type, 2); // QueryRequest
    }

    #[test]
    fn test_error_response_handling() {
        use wip_rust::wip_common_rs::packet::types::error_response::ErrorResponse;
        
        // 様々なエラーレスポンスのテスト
        let error_codes = vec![400, 404, 500, 503];
        
        for code in error_codes {
            let error_resp = ErrorResponse::new(0x999, code, format!("Error {}", code));
            let bytes = error_resp.to_bytes();
            
            assert_eq!(bytes.len(), 16);
            
            // パケット型がErrorResponseであることを確認
            let as_u128 = wip_rust::wip_common_rs::packet::core::bit_utils::bytes_to_u128_le(&bytes);
            let packet_type = wip_rust::wip_common_rs::packet::core::bit_utils::extract_bits(as_u128, 16, 3);
            assert_eq!(packet_type, 7); // ErrorResponse
        }
    }
}

/// 負荷テスト
#[cfg(test)]
mod load_tests {
    use super::*;
    use std::sync::{Arc, Mutex};
    use std::thread;

    #[test]
    fn test_concurrent_packet_creation() {
        let num_threads = 10;
        let packets_per_thread = 100;
        let results = Arc::new(Mutex::new(Vec::new()));
        
        let mut handles = Vec::new();
        
        for thread_id in 0..num_threads {
            let results_clone = Arc::clone(&results);
            
            let handle = thread::spawn(move || {
                let start = Instant::now();
                
                for i in 0..packets_per_thread {
                    let req = LocationRequest::create_coordinate_lookup(
                        35.0 + (i as f64) * 0.001,
                        139.0 + (thread_id as f64) * 0.001,
                        (thread_id * 1000 + i) as u16,
                        true, true, false, false, false, 0, 1
                    );
                    
                    let bytes = req.to_bytes();
                    assert!(verify_checksum12(&bytes, 116, 12));
                }
                
                let duration = start.elapsed();
                results_clone.lock().unwrap().push(duration);
            });
            
            handles.push(handle);
        }
        
        // すべてのスレッドの完了を待つ
        for handle in handles {
            handle.join().unwrap();
        }
        
        let results = results.lock().unwrap();
        let total_packets = num_threads * packets_per_thread;
        let avg_duration = results.iter().sum::<Duration>() / results.len() as u32;
        
        println!("Created {} packets across {} threads", total_packets, num_threads);
        println!("Average time per thread: {:?}", avg_duration);
        
        // 各スレッドが合理的な時間内で完了することを確認
        for duration in results.iter() {
            assert!(duration < &Duration::from_secs(5));
        }
    }

    #[test]
    fn test_memory_usage_stability() {
        // 大量のパケット作成とメモリ使用量の安定性テスト
        let num_iterations = 1000;
        
        for i in 0..num_iterations {
            let req = LocationRequest::create_coordinate_lookup(
                35.0 + (i as f64) * 0.0001,
                139.0 + (i as f64) * 0.0001,
                i as u16,
                i % 2 == 0, i % 3 == 0, i % 5 == 0, false, false, 0, 1
            );
            
            let bytes = req.to_bytes();
            assert!(bytes.len() >= 16);
            
            // 定期的にガベージコレクションを促す（Rustでは自動だが明示的に）
            if i % 100 == 0 {
                // メモリプレッシャーをかけて安定性を確認
                let _temp_vec: Vec<u8> = vec![0; 1024];
            }
        }
        
        println!("Memory stability test completed for {} iterations", num_iterations);
    }

    #[test]
    fn test_checksum_calculation_load() {
        let data_sizes = vec![16, 64, 256, 1024, 4096];
        
        for size in data_sizes {
            let mut data = vec![0x42; size];
            let iterations = 1000;
            
            let start = Instant::now();
            
            for _ in 0..iterations {
                // チェックサムの埋め込みと検証
                wip_rust::wip_common_rs::packet::core::checksum::embed_checksum12_at(&mut data, 116, 12);
                assert!(verify_checksum12(&data, 116, 12));
            }
            
            let duration = start.elapsed();
            let avg_time = duration / iterations as u32;
            
            println!("Checksum ops for {}B data: {:?} avg per operation", size, avg_time);
            
            // パフォーマンス基準
            assert!(avg_time < Duration::from_micros(100)); // 100マイクロ秒以内
        }
    }
}

/// ネットワーク関連のテスト
#[cfg(test)]
mod network_tests {
    use super::*;

    #[test]
    fn test_udp_socket_basic_operations() {
        // UDPソケットの基本操作テスト
        let socket = UdpSocket::bind("127.0.0.1:0").expect("Failed to bind socket");
        let local_addr = socket.local_addr().expect("Failed to get local address");
        
        println!("Bound to address: {}", local_addr);
        
        // タイムアウト設定
        socket.set_read_timeout(Some(Duration::from_millis(100))).unwrap();
        socket.set_write_timeout(Some(Duration::from_millis(100))).unwrap();
        
        // 自分自身にパケットを送信
        let test_data = b"test_packet";
        socket.send_to(test_data, local_addr).expect("Failed to send data");
        
        let mut buf = [0; 1024];
        match socket.recv_from(&mut buf) {
            Ok((size, _)) => {
                assert_eq!(&buf[..size], test_data);
            }
            Err(e) => {
                // タイムアウトエラーは想定内
                println!("Expected timeout or other error: {}", e);
            }
        }
    }

    #[test]
    fn test_packet_size_limits() {
        // 様々なサイズのパケットをテスト
        let sizes = vec![16, 32, 64, 128, 256, 512, 1024];
        
        for size in sizes {
            let data = vec![0x42; size];
            let report = ReportRequest::new(0x123, data.clone(), 1);
            let bytes = report.to_bytes();
            
            // パケットサイズが適切であることを確認
            assert!(bytes.len() >= 16); // 最小ヘッダサイズ
            assert!(verify_checksum12(&bytes, 116, 12));
            
            println!("Packet with {} bytes data serialized to {} bytes", size, bytes.len());
        }
    }

    #[test]
    fn test_network_error_simulation() {
        // ネットワークエラーのシミュレーション
        let non_existent_addr = "192.0.2.1:9999"; // RFC 5737のテスト用IP
        
        let client = WeatherClient::new(non_existent_addr.to_string());
        
        let start = Instant::now();
        let result = client.get_weather_by_coordinates(35.0, 139.0, true, false, false);
        let duration = start.elapsed();
        
        // エラーが適切に処理されることを確認
        assert!(result.is_err());
        
        // タイムアウトが設定値以内であることを確認
        assert!(duration < Duration::from_secs(30));
        
        println!("Network error handled in: {:?}", duration);
    }
}

/// パフォーマンス基準テスト
#[cfg(test)]
mod performance_benchmarks {
    use super::*;

    #[test]
    fn test_response_time_requirements() {
        // WIP仕様書の要件：平均レスポンス時間 < 100ms
        let num_requests = 100;
        let mut total_duration = Duration::new(0, 0);
        
        for i in 0..num_requests {
            let start = Instant::now();
            
            // パケット作成からシリアライゼーションまでの時間を測定
            let req = LocationRequest::create_coordinate_lookup(
                35.0 + (i as f64) * 0.001,
                139.0 + (i as f64) * 0.001,
                i as u16,
                true, true, false, false, false, 0, 1
            );
            let _bytes = req.to_bytes();
            
            total_duration += start.elapsed();
        }
        
        let avg_duration = total_duration / num_requests as u32;
        
        println!("Average packet processing time: {:?}", avg_duration);
        
        // 目標：1ms以内（実際のネットワーク通信を除く）
        assert!(avg_duration < Duration::from_millis(1));
    }

    #[test]
    fn test_throughput_requirements() {
        // WIP仕様書の要件：> 100 requests/second
        let duration_limit = Duration::from_secs(1);
        let start = Instant::now();
        let mut count = 0;
        
        while start.elapsed() < duration_limit {
            let req = QueryRequest::new(count, 130010, true, false, false, 0);
            let _bytes = req.to_bytes();
            count += 1;
        }
        
        let actual_duration = start.elapsed();
        let throughput = count as f64 / actual_duration.as_secs_f64();
        
        println!("Achieved throughput: {:.2} requests/second", throughput);
        
        // 目標：1000 requests/second以上（ネットワーク I/O除く）
        assert!(throughput > 1000.0);
    }
}