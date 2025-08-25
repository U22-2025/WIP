use bitvec::prelude::*;
use wip_rust::wip_common_rs::packet::core::{
    calc_checksum12, ExtendedFieldManager, FieldDefinition, FieldType, FieldValue,
};
use wip_rust::wip_common_rs::packet::types::{
    LocationRequest, LocationResponse, QueryRequest, ReportRequest, ReportResponse,
};

fn print_hex(label: &str, bytes: &[u8]) {
    let hex = bytes.iter().map(|b| format!("{:02X}", b)).collect::<Vec<_>>().join(" ");
    println!("{} ({} bytes):\n{}\n", label, bytes.len(), hex);
}

fn build_fake_location_response(area_code: u32, version: u8, packet_id: u16,
                                latitude: f64, longitude: f64, source: &str) -> Vec<u8> {
    // 20バイト固定部（ヘッダ16B + 末尾4B）
    let mut bits = bitvec![u8, Lsb0; 0; 160];
    bits[0..4].store(version);
    bits[4..16].store(packet_id);
    bits[16..19].store(1u8); // type=1 (LocationResponse)
    bits[96..116].store(area_code);
    let mut data = [0u8; 20];
    data.copy_from_slice(bits.as_raw_slice());

    // ヘッダ16Bのチェックサムを計算して埋め込み
    let checksum = calc_checksum12(&data[..16]);
    let mut head_bits = bitvec![u8, Lsb0; 0; 128];
    head_bits.copy_from_bitslice(&BitSlice::<u8, Lsb0>::from_slice(&data[..16]));
    head_bits[116..128].store(checksum);
    let mut head = [0u8; 16];
    head.copy_from_slice(head_bits.as_raw_slice());
    data[..16].copy_from_slice(&head);

    // 拡張フィールド（latitude/longitude/source）
    let mut efm = ExtendedFieldManager::new();
    efm.add_definition(FieldDefinition::new("latitude".to_string(), FieldType::F64));
    efm.add_definition(FieldDefinition::new("longitude".to_string(), FieldType::F64));
    efm.add_definition(FieldDefinition::new("source".to_string(), FieldType::String));
    let _ = efm.set_value("latitude".to_string(), FieldValue::F64(latitude));
    let _ = efm.set_value("longitude".to_string(), FieldValue::F64(longitude));
    let _ = efm.set_value("source".to_string(), FieldValue::String(source.to_string()));
    let ext = efm.serialize().unwrap();

    let mut out = Vec::with_capacity(20 + ext.len());
    out.extend_from_slice(&data);
    out.extend_from_slice(&ext);
    out
}

fn build_fake_report_response(area_code: u32, version: u8, packet_id: u16,
                              weather_code: u16, temp_c: i8, pop: u8) -> Vec<u8> {
    // Use the same approach as ReportRequest::to_bytes() to ensure compatibility
    use wip_rust::wip_common_rs::packet::core::bit_utils::{bytes_to_u128_le, u128_to_bytes_le};
    use once_cell::sync::Lazy;
    use wip_rust::wip_common_rs::packet::core::format_base::JsonPacketSpecLoader;
    
    static RESPONSE_FIELDS_LOCAL: Lazy<wip_rust::wip_common_rs::packet::core::bit_utils::PacketFields> = Lazy::new(|| {
        let json = include_str!("../src/wip_common_rs/packet/format_spec/response_fields.json");
        let (fields, _specs) = JsonPacketSpecLoader::load_from_json(json).expect("response spec parse");
        fields
    });
    
    let fields = &*RESPONSE_FIELDS_LOCAL;
    let mut fixed = [0u8; 20];

    // Build header (first 16 bytes) using u128 bit manipulation
    let mut head = [0u8; 16];
    let mut bits_u128 = bytes_to_u128_le(&head);
    
    // Set all header fields using the proper field positions
    if let Some(f) = fields.get_field("version") { f.set(&mut bits_u128, version as u128); }
    if let Some(f) = fields.get_field("packet_id") { f.set(&mut bits_u128, packet_id as u128); }
    if let Some(f) = fields.get_field("type") { f.set(&mut bits_u128, 5u128); } // Type 5 for ReportResponse
    if let Some(f) = fields.get_field("weather_flag") { f.set(&mut bits_u128, if weather_code != 0 { 1 } else { 0 }); }
    if let Some(f) = fields.get_field("temperature_flag") { f.set(&mut bits_u128, if temp_c != 0 { 1 } else { 0 }); }
    if let Some(f) = fields.get_field("pop_flag") { f.set(&mut bits_u128, if pop != 0 { 1 } else { 0 }); }
    if let Some(f) = fields.get_field("alert_flag") { f.set(&mut bits_u128, 0); }
    if let Some(f) = fields.get_field("disaster_flag") { f.set(&mut bits_u128, 0); }
    if let Some(f) = fields.get_field("ex_flag") { f.set(&mut bits_u128, 0); }
    if let Some(f) = fields.get_field("request_auth") { f.set(&mut bits_u128, 0); }
    if let Some(f) = fields.get_field("response_auth") { f.set(&mut bits_u128, 0); }
    if let Some(f) = fields.get_field("day") { f.set(&mut bits_u128, 0); }
    if let Some(f) = fields.get_field("reserved") { f.set(&mut bits_u128, 0); }
    if let Some(f) = fields.get_field("timestamp") { f.set(&mut bits_u128, 0); } // Not needed for response
    if let Some(f) = fields.get_field("area_code") { f.set(&mut bits_u128, area_code as u128); }
    if let Some(f) = fields.get_field("checksum") { f.set(&mut bits_u128, 0); } // Will be set later
    
    u128_to_bytes_le(bits_u128, &mut head);

    // Calculate checksum and set it
    let checksum = calc_checksum12(&head);
    let mut bits_u128 = bytes_to_u128_le(&head);
    if let Some(f) = fields.get_field("checksum") { 
        f.set(&mut bits_u128, checksum as u128); 
    }
    u128_to_bytes_le(bits_u128, &mut head);

    // Copy header to fixed buffer
    fixed[..16].copy_from_slice(&head);
    
    // Set the payload fields using BitSlice for the tail fields
    let bits = BitSlice::<u8, Lsb0>::from_slice_mut(&mut fixed);
    if let Some(f) = fields.get_field("weather_code") {
        bits[f.start..f.start+f.length].store(weather_code);
    }
    if let Some(f) = fields.get_field("temperature") {
        bits[f.start..f.start+f.length].store((temp_c as i16 + 100) as u8);
    }
    if let Some(f) = fields.get_field("pop") {
        bits[f.start..f.start+f.length].store(pop);
    }

    fixed.to_vec()
}

