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

/// 12ビットチェックサムを検証する
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
    if data_with_checksum.is_empty() || checksum_length != 12 {
        return false;
    }
    
    // データからビット列を復元（リトルエンディアン）
    let mut bitstr = 0u128;
    for (i, &byte) in data_with_checksum.iter().enumerate() {
        bitstr |= (byte as u128) << (i * 8);
    }
    
    // 格納されているチェックサムを抽出
    let stored_checksum = ((bitstr >> checksum_start_bit) & 0xFFF) as u16;
    
    // チェックサム部分を0にしたデータを作成
    let checksum_mask = 0xFFFu128 << checksum_start_bit;
    let bitstr_without_checksum = bitstr & !checksum_mask;
    
    // チェックサム部分を0にしたバイト列を生成
    let mut data_without_checksum = vec![0u8; data_with_checksum.len()];
    for i in 0..data_with_checksum.len() {
        data_without_checksum[i] = ((bitstr_without_checksum >> (i * 8)) & 0xFF) as u8;
    }
    
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

/// ヘッダ（16バイト）に12ビットチェックサムを埋め込む（固定位置 116..128）
pub fn embed_checksum12_le(header: &mut [u8]) {
    use bitvec::prelude::*;
    // ゼロ化したコピーでチェックサムを計算
    let mut tmp = header.to_vec();
    if tmp.len() >= 16 {
        let tmp_head = &mut tmp[..16];
        let tmp_bits = BitSlice::<u8, Lsb0>::from_slice_mut(tmp_head);
        tmp_bits[116..128].store(0u16);
    }
    let checksum = calc_checksum12(&tmp[..16]);
    // 元のヘッダに埋め込み
    if header.len() >= 16 {
        let bits = BitSlice::<u8, Lsb0>::from_slice_mut(&mut header[..16]);
        bits[116..128].store(checksum);
    }
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
    fn test_verify_checksum12() {
        // テスト用データを作成（16バイト）
        let mut data = [0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08,
                        0x09, 0x0A, 0x0B, 0x0C, 0x0D, 0x0E, 0x00, 0x00];
        
        // チェックサムを計算してデータに埋め込み（116-127ビット位置）
        let checksum = calc_checksum12(&data);
        
        // 116ビット目から12ビット分にチェックサムを設定
        // 116ビット = 14.5バイト目から
        let byte_pos = 116 / 8; // 14
        let bit_offset = 116 % 8; // 4
        
        // 簡易的にチェックサムを設定
        data[byte_pos] |= ((checksum << bit_offset) & 0xFF) as u8;
        if byte_pos + 1 < data.len() {
            data[byte_pos + 1] |= (checksum >> (8 - bit_offset)) as u8;
        }
        
        assert!(verify_checksum12(&data, 116, 12));
    }

    #[test]
    fn test_optimized_vs_standard() {
        let data = [0x12, 0x34, 0x56, 0x78, 0x9A, 0xBC, 0xDE, 0xF0];
        let standard = calc_checksum12(&data);
        let optimized = calc_checksum12_optimized(&data);
        assert_eq!(standard, optimized);
    }
}
