use wip_rust::wip_common_rs::packet::core::checksum::{
    calc_checksum12, verify_checksum12, embed_checksum12_at, embed_checksum12_le
};

#[test]
fn test_20_byte_response_packet() {
    // 20バイトのレスポンスパケット（Python WIPサーバーでよく使われる）
    let mut response_packet = vec![
        0x01, 0x23, 0x45, 0x67,  // ヘッダー前半
        0x89, 0xAB, 0xCD, 0xEF,  // ヘッダー後半
        0x11, 0x22, 0x33, 0x44,  // データ部分
        0x55, 0x66, 0x77, 0x88,  // 追加データ
        0x99, 0xAA, 0x00, 0x00   // 最後2バイトにチェックサム
    ];
    
    // 最後12ビット（144-155ビット位置）にチェックサムを埋め込み
    embed_checksum12_at(&mut response_packet, 144, 12);
    
    // チェックサムが正しく埋め込まれ、検証できることを確認
    assert!(verify_checksum12(&response_packet, 144, 12));
    
    // データ破損時の検証失敗をテスト
    let mut corrupted_packet = response_packet.clone();
    corrupted_packet[5] ^= 0xFF; // 5バイト目を破損
    assert!(!verify_checksum12(&corrupted_packet, 144, 12));
}

#[test]
fn test_disaster_info_packet_variable_length() {
    // 災害情報付加で可変長になるパケットをテスト
    let packet_sizes = vec![24, 32, 48, 64, 128];
    
    for size in packet_sizes {
        let mut packet = vec![0u8; size];
        
        // パケットにランダムテストデータを設定
        for (i, byte) in packet.iter_mut().enumerate() {
            *byte = ((i * 37 + 123) % 256) as u8; // 疑似ランダムデータ
        }
        
        // パケット末尾の12ビットにチェックサムを配置
        let checksum_pos = (size - 2) * 8; // 最後から2バイト目の開始ビット
        
        // チェックサム部分をクリア
        packet[size - 2] = 0;
        packet[size - 1] = 0;
        
        // チェックサムを埋め込み
        embed_checksum12_at(&mut packet, checksum_pos, 12);
        
        // 検証
        assert!(verify_checksum12(&packet, checksum_pos, 12),
               "Failed verification for {} byte packet at position {}", size, checksum_pos);
        
        // 破損テスト
        let mut corrupted = packet.clone();
        corrupted[0] ^= 0xFF;
        assert!(!verify_checksum12(&corrupted, checksum_pos, 12),
               "Corruption detection failed for {} byte packet", size);
    }
}

#[test]
fn test_large_extended_packet() {
    // 大きな拡張パケット（災害情報、気象データ、座標データ等を含む）
    let mut large_packet = vec![0u8; 256];
    
    // ヘッダー部分（最初16バイト）
    large_packet[0..16].copy_from_slice(&[
        0x02, 0x34, 0x56, 0x78, 0x9A, 0xBC, 0xDE, 0xF0,
        0x11, 0x22, 0x33, 0x44, 0x55, 0x66, 0x77, 0x88
    ]);
    
    // 災害情報部分（16-128バイト）
    for i in 16..128 {
        large_packet[i] = ((i * 7 + 42) % 256) as u8;
    }
    
    // 気象データ部分（128-240バイト）
    for i in 128..240 {
        large_packet[i] = ((i * 11 + 73) % 256) as u8;
    }
    
    // チェックサム部分をクリア（最後16バイト）
    for i in 240..256 {
        large_packet[i] = 0;
    }
    
    // 複数の位置でチェックサムをテスト
    let checksum_positions = vec![
        116,  // 標準位置（ヘッダー内）
        1936, // パケット末尾の12ビット（242バイト目）
        2032, // 254バイト目の開始位置
    ];
    
    for &pos in &checksum_positions {
        let mut test_packet = large_packet.clone();
        
        // チェックサムを埋め込み
        embed_checksum12_at(&mut test_packet, pos, 12);
        
        // 検証
        assert!(verify_checksum12(&test_packet, pos, 12),
               "Failed for large packet at position {}", pos);
    }
}

