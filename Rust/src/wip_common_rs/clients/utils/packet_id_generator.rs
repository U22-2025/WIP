use rand::Rng;
use std::sync::{Mutex, OnceLock};

/// 12ビットパケットIDを生成する
#[derive(Debug)]
pub struct PacketIDGenerator12Bit {
    current_id: u16,
}

impl PacketIDGenerator12Bit {
    /// 新しいパケットIDジェネレーターを作成
    pub fn new() -> Self {
        let current_id = rand::thread_rng().gen_range(0..=0x0FFF);
        Self { current_id }
    }

    /// 次のパケットIDを生成（12ビット範囲内で循環）
    pub fn next_id(&mut self) -> u16 {
        let id = self.current_id;
        self.current_id = (self.current_id + 1) & 0x0FFF; // 12ビットマスク
        id
    }
}

/// グローバルなPacketIdGeneratorのシングルトン実装
pub struct PacketIdGenerator;

impl PacketIdGenerator {
    /// 次のパケットIDを生成（スレッドセーフ）
    pub fn next_id() -> u16 {
        static GENERATOR: OnceLock<Mutex<PacketIDGenerator12Bit>> = OnceLock::new();

        let generator = GENERATOR.get_or_init(|| Mutex::new(PacketIDGenerator12Bit::new()));

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
        use std::collections::HashSet;

        let mut generator = PacketIDGenerator12Bit::new();

        let first_id = generator.next_id();
        assert!(first_id <= 0x0FFF);

        let mut ids = HashSet::new();
        ids.insert(first_id);

        for _ in 0..0x0FFF {
            let id = generator.next_id();
            assert!(id <= 0x0FFF);
            assert!(ids.insert(id), "duplicate id {id}");
        }

        assert_eq!(ids.len(), 0x1000);

        let wrapped_id = generator.next_id();
        assert_eq!(wrapped_id, first_id);
    }

    #[test]
    fn packet_id_wraps_at_12_bits() {
        let mut generator = PacketIDGenerator12Bit::new();
        generator.current_id = 0xFFF; // 12ビット最大値

        let last_id = generator.next_id();
        let wrapped_id = generator.next_id();

        assert_eq!(last_id, 0xFFF);
        assert_eq!(wrapped_id, 0); // 0へラップする
    }
}
