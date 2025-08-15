/// ビット操作ユーティリティ
/// Python版 format_base.py の extract_bits 関数等と同等

/// 指定されたビット範囲から値を抽出する
/// 
/// Args:
///     data: 元データ（整数値）
///     start_bit: 開始ビット位置（LSB基準）
///     length: 抽出するビット長
/// 
/// Returns:
///     抽出された値
pub fn extract_bits(data: u128, start_bit: usize, length: usize) -> u128 {
    if length == 0 || length > 128 {
        return 0;
    }
    
    // 範囲チェック: start_bit + length が128を超えてはいけない
    if start_bit >= 128 || start_bit + length > 128 {
        return 0;
    }
    
    let mask = if length >= 128 {
        u128::MAX
    } else {
        (1u128 << length) - 1
    };
    
    (data >> start_bit) & mask
}

/// 指定されたビット範囲に値を設定する
/// 
/// Args:
///     data: 対象データ（可変参照）
///     start_bit: 開始ビット位置（LSB基準）
///     length: 設定するビット長
///     value: 設定する値
pub fn set_bits(data: &mut u128, start_bit: usize, length: usize, value: u128) {
    if length == 0 || length > 128 {
        return;
    }
    
    // 範囲チェック: start_bit + length が128を超えてはいけない
    if start_bit >= 128 || start_bit + length > 128 {
        return;
    }
    
    let mask = if length >= 128 {
        u128::MAX
    } else {
        (1u128 << length) - 1
    };
    
    // 既存ビットをクリア
    *data &= !(mask << start_bit);
    
    // 新しい値を設定
    *data |= (value & mask) << start_bit;
}

/// バイト配列からリトルエンディアンで128ビット整数を構築
/// 
/// Args:
///     bytes: バイト配列
/// 
/// Returns:
///     128ビット整数値
pub fn bytes_to_u128_le(bytes: &[u8]) -> u128 {
    let mut result = 0u128;
    
    for (i, &byte) in bytes.iter().enumerate().take(16) {
        result |= (byte as u128) << (i * 8);
    }
    
    result
}

/// 128ビット整数をリトルエンディアンでバイト配列に変換
/// 
/// Args:
///     value: 128ビット整数
///     output: 出力バイト配列
pub fn u128_to_bytes_le(value: u128, output: &mut [u8]) {
    for (i, byte) in output.iter_mut().enumerate().take(16) {
        *byte = ((value >> (i * 8)) & 0xFF) as u8;
    }
}

/// ビットフィールドの定義構造体
#[derive(Debug, Clone, PartialEq)]
pub struct BitField {
    pub start: usize,
    pub length: usize,
    pub name: String,
}

impl BitField {
    /// 新しいビットフィールドを作成
    pub fn new(name: &str, start: usize, length: usize) -> Self {
        Self {
            start,
            length,
            name: name.to_string(),
        }
    }
    
    /// このフィールドから値を抽出
    pub fn extract(&self, data: u128) -> u128 {
        extract_bits(data, self.start, self.length)
    }
    
    /// このフィールドに値を設定
    pub fn set(&self, data: &mut u128, value: u128) {
        set_bits(data, self.start, self.length, value);
    }
    
    /// このフィールドの終了位置を計算
    pub fn end(&self) -> usize {
        self.start + self.length
    }
}

/// パケットフィールドマネージャー
#[derive(Debug, Clone)]
pub struct PacketFields {
    fields: Vec<BitField>,
    total_bits: usize,
}

impl PacketFields {
    /// 新しいフィールドマネージャーを作成
    pub fn new() -> Self {
        Self {
            fields: Vec::new(),
            total_bits: 0,
        }
    }
    
    /// フィールドを追加
    pub fn add_field(&mut self, name: &str, length: usize) {
        let field = BitField::new(name, self.total_bits, length);
        self.total_bits = field.end();
        self.fields.push(field);
    }
    
    /// フィールドを名前で検索
    pub fn get_field(&self, name: &str) -> Option<&BitField> {
        self.fields.iter().find(|f| f.name == name)
    }
    
    /// 全フィールドを取得
    pub fn get_all_fields(&self) -> &[BitField] {
        &self.fields
    }
    
    /// 合計ビット数を取得
    pub fn total_bits(&self) -> usize {
        self.total_bits
    }
    
    /// バイト数を計算
    pub fn total_bytes(&self) -> usize {
        (self.total_bits + 7) / 8
    }
}

impl Default for PacketFields {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_extract_bits() {
        let data = 0b11010110u128; // 214 in binary
        
        // 下位4ビットを抽出 (0110 = 6)
        assert_eq!(extract_bits(data, 0, 4), 6);
        
        // 2-5ビット目を抽出 (LSB基準で0101 = 5)
        assert_eq!(extract_bits(data, 2, 4), 5);
        
        // 上位4ビットを抽出 (1101 = 13)
        assert_eq!(extract_bits(data, 4, 4), 13);
    }

    #[test]
    fn test_set_bits() {
        let mut data = 0u128;
        
        // 下位4ビットに5を設定
        set_bits(&mut data, 0, 4, 5);
        assert_eq!(data, 5);
        
        // 4-7ビット目に10を設定
        set_bits(&mut data, 4, 4, 10);
        assert_eq!(data, 0b10100101); // 165
        
        // 既存ビットを上書き
        set_bits(&mut data, 0, 4, 15);
        assert_eq!(data, 0b10101111); // 175
    }

    #[test]
    fn test_bytes_to_u128_le() {
        let bytes = [0x01, 0x02, 0x03, 0x04];
        let result = bytes_to_u128_le(&bytes);
        // リトルエンディアン: 0x04030201
        assert_eq!(result, 0x04030201u128);
    }

    #[test]
    fn test_u128_to_bytes_le() {
        let value = 0x04030201u128;
        let mut bytes = [0u8; 4];
        u128_to_bytes_le(value, &mut bytes);
        assert_eq!(bytes, [0x01, 0x02, 0x03, 0x04]);
    }

    #[test]
    fn test_bit_field() {
        let field = BitField::new("test", 4, 8);
        assert_eq!(field.start, 4);
        assert_eq!(field.length, 8);
        assert_eq!(field.end(), 12);
        
        let data = 0xFF0u128; // 11111111 0000
        assert_eq!(field.extract(data), 0xFF);
        
        let mut data = 0u128;
        field.set(&mut data, 0xAB);
        assert_eq!(data, 0xAB0u128);
    }

    #[test]
    fn test_packet_fields() {
        let mut fields = PacketFields::new();
        fields.add_field("version", 4);
        fields.add_field("packet_id", 12);
        fields.add_field("type", 3);
        
        assert_eq!(fields.total_bits(), 19);
        assert_eq!(fields.total_bytes(), 3); // (19 + 7) / 8 = 3
        
        let version_field = fields.get_field("version").unwrap();
        assert_eq!(version_field.start, 0);
        assert_eq!(version_field.length, 4);
        
        let packet_id_field = fields.get_field("packet_id").unwrap();
        assert_eq!(packet_id_field.start, 4);
        assert_eq!(packet_id_field.length, 12);
    }

    #[test]
    fn test_edge_cases() {
        // 空のビット抽出
        assert_eq!(extract_bits(0xFF, 0, 0), 0);
        
        // 範囲外ビット抽出
        assert_eq!(extract_bits(0xFF, 10, 4), 0);
        
        // 最大値のテスト
        let max_val = u128::MAX;
        assert_eq!(extract_bits(max_val, 0, 64), u64::MAX as u128);
    }
}