#[test]
fn test_multiple_checksum_positions() {
    // 複数のパケットで異なる位置のチェックサムをテスト（現実的なシナリオ）
    let positions = vec![
        (32, 12),   // 4バイト目の12ビット
        (128, 12),  // 16バイト目の12ビット
        (256, 12),  // 32バイト目の12ビット
        (372, 12),  // 46.5バイト目の12ビット
    ];
    
    // 各位置で独立したパケットでテスト
    for &(pos, len) in &positions {
        let mut packet = vec![0u8; 48];
        
        // テストデータを設定
        for (i, byte) in packet.iter_mut().enumerate() {
            *byte = (i % 256) as u8;
        }
        
        // この位置にチェックサムを埋め込み
        embed_checksum12_at(&mut packet, pos, len);
        
        // 検証
        assert!(verify_checksum12(&packet, pos, len),
               "Failed verification at position {}", pos);
    }
}

#[test]
fn test_backward_compatibility() {
    // 既存のembed_checksum12_leとの後方互換性をテスト
    let test_headers = vec![
        vec![0u8; 16],                                    // 最小サイズ
        vec![0x12, 0x34, 0x56, 0x78, 0x9A, 0xBC, 0xDE, 0xF0,
             0x11, 0x22, 0x33, 0x44, 0x55, 0x66, 0x00, 0x00], // 典型的なヘッダー
        vec![0u8; 32],                                    // 拡張ヘッダー
    ];
    
    for original_header in test_headers {
        let mut header_old = original_header.clone();
        let mut header_new = original_header.clone();
        
        // 古いAPIを使用
        embed_checksum12_le(&mut header_old);
        
        // 新しいAPIで同等の操作
        embed_checksum12_at(&mut header_new, 116, 12);
        
        // 結果が同じであることを確認
        assert_eq!(header_old, header_new, "Backward compatibility failed");
        
        // 両方とも正しく検証できることを確認
        assert!(verify_checksum12(&header_old, 116, 12));
        assert!(verify_checksum12(&header_new, 116, 12));
    }
}

#[test]
fn test_edge_cases() {
    // エッジケースのテスト
    
    // 最小サイズ（2バイト、16ビット）
    let mut min_packet = vec![0x12, 0x00];
    embed_checksum12_at(&mut min_packet, 4, 12);
    assert!(verify_checksum12(&min_packet, 4, 12));
    
    // チェックサムが境界を跨ぐ場合
    let mut boundary_packet = vec![0x12, 0x34, 0x56, 0x00, 0x00];
    embed_checksum12_at(&mut boundary_packet, 20, 12); // 2.5バイト目から12ビット
    assert!(verify_checksum12(&boundary_packet, 20, 12));
    
    // 無効な位置（パケットサイズを超える）
    let mut invalid_packet = vec![0x12, 0x34];
    embed_checksum12_at(&mut invalid_packet, 100, 12); // 範囲外
    // 関数は何もしないはず（パニックしない）
    
    // チェックサム長が12以外
    let mut invalid_length_packet = vec![0x12, 0x34, 0x56, 0x78];
    embed_checksum12_at(&mut invalid_length_packet, 0, 8); // 8ビット指定
    // 関数は何もしないはず
}

#[test]
fn test_performance_comparison() {
    // パフォーマンス比較テスト（大きなパケット）
    let mut large_packet = vec![0u8; 1024];
    for (i, byte) in large_packet.iter_mut().enumerate() {
        *byte = (i % 256) as u8;
    }
    
    // 複数回実行して安定性をテスト  
    // 1024バイト = 8192ビット、チェックサム12ビットなので最大位置は8180
    let checksum_pos = 8180; // 1022.5バイト目
    
    for _ in 0..100 {
        let mut test_packet = large_packet.clone();
        embed_checksum12_at(&mut test_packet, checksum_pos, 12);
        assert!(verify_checksum12(&test_packet, checksum_pos, 12),
               "Performance test failed at position {}", checksum_pos);
    }
}