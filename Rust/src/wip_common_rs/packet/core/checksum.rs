/// WIP パケットのチェックサム計算・検証機能
/// Python版 format_base.py の calc_checksum12, verify_checksum12 と同等

/// 12ビットチェックサムを計算する
/// 
/// Args:
///     data: チェックサム計算対象のバイト列
/// 
/// Returns:
///     12ビットチェックサム値
pub fn calc_checksum12(data: &[u8]) -> u16 {
    let mut total = 0u32;
    
    // 1バイトずつ加算
    for &byte in data {
        total += byte as u32;
    }
    
    // キャリーを12ビットに折り返し
    while total >> 12 != 0 {
        total = (total & 0xFFF) + (total >> 12);
    }
    
    // 1の補数を返す（12ビットマスク）
    let checksum = (!total) & 0xFFF;
    checksum as u16
}

/// 12ビットチェックサムを検証する（可変長パケット対応）
/// 
/// Args:
///     data_with_checksum: チェックサムを含むバイト列
///     checksum_start_bit: チェックサムの開始ビット位置
///     checksum_length: チェックサムの長さ（ビット）
/// 
/// Returns:
///     チェックサムが正しければtrue
pub fn verify_checksum12(
    data_with_checksum: &[u8], 
    checksum_start_bit: usize, 
    checksum_length: usize
) -> bool {
    use bitvec::prelude::*;
    
    if data_with_checksum.is_empty() || checksum_length != 12 {
        return false;
    }
    
    // パケットサイズがチェックサム位置を収容できるかチェック
    if data_with_checksum.len() * 8 < checksum_start_bit + checksum_length {
        return false;
    }
    
    // ビット操作でチェックサムを抽出
    let bits = BitSlice::<u8, bitvec::order::Lsb0>::from_slice(data_with_checksum);
    let stored_checksum = bits[checksum_start_bit..checksum_start_bit + checksum_length]
        .load::<u16>();
    
    // チェックサム部分を0にしたデータを作成
    let mut data_without_checksum = data_with_checksum.to_vec();
    let bits_mut = BitSlice::<u8, bitvec::order::Lsb0>::from_slice_mut(&mut data_without_checksum);
    bits_mut[checksum_start_bit..checksum_start_bit + checksum_length].store(0u16);
    
    // チェックサムを計算
    let calculated_checksum = calc_checksum12(&data_without_checksum);
    
    // 計算されたチェックサムと格納されたチェックサムを比較
    calculated_checksum == stored_checksum
}

/// 最適化されたチェックサム計算（ゼロコピー）
pub fn calc_checksum12_optimized(data: &[u8]) -> u16 {
    // SIMD最適化の余地あり
    let mut total = data.iter().map(|&b| b as u32).sum::<u32>();
    
    // キャリーフォールドをループ展開で最適化
    total = (total & 0xFFF) + (total >> 12);
    if total >> 12 != 0 {
        total = (total & 0xFFF) + (total >> 12);
    }
    
    (!total & 0xFFF) as u16
}

/// パケットの指定位置に12ビットチェックサムを埋め込む（可変長対応）
/// 
/// Args:
///     packet: チェックサムを埋め込むパケットデータ
///     checksum_start_bit: チェックサムの開始ビット位置
///     checksum_length: チェックサムの長さ（ビット、通常12）
pub fn embed_checksum12_at(packet: &mut [u8], checksum_start_bit: usize, checksum_length: usize) {
    use bitvec::prelude::*;
    
    if packet.is_empty() || checksum_length != 12 {
        return;
    }
    
    // チェックサム部分を0にしたコピーでチェックサムを計算
    let mut tmp = packet.to_vec();
    
    // ビット操作でチェックサム部分をゼロクリア
    if tmp.len() * 8 >= checksum_start_bit + checksum_length {
        let bits = BitSlice::<u8, bitvec::order::Lsb0>::from_slice_mut(&mut tmp);
        bits[checksum_start_bit..checksum_start_bit + checksum_length].store(0u16);
    }
    
    // チェックサムを計算
    let checksum = calc_checksum12(&tmp);
    
    // 元のパケットにチェックサムを埋め込み
    if packet.len() * 8 >= checksum_start_bit + checksum_length {
        let bits = BitSlice::<u8, bitvec::order::Lsb0>::from_slice_mut(packet);
        bits[checksum_start_bit..checksum_start_bit + checksum_length].store(checksum);
    }
}

