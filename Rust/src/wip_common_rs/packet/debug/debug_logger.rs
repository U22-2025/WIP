use bitvec::prelude::*;
use crate::wip_common_rs::packet::core::checksum::verify_checksum12;
// Note: Imports currently unused but kept for future features

/// Minimal packet debug logger to mirror Python's packet inspection utilities.
/// - Pretty prints header fields and verifies checksum
/// - Dumps extended field area length
pub struct PacketDebugLogger;

impl PacketDebugLogger {
    pub fn log_request(buf: &[u8]) {
        if buf.len() < 16 {
            eprintln!("[PacketDebug] too short: {} bytes", buf.len());
            return;
        }
        let head = &buf[..16];
        let ok = verify_checksum12(head, 116, 12);
        let bits = BitSlice::<u8, Lsb0>::from_slice(head);
        let version: u8 = bits[0..4].load();
        let packet_id: u16 = bits[4..16].load();
        let ty: u8 = bits[16..19].load();
        let ex_flag: u8 = bits[24..25].load();
        let ts: u64 = bits[32..96].load();
        let area: u32 = bits[96..116].load();
        eprintln!(
            "[PacketDebug] req v={} id={} type={} ex={} ts={} area={} chk_ok={}",
            version, packet_id, ty, ex_flag, ts, area, ok
        );
        if buf.len() > 16 {
            eprintln!("[PacketDebug] ext_len={} bytes", buf.len() - 16);
        }
    }

    pub fn log_response(buf: &[u8]) {
        if buf.len() < 16 {
            eprintln!("[PacketDebug] too short: {} bytes", buf.len());
            return;
        }
        let head = &buf[..16];
        let ok = verify_checksum12(head, 116, 12);
        // Try 20-byte header for response tail fields as well
        let bits20 = if buf.len() >= 20 { Some(BitSlice::<u8, Lsb0>::from_slice(&buf[..20])) } else { None };
        let bits16 = BitSlice::<u8, Lsb0>::from_slice(head);
        let version: u8 = bits16[0..4].load();
        let packet_id: u16 = bits16[4..16].load();
        let ty: u8 = bits16[16..19].load();
        let area: u32 = bits16[96..116].load();
        eprintln!(
            "[PacketDebug] resp v={} id={} type={} area={} chk_ok={}",
            version, packet_id, ty, area, ok
        );
        if let Some(b20) = bits20 {
            let wc: u16 = b20[128..144].load();
            let temp_raw: u8 = b20[144..152].load();
            let pop: u8 = b20[152..160].load();
            eprintln!("[PacketDebug] tail wc={} temp_raw={} pop={}", wc, temp_raw, pop);
        }
        if buf.len() > 20 { eprintln!("[PacketDebug] ext_len={} bytes", buf.len() - 20); }
    }
}

