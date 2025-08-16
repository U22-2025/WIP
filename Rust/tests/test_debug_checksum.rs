use wip_rust::wip_common_rs::packet::core::checksum::{
    calc_checksum12, verify_checksum12, embed_checksum12_at, embed_checksum12_le
};

#[test]
fn test_debug_basic_checksum() {
    // 基本的なチェックサム計算をテスト
    let data = vec![0x12, 0x34, 0x56, 0x78];
    let checksum = calc_checksum12(&data);
    println!("Basic checksum: 0x{:03X}", checksum);
    
    // 手動でチェックサムを埋め込んでテスト
    let mut packet = vec![0x12, 0x34, 0x56, 0x78, 0x00, 0x00];
    
    // 最後2バイト（32ビット位置）にチェックサムを埋め込み
    embed_checksum12_at(&mut packet, 32, 12);
    
    println!("Packet after embed: {:02X?}", packet);
    
    // 検証
    let is_valid = verify_checksum12(&packet, 32, 12);
    println!("Verification result: {}", is_valid);
    
    assert!(is_valid, "Basic checksum verification failed");
}

#[test]
fn test_debug_116_position() {
    // 16バイトパケットの116ビット位置テスト
    let mut header = vec![0x12, 0x34, 0x56, 0x78, 0x9A, 0xBC, 0xDE, 0xF0,
                         0x11, 0x22, 0x33, 0x44, 0x55, 0x66, 0x00, 0x00];
    
    println!("Original header: {:02X?}", header);
    
    // 新しいAPIで116ビット位置にチェックサムを埋め込み
    embed_checksum12_at(&mut header, 116, 12);
    
    println!("Header after embed_checksum12_at: {:02X?}", header);
    
    // 検証
    let is_valid = verify_checksum12(&header, 116, 12);
    println!("Verification result: {}", is_valid);
    
    assert!(is_valid, "116-bit position checksum verification failed");
    
    // 古いAPIと比較
    let mut header_old = vec![0x12, 0x34, 0x56, 0x78, 0x9A, 0xBC, 0xDE, 0xF0,
                             0x11, 0x22, 0x33, 0x44, 0x55, 0x66, 0x00, 0x00];
    
    embed_checksum12_le(&mut header_old);
    
    println!("Header after embed_checksum12_le: {:02X?}", header_old);
    
    // 両方とも同じ結果になるはず
    assert_eq!(header, header_old, "Old and new API should produce same result");
}

#[test]
fn test_debug_bit_extraction() {
    use bitvec::prelude::*;
    
    // ビット操作の確認
    let data = vec![0x12, 0x34, 0x56, 0x78];
    let bits = BitSlice::<u8, bitvec::order::Lsb0>::from_slice(&data);
    
    // 各ビット位置での値を確認
    println!("Data: {:02X?}", data);
    println!("Bits 0-7: 0x{:02X}", bits[0..8].load::<u8>());
    println!("Bits 8-15: 0x{:02X}", bits[8..16].load::<u8>());
    println!("Bits 16-23: 0x{:02X}", bits[16..24].load::<u8>());
    println!("Bits 24-31: 0x{:02X}", bits[24..32].load::<u8>());
    
    // 特定の12ビットを抽出
    if data.len() * 8 >= 20 {
        let twelve_bits = bits[8..20].load::<u16>();
        println!("Bits 8-19 (12 bits): 0x{:03X}", twelve_bits);
    }
}

#[test]
fn test_debug_manual_verification() {
    // 手動でチェックサムを検証してみる
    let mut packet = vec![0x12, 0x34, 0x00, 0x00]; // 最後2バイトにチェックサム
    
    // チェックサムを計算して手動で埋め込み
    let data_for_checksum = vec![0x12, 0x34, 0x00, 0x00]; // チェックサム部分は0
    let checksum = calc_checksum12(&data_for_checksum);
    
    println!("Calculated checksum: 0x{:03X}", checksum);
    
    // 16ビット位置（2バイト目）に12ビットのチェックサムを埋め込み
    use bitvec::prelude::*;
    let bits = BitSlice::<u8, bitvec::order::Lsb0>::from_slice_mut(&mut packet);
    bits[16..28].store(checksum);
    
    println!("Packet after manual embed: {:02X?}", packet);
    
    // 検証
    let is_valid = verify_checksum12(&packet, 16, 12);
    println!("Manual verification result: {}", is_valid);
    
    assert!(is_valid, "Manual checksum verification failed");
}