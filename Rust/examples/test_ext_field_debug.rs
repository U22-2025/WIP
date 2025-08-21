use wip_rust::wip_common_rs::packet::core::extended_field::{pack_ext_fields, unpack_ext_fields, FieldValue};
use std::collections::HashMap;

fn main() {
    println!("Testing extended field packing for auth_hash");
    
    // Test auth_hash field according to extended_fields.json: {"id": 4, "type":"str"}
    let mut fields = HashMap::new();
    let auth_hash = "abcd1234567890ef"; // Sample auth hash
    fields.insert("auth_hash".to_string(), FieldValue::String(auth_hash.to_string()));
    
    println!("Input field: auth_hash = \"{}\"", auth_hash);
    
    // Pack the field
    let packed = pack_ext_fields(&fields);
    println!("Packed bytes: {} bytes", packed.len());
    println!("Packed hex: {:02X?}", packed);
    
    // Show binary structure
    if packed.len() >= 2 {
        let len_bits = (packed[0] as u16) | ((packed[1] as u16 & 0x03) << 8);
        let id_bits = (packed[1] >> 2) & 0x3F;
        println!("Header analysis:");
        println!("  Length (10 bits): {} bytes", len_bits);
        println!("  ID (6 bits): {}", id_bits);
        
        if packed.len() > 2 {
            println!("  Payload: {:02X?}", &packed[2..]);
            println!("  Payload as string: {:?}", String::from_utf8_lossy(&packed[2..]));
        }
    }
    
    // Unpack and verify
    let unpacked = unpack_ext_fields(&packed);
    println!("Unpacked fields: {:?}", unpacked);
    
    // Verify round-trip
    if let Some(FieldValue::String(unpacked_hash)) = unpacked.get("auth_hash") {
        println!("Round-trip success: {} -> {}", auth_hash, unpacked_hash);
        if auth_hash == unpacked_hash {
            println!("✓ Round-trip verified correctly");
        } else {
            println!("✗ Round-trip mismatch!");
        }
    } else {
        println!("✗ Failed to unpack auth_hash field");
    }
}