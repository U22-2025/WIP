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
    calc_checksum12_with_debug(data, false)
}

/// 12ビットチェックサムを計算する（デバッグ機能付き）
/// 
/// Args:
///     data: チェックサム計算対象のバイト列
///     debug: デバッグログを出力するかどうか
/// 
/// Returns:
///     12ビットチェックサム値
pub fn calc_checksum12_with_debug(data: &[u8], debug: bool) -> u16 {
    if debug {
        eprintln!("[DEBUG] チェックサム計算開始: データ長={} bytes", data.len());
        eprintln!("[DEBUG] データ: {:02X?}", data);
    }
    
    let mut total = 0u32;
    
    // 1バイトずつ加算
    for (i, &byte) in data.iter().enumerate() {
        total += byte as u32;
        if debug && i < 20 {
            eprintln!("[DEBUG] byte[{}] = 0x{:02X}, total = 0x{:X}", i, byte, total);
        }
    }
    
    if debug {
        eprintln!("[DEBUG] 加算完了: total = 0x{:X}", total);
    }
    
    // キャリーを12ビットに折り返し
    let mut fold_count = 0;
    while total >> 12 != 0 {
        let new_total = (total & 0xFFF) + (total >> 12);
        if debug {
            eprintln!("[DEBUG] キャリーフォールド#{}: 0x{:X} -> 0x{:X}", fold_count, total, new_total);
        }
        total = new_total;
        fold_count += 1;
        if fold_count > 10 { // 無限ループ防止
            break;
        }
    }
    
    // 1の補数を返す（12ビットマスク）
    let checksum = (!total) & 0xFFF;
    
    if debug {
        eprintln!("[DEBUG] 最終チェックサム: ~0x{:X} & 0xFFF = 0x{:03X}", total, checksum);
    }
    
    checksum as u16
}

