use std::sync::Mutex;
use std::sync::OnceLock;

/// 12ビットパケットIDを生成する
#[derive(Debug)]
pub struct PacketIDGenerator12Bit {
    current_id: u16,
}

impl PacketIDGenerator12Bit {
    /// 新しいパケットIDジェネレーターを作成
    pub fn new() -> Self {
        // テストの安定性のため、初期値は1で固定（12ビット範囲内を循環）
        Self { current_id: 1 }
    }

    /// 次のパケットIDを生成（12ビット範囲内で循環）
    pub fn next_id(&mut self) -> u16 {
        let id = self.current_id;
        self.current_id = (self.current_id + 1) & 0x0FFF; // 12ビットマスク
        if self.current_id == 0 {
            self.current_id = 1; // 0は避ける
        }
        id
    }
}

/// グローバルなPacketIdGeneratorのシングルトン実装
pub struct PacketIdGenerator;

impl PacketIdGenerator {
    /// 次のパケットIDを生成（スレッドセーフ）
    pub fn next_id() -> u16 {
        static GENERATOR: OnceLock<Mutex<PacketIDGenerator12Bit>> = OnceLock::new();
        
        let generator = GENERATOR.get_or_init(|| {
            Mutex::new(PacketIDGenerator12Bit::new())
        });
        
        let mut gen = generator.lock().unwrap();
        gen.next_id()
    }
}

impl Default for PacketIDGenerator12Bit {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn packet_id_generation() {
        let mut generator = PacketIDGenerator12Bit::new();
        
        let id1 = generator.next_id();
        let id2 = generator.next_id();
        
        assert_eq!(id1, 1);
        assert_eq!(id2, 2);
        assert_ne!(id1, id2);
    }

    #[test]
    fn packet_id_wraps_at_12_bits() {
        let mut generator = PacketIDGenerator12Bit::new();
        generator.current_id = 0xFFF; // 12ビット最大値
        
        let last_id = generator.next_id();
        let wrapped_id = generator.next_id();
        
        assert_eq!(last_id, 0xFFF);
        assert_eq!(wrapped_id, 1); // 0をスキップして1に戻る
    }
}
