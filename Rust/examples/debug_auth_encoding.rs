use wip_rust::wip_common_rs::packet::core::extended_field::{pack_ext_fields, unpack_ext_fields, FieldValue};
use std::collections::HashMap;

fn main() {
    println!("=== Debugging auth_hash encoding issue ===\n");
    
    let auth_hash = "1f9e648b2c8fa0a8e78581714e04ca807c788b8a7c5c95318ed0937b0f048b88";
    
    // Test 1: Current implementation (String with length prefix)
    println!("Test 1: auth_hash as FieldValue::String");
    let mut fields1 = HashMap::new();
    fields1.insert("auth_hash".to_string(), FieldValue::String(auth_hash.to_string()));
    let packed1 = pack_ext_fields(&fields1);
    
    println!("  Packed bytes: {} bytes", packed1.len());
    println!("  Header: {:02X?}", &packed1[0..2]);
    println!("  First 16 payload bytes: {:02X?}", &packed1[2..18.min(packed1.len())]);
    
    if packed1.len() >= 2 {
        let len_bits = (packed1[0] as u16) | ((packed1[1] as u16 & 0x03) << 8);
        let id_bits = (packed1[1] >> 2) & 0x3F;
        println!("  Length field: {} bytes", len_bits);
        println!("  ID field: {}", id_bits);
    }
    
    // Test 2: Try auth_hash as raw bytes (no length prefix)
    println!("\nTest 2: auth_hash as FieldValue::Bytes");
    let auth_bytes = hex::decode(auth_hash).unwrap_or_else(|_| auth_hash.as_bytes().to_vec());
    let mut fields2 = HashMap::new();
    fields2.insert("auth_hash".to_string(), FieldValue::Bytes(auth_bytes));
    let packed2 = pack_ext_fields(&fields2);
    
    println!("  Packed bytes: {} bytes", packed2.len());
    println!("  Header: {:02X?}", &packed2[0..2]);
    if packed2.len() > 2 {
        println!("  First 16 payload bytes: {:02X?}", &packed2[2..18.min(packed2.len())]);
    }
    
    if packed2.len() >= 2 {
        let len_bits = (packed2[0] as u16) | ((packed2[1] as u16 & 0x03) << 8);
        let id_bits = (packed2[1] >> 2) & 0x3F;
        println!("  Length field: {} bytes", len_bits);
        println!("  ID field: {}", id_bits);
    }
    
    // Decode what the current approach actually produces
    println!("\n=== Analyzing current auth_hash encoding ===");
    let unpacked1 = unpack_ext_fields(&packed1);
    println!("Unpacked fields from String approach: {:?}", unpacked1);
    
    let unpacked2 = unpack_ext_fields(&packed2);
    println!("Unpacked fields from Bytes approach: {:?}", unpacked2);
    
    // Show what the actual string serialization looks like
    let string_val = FieldValue::String(auth_hash.to_string());
    let serialized = string_val.serialize();
    println!("\nString serialization details:");
    println!("  Total serialized bytes: {}", serialized.len());
    println!("  First 8 bytes: {:02X?}", &serialized[0..8.min(serialized.len())]);
    println!("  As hex: {}", hex::encode(&serialized));
}