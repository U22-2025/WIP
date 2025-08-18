// パケット生成テスト用の簡単なスクリプト
use std::collections::HashMap;

#[derive(Debug)]
struct Field {
    start: usize,
    length: usize,
}

fn extract_bits(data: u128, start_bit: usize, length: usize) -> u128 {
    if length == 0 || length > 128 {
        return 0;
    }
    
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

fn set_bits(data: &mut u128, start_bit: usize, length: usize, value: u128) {
    if length == 0 || length > 128 {
        return;
    }
    
    if start_bit >= 128 || start_bit + length > 128 {
        return;
    }
    
    let mask = if length >= 128 {
        u128::MAX
    } else {
        (1u128 << length) - 1
    };
    
    *data &= !(mask << start_bit);
    *data |= (value & mask) << start_bit;
}

fn u128_to_bytes_le(value: u128, output: &mut [u8]) {
    for (i, byte) in output.iter_mut().enumerate().take(16) {
        *byte = ((value >> (i * 8)) & 0xFF) as u8;
    }
}

fn main() {
    // フィールド定義（JSON順序ではなく、実際のビット位置）
    let mut fields = HashMap::new();
    let mut bit_pos = 0;
    
    // version: 4ビット (bit 0-3)
    fields.insert("version", Field { start: bit_pos, length: 4 });
    bit_pos += 4;
    
    // packet_id: 12ビット (bit 4-15)
    fields.insert("packet_id", Field { start: bit_pos, length: 12 });
    bit_pos += 12;
    
    // type: 3ビット (bit 16-18)
    fields.insert("type", Field { start: bit_pos, length: 3 });
    bit_pos += 3;
    
    // flags: 8ビット (bit 19-26)
    fields.insert("weather_flag", Field { start: bit_pos, length: 1 });
    bit_pos += 1;
    fields.insert("temperature_flag", Field { start: bit_pos, length: 1 });
    bit_pos += 1;
    fields.insert("pop_flag", Field { start: bit_pos, length: 1 });
    bit_pos += 1;
    fields.insert("alert_flag", Field { start: bit_pos, length: 1 });
    bit_pos += 1;
    fields.insert("disaster_flag", Field { start: bit_pos, length: 1 });
    bit_pos += 1;
    fields.insert("ex_flag", Field { start: bit_pos, length: 1 });
    bit_pos += 1;
    fields.insert("request_auth", Field { start: bit_pos, length: 1 });
    bit_pos += 1;
    fields.insert("response_auth", Field { start: bit_pos, length: 1 });
    bit_pos += 1;
    
    // day: 3ビット (bit 27-29)
    fields.insert("day", Field { start: bit_pos, length: 3 });
    bit_pos += 3;
    
    // reserved: 2ビット (bit 30-31)
    fields.insert("reserved", Field { start: bit_pos, length: 2 });
    bit_pos += 2;
    
    // timestamp: 64ビット (bit 32-95)
    fields.insert("timestamp", Field { start: bit_pos, length: 64 });
    bit_pos += 64;
    
    // area_code: 20ビット (bit 96-115)
    fields.insert("area_code", Field { start: bit_pos, length: 20 });
    bit_pos += 20;
    
    // checksum: 12ビット (bit 116-127)
    fields.insert("checksum", Field { start: bit_pos, length: 12 });
    
    println!("フィールド定義:");
    for (name, field) in &fields {
        println!("  {}: bit {}-{} ({}ビット)", name, field.start, field.start + field.length - 1, field.length);
    }
    println!();
    
    // テストパケット作成
    let mut packet_bits = 0u128;
    
    // フィールド設定
    set_bits(&mut packet_bits, fields["version"].start, fields["version"].length, 1);  // version = 1
    set_bits(&mut packet_bits, fields["packet_id"].start, fields["packet_id"].length, 85);  // packet_id = 85 (実際に送信されていた値)
    set_bits(&mut packet_bits, fields["type"].start, fields["type"].length, 2);  // type = 2 (Query)
    set_bits(&mut packet_bits, fields["weather_flag"].start, fields["weather_flag"].length, 1);  // weather = true
    set_bits(&mut packet_bits, fields["temperature_flag"].start, fields["temperature_flag"].length, 0);  // temperature = false
    set_bits(&mut packet_bits, fields["pop_flag"].start, fields["pop_flag"].length, 0);  // pop = false
    set_bits(&mut packet_bits, fields["alert_flag"].start, fields["alert_flag"].length, 0);  // alert = false
    set_bits(&mut packet_bits, fields["disaster_flag"].start, fields["disaster_flag"].length, 0);  // disaster = false
    set_bits(&mut packet_bits, fields["ex_flag"].start, fields["ex_flag"].length, 0);  // ex_flag = false
    set_bits(&mut packet_bits, fields["request_auth"].start, fields["request_auth"].length, 0);  // auth = false
    set_bits(&mut packet_bits, fields["response_auth"].start, fields["response_auth"].length, 0);  // auth = false
    set_bits(&mut packet_bits, fields["day"].start, fields["day"].length, 0);  // day = 0
    set_bits(&mut packet_bits, fields["reserved"].start, fields["reserved"].length, 0);  // reserved = 0
    set_bits(&mut packet_bits, fields["timestamp"].start, fields["timestamp"].length, 0x68A2EE00);  // timestamp (簡易)
    set_bits(&mut packet_bits, fields["area_code"].start, fields["area_code"].length, 11000);  // area_code = 11000
    set_bits(&mut packet_bits, fields["checksum"].start, fields["checksum"].length, 0x8A);  // checksum (仮)
    
    // バイト配列に変換
    let mut packet_bytes = [0u8; 16];
    u128_to_bytes_le(packet_bits, &mut packet_bytes);
    
    println!("生成されたパケット:");
    println!("  バイト: {:02X?}", packet_bytes);
    println!("  バイナリ: {:0128b}", packet_bits);
    println!();
    
    // 実際に送信されたパケット
    let actual_packet = [0xF0u8, 0x55, 0x00, 0x6B, 0x41, 0x00, 0x00, 0xA0, 0xEE, 0xA2, 0x68, 0x00, 0x00, 0x00, 0x00, 0x8A];
    println!("実際のパケット: {:02X?}", actual_packet);
    
    // 最初の2バイトを詳細分析
    let first_two_bytes = u16::from_le_bytes([actual_packet[0], actual_packet[1]]);
    println!("最初の2バイト: 0x{:04X} = {:016b}", first_two_bytes, first_two_bytes);
    
    let version = first_two_bytes & 0x0F;  // bit 0-3
    let packet_id = (first_two_bytes >> 4) & 0x0FFF;  // bit 4-15
    
    println!("解析結果:");
    println!("  version: {} (期待値: 1)", version);
    println!("  packet_id: {} (期待値: 85)", packet_id);
    
    if version != 1 {
        println!("⚠️ バージョンが正しくありません！");
    }
    if packet_id != 85 {
        println!("⚠️ パケットIDが正しくありません！");
    }
}