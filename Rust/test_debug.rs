use crate::wip_common_rs::packet::core::checksum::{embed_checksum12_at, verify_checksum12};

fn main() {
    let mut packet_20 = vec![0x12, 0x34, 0x56, 0x78, 0x9A, 0xBC, 0xDE, 0xF0,
                            0x11, 0x22, 0x33, 0x44, 0x55, 0x66, 0x77, 0x88,
                            0x99, 0xAA, 0x00, 0x00]; // 最後2バイトにチェックサム
    
    println!("Before embed: {:02X?}", packet_20);
    embed_checksum12_at(&mut packet_20, 144, 12);
    println!("After embed: {:02X?}", packet_20);
    
    let result = verify_checksum12(&packet_20, 144, 12);
    println!("Verification result: {}", result);
}
