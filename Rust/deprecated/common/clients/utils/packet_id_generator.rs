use std::sync::Mutex;
use rand::Rng;

pub struct PacketIDGenerator12Bit {
    current: Mutex<u16>,
}

impl PacketIDGenerator12Bit {
    pub fn new() -> Self {
        let start = rand::thread_rng().gen_range(0..4096);
        Self { current: Mutex::new(start) }
    }

    pub fn next_id(&self) -> u16 {
        let mut c = self.current.lock().unwrap();
        let id = *c;
        *c = (*c + 1) % 4096;
        id
    }

    pub fn next_id_bytes(&self) -> [u8; 2] {
        self.next_id().to_le_bytes()
    }
}