fn main() {
    println!("=== WIP Packet Showcase ===\n");

    // 1) LocationRequest（座標→エリアコード）
    let loc_req = LocationRequest::create_coordinate_lookup(
        35.6895, 139.6917, 0x101, true, true, true, false, false, 0, 1,
    );
    let loc_req_bytes = loc_req.to_bytes();
    print_hex("LocationRequest", &loc_req_bytes);

    // 2) ReportRequest（センサーデータ送信）
    let rep_req = ReportRequest::create_sensor_data_report(
        "011000", Some(100), Some(22.0), Some(30), None, None, 1, 0x202,
    );
    let rep_req_bytes = rep_req.to_bytes();
    print_hex("ReportRequest", &rep_req_bytes);

    // 3) QueryRequest（エリアコードから気象データ要求）
    let qry_req = QueryRequest::create_query_request(
        "011000", 0x303, true, true, true, false, false, 0, 1,
    );
    let qry_req_bytes = qry_req.to_bytes();
    print_hex("QueryRequest", &qry_req_bytes);

    // 4) LocationResponse のダミーパケットを生成して復号
    let loc_resp_bytes = build_fake_location_response(11000, 1, 0x404, 35.0, 139.0, "127.0.0.1:12345");
    print_hex("LocationResponse (fake)", &loc_resp_bytes);
    if let Some(loc_resp) = LocationResponse::from_bytes(&loc_resp_bytes) {
        println!("Parsed LocationResponse: area_code={}, coords={:?}, source={:?}\n",
                 loc_resp.get_area_code_str(), loc_resp.get_coordinates(), loc_resp.get_source_info());
    } else {
        println!("Failed to parse LocationResponse\n");
    }

    // 5) ReportResponse のダミーパケットを生成して復号
    let rep_resp_bytes = build_fake_report_response(11000, 1, 0x505, 10, 22, 35);
    print_hex("ReportResponse (fake)", &rep_resp_bytes);
    
    // Debug the packet structure
    use bitvec::prelude::*;
    let bits = BitSlice::<u8, Lsb0>::from_slice(&rep_resp_bytes);
    println!("Debug packet structure:");
    println!("  version (bits 0-3): {:?}", bits[0..4].load::<u8>());
    println!("  packet_id (bits 4-15): 0x{:03X}", bits[4..16].load::<u16>());
    println!("  type (bits 16-18): {}", bits[16..19].load::<u8>());
    println!("  area_code (bits 96-115): {}", bits[96..116].load::<u32>());
    println!("  weather_code (bits 128-143): {}", bits[128..144].load::<u16>());
    println!("  temperature (bits 144-151): {}", bits[144..152].load::<u8>());
    println!("  pop (bits 152-159): {}", bits[152..160].load::<u8>());
    println!();
    
    if let Some(rep_resp) = ReportResponse::from_bytes(&rep_resp_bytes) {
        println!("Parsed ReportResponse: area_code={}, weather_code={:?}, temp_c={:?}, pop={:?}",
                 rep_resp.area_code, rep_resp.weather_code, rep_resp.temperature_c, rep_resp.pop);
    } else {
        println!("Failed to parse ReportResponse");
    }
}