/// ヘッダ（16バイト以上）に12ビットチェックサムを埋め込む（固定位置 116..128）
/// 後方互換性のため残存、内部的には embed_checksum12_at を使用
pub fn embed_checksum12_le(header: &mut [u8]) {
    // 固定位置116ビット（14.5バイト目）からの12ビット
    embed_checksum12_at(header, 116, 12);
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_calc_checksum12_basic() {
        let data = [0x01, 0x02, 0x03, 0x04];
        let checksum = calc_checksum12(&data);
        assert!(checksum <= 0xFFF); // 12ビット以内
    }

    #[test]
    fn test_calc_checksum12_empty() {
        let data = [];
        let checksum = calc_checksum12(&data);
        assert_eq!(checksum, 0xFFF); // すべてのビットが1（~0 & 0xFFF）
    }

    #[test]
    fn test_calc_checksum12_all_zeros() {
        let data = [0x00; 16];
        let checksum = calc_checksum12(&data);
        assert_eq!(checksum, 0xFFF); // ~0 & 0xFFF
    }

    #[test]
    fn test_calc_checksum12_carry_fold() {
        // 12ビットを超える値でキャリーフォールドをテスト
        let data = [0xFF; 16]; // 大きな値
        let checksum = calc_checksum12(&data);
        assert!(checksum <= 0xFFF);
    }

    #[test]
    fn test_embed_checksum12_at_variable_length() {
        // 20バイトのレスポンスパケットをテスト
        let mut packet_20 = vec![0x12, 0x34, 0x56, 0x78, 0x9A, 0xBC, 0xDE, 0xF0,
                                0x11, 0x22, 0x33, 0x44, 0x55, 0x66, 0x77, 0x88,
                                0x99, 0xAA, 0x00, 0x00]; // 最後2バイトにチェックサム
        
        // 最後12ビット（144-155ビット位置）にチェックサムを埋め込み
        embed_checksum12_at(&mut packet_20, 144, 12);
        
        // チェックサムが正しく埋め込まれているか検証
        assert!(verify_checksum12(&packet_20, 144, 12));
        
        // 40バイトの拡張パケットをテスト
        let mut packet_40 = vec![0u8; 40];
        packet_40[0] = 0xAB;
        packet_40[1] = 0xCD;
        packet_40[39] = 0xEF; // 最後のバイト
        
        // パケット末尾の12ビット（308-319ビット位置）にチェックサムを埋め込み
        embed_checksum12_at(&mut packet_40, 308, 12);
        
        // チェックサムが正しく埋め込まれているか検証
        assert!(verify_checksum12(&packet_40, 308, 12));
    }

    #[test]
    fn test_embed_checksum12_at_different_positions() {
        // 異なる位置でのチェックサム埋め込みをテスト
        let test_cases = vec![
            (16, 32),   // 4バイト目（32ビット位置）
            (24, 64),   // 8バイト目（64ビット位置）
            (32, 116),  // 14.5バイト目（116ビット位置、標準）
            (48, 372),  // 46.5バイト目（372ビット位置）
        ];
        
        for (packet_size, checksum_pos) in test_cases {
            let mut packet = vec![0u8; packet_size];
            
            // パケットにテストデータを設定
            for (i, byte) in packet.iter_mut().enumerate() {
                *byte = (i % 256) as u8;
            }
            
            // チェックサムを埋め込み
            embed_checksum12_at(&mut packet, checksum_pos, 12);
            
            // 検証
            assert!(verify_checksum12(&packet, checksum_pos, 12),
                   "Failed for packet size {} at position {}", packet_size, checksum_pos);
        }
    }

    #[test]
    fn test_embed_checksum12_le_compatibility() {
        // 既存の embed_checksum12_le が新しい実装と互換性があることを確認
        let mut header_old_style = vec![0x12, 0x34, 0x56, 0x78, 0x9A, 0xBC, 0xDE, 0xF0,
                                       0x11, 0x22, 0x33, 0x44, 0x55, 0x66, 0x00, 0x00];
        let mut header_new_style = header_old_style.clone();
        
        // 古いAPIでチェックサム埋め込み
        embed_checksum12_le(&mut header_old_style);
        
        // 新しいAPIで同じ位置にチェックサム埋め込み
        embed_checksum12_at(&mut header_new_style, 116, 12);
        
        // 結果が同じかチェック
        assert_eq!(header_old_style, header_new_style);
        
        // 両方とも検証できることを確認
        assert!(verify_checksum12(&header_old_style, 116, 12));
        assert!(verify_checksum12(&header_new_style, 116, 12));
    }

    #[test]
    fn test_verify_checksum12() {
        // テスト用データを作成（16バイト）
        let mut data = [0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08,
                        0x09, 0x0A, 0x0B, 0x0C, 0x0D, 0x0E, 0x00, 0x00];
        
        // 新しいAPIでチェックサムを埋め込み
        embed_checksum12_at(&mut data, 116, 12);
        
        // 検証
        assert!(verify_checksum12(&data, 116, 12));
        
        // データを破損させて検証失敗をテスト
        data[0] = 0xFF;
        assert!(!verify_checksum12(&data, 116, 12));
    }

    #[test]
    fn test_optimized_vs_standard() {
        let data = [0x12, 0x34, 0x56, 0x78, 0x9A, 0xBC, 0xDE, 0xF0];
        let standard = calc_checksum12(&data);
        let optimized = calc_checksum12_optimized(&data);
        assert_eq!(standard, optimized);
    }
}