/// 12ビットチェックサムを検証する（可変長パケット対応）
/// Python版format_base.pyのverify_checksum12()と同等の処理
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
    
    // パケットサイズがチェックサム位置を収容できるかチェック
    if data_with_checksum.len() * 8 < checksum_start_bit + checksum_length {
        return false;
    }
    
    // 格納されているチェックサムを抽出
    let stored_checksum = {
        let byte_start = checksum_start_bit / 8;
        let bit_start_in_byte = checksum_start_bit % 8;
        let mut checksum = 0u16;
        let mut bits_to_read = checksum_length;
        let mut byte_idx = byte_start;
        let mut bit_offset = bit_start_in_byte;
        let mut result_shift = 0;
        
        while bits_to_read > 0 && byte_idx < data_with_checksum.len() {
            let bits_in_this_byte = (8 - bit_offset).min(bits_to_read);
            // オーバーフロー防止
            let bits_in_this_byte = bits_in_this_byte.min(8);
            
            if bits_in_this_byte > 0 {
                let mask = if bits_in_this_byte < 8 {
                    ((1u8 << bits_in_this_byte) - 1) << bit_offset
                } else {
                    0xFF
                };
                let value_bits = (data_with_checksum[byte_idx] & mask) >> bit_offset;
                
                if result_shift < 16 {
                    checksum |= (value_bits as u16) << result_shift;
                }
                
                result_shift += bits_in_this_byte;
            }
            
            bits_to_read -= bits_in_this_byte;
            byte_idx += 1;
            bit_offset = 0;
        }
        
        checksum
    };
    
    // チェックサム部分を0にしたデータを作成
    let mut data_without_checksum = data_with_checksum.to_vec();
    
    // ビットレベルでチェックサム部分を0にする
    let byte_start = checksum_start_bit / 8;
    let bit_start_in_byte = checksum_start_bit % 8;
    let mut bits_to_clear = checksum_length;
    let mut byte_idx = byte_start;
    let mut bit_offset = bit_start_in_byte;
    
    while bits_to_clear > 0 && byte_idx < data_without_checksum.len() {
        let bits_in_this_byte = (8 - bit_offset).min(bits_to_clear);
        // オーバーフロー防止
        let bits_in_this_byte = bits_in_this_byte.min(8);
        
        if bits_in_this_byte > 0 {
            if bits_in_this_byte < 8 {
                let mask = ((1u8 << bits_in_this_byte) - 1) << bit_offset;
                data_without_checksum[byte_idx] &= !mask;
            } else if bits_in_this_byte == 8 && bit_offset == 0 {
                // 1バイト全体をクリア
                data_without_checksum[byte_idx] = 0;
            }
        }
        
        bits_to_clear -= bits_in_this_byte;
        byte_idx += 1;
        bit_offset = 0;
    }
    
    // Python版と同様: パケットの最小サイズ（16バイト）まで0パディング
    let min_packet_size = 16; // ヘッダの最小サイズ
    if data_without_checksum.len() < min_packet_size {
        data_without_checksum.resize(min_packet_size, 0);
    }
    
    // チェックサムを計算（デバッグモードで詳細出力）
    let calculated_checksum = if std::env::var("WIP_DEBUG_CHECKSUM").is_ok() {
        eprintln!("[DEBUG] verify_checksum12: パケット長={}, チェックサム位置={}-{}", 
                 data_with_checksum.len(), checksum_start_bit, checksum_start_bit + checksum_length - 1);
        eprintln!("[DEBUG] 格納チェックサム: 0x{:03X}", stored_checksum);
        let calc = calc_checksum12_with_debug(&data_without_checksum, true);
        eprintln!("[DEBUG] 計算チェックサム: 0x{:03X}", calc);
        calc
    } else {
        calc_checksum12(&data_without_checksum)
    };
    
    // 計算されたチェックサムと格納されたチェックサムを比較
    let result = calculated_checksum == stored_checksum;
    
    if std::env::var("WIP_DEBUG_CHECKSUM").is_ok() {
        eprintln!("[DEBUG] チェックサム検証結果: {} (計算:0x{:03X} vs 格納:0x{:03X})", 
                 if result { "OK" } else { "NG" }, calculated_checksum, stored_checksum);
    }
    
    result
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
/// Python版format_base.pyのto_bytes()と同等の処理
/// 
/// Args:
///     packet: チェックサムを埋め込むパケットデータ
///     checksum_start_bit: チェックサムの開始ビット位置
///     checksum_length: チェックサムの長さ（ビット、通常12）
pub fn embed_checksum12_at(packet: &mut [u8], checksum_start_bit: usize, checksum_length: usize) {
    if packet.is_empty() || checksum_length != 12 {
        return;
    }
    
    // パケットサイズがチェックサム位置を収容できるかチェック
    if packet.len() * 8 < checksum_start_bit + checksum_length {
        return;
    }
    
    // Python版と同様の処理: チェックサム部分を0にしてから計算
    // 1. チェックサム部分を0に設定
    let mut data_for_checksum = packet.to_vec();
    
    // ビットレベルでチェックサム部分を0にする
    let byte_start = checksum_start_bit / 8;
    let bit_start_in_byte = checksum_start_bit % 8;
    let remaining_bits = checksum_length;
    
    // チェックサム部分のビットをクリア
    let mut bits_to_clear = remaining_bits;
    let mut byte_idx = byte_start;
    let mut bit_offset = bit_start_in_byte;
    
    while bits_to_clear > 0 && byte_idx < data_for_checksum.len() {
        let bits_in_this_byte = (8 - bit_offset).min(bits_to_clear);
        // オーバーフロー防止: bits_in_this_byteが8を超えないことを保証
        let bits_in_this_byte = bits_in_this_byte.min(8);
        if bits_in_this_byte > 0 && bits_in_this_byte < 8 {
            let mask = ((1u8 << bits_in_this_byte) - 1) << bit_offset;
            data_for_checksum[byte_idx] &= !mask;
        } else if bits_in_this_byte == 8 && bit_offset == 0 {
            // 1バイト全体をクリア
            data_for_checksum[byte_idx] = 0;
        }
        
        bits_to_clear -= bits_in_this_byte;
        byte_idx += 1;
        bit_offset = 0;
    }
    
    // Python版と同様: パケットの最小サイズ（16バイト）まで0パディング
    let min_packet_size = 16; // ヘッダの最小サイズ
    if data_for_checksum.len() < min_packet_size {
        data_for_checksum.resize(min_packet_size, 0);
    }
    
    // チェックサムを計算（デバッグモードで詳細出力）
    let checksum = if std::env::var("WIP_DEBUG_CHECKSUM").is_ok() {
        eprintln!("[DEBUG] embed_checksum12_at: パケット長={}, チェックサム位置={}-{}", 
                 packet.len(), checksum_start_bit, checksum_start_bit + checksum_length - 1);
        calc_checksum12_with_debug(&data_for_checksum, true)
    } else {
        calc_checksum12(&data_for_checksum)
    };
    
    // 計算されたチェックサムを元のパケットに埋め込み
    let mut bits_to_set = checksum_length;
    let mut checksum_value = checksum;
    byte_idx = byte_start;
    bit_offset = bit_start_in_byte;
    
    while bits_to_set > 0 && byte_idx < packet.len() {
        let bits_in_this_byte = (8 - bit_offset).min(bits_to_set);
        // オーバーフロー防止: bits_in_this_byteが適切な範囲内であることを保証
        let bits_in_this_byte = bits_in_this_byte.min(8);
        
        if bits_in_this_byte > 0 {
            let mask = if bits_in_this_byte >= 16 {
                0xFFFF
            } else {
                (1u16 << bits_in_this_byte) - 1
            };
            let value_bits = (checksum_value & mask) as u8;
            
            // 既存のビットをクリアしてから新しい値を設定
            if bits_in_this_byte < 8 {
                let clear_mask = ((1u8 << bits_in_this_byte) - 1) << bit_offset;
                packet[byte_idx] &= !clear_mask;
                packet[byte_idx] |= value_bits << bit_offset;
            } else if bits_in_this_byte == 8 && bit_offset == 0 {
                // 1バイト全体を設定
                packet[byte_idx] = value_bits;
            }
            
            checksum_value >>= bits_in_this_byte;
        }
        
        bits_to_set -= bits_in_this_byte;
        byte_idx += 1;
        bit_offset = 0;
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
