use crate::wip_common_rs::packet::core::exceptions::PacketParseError;
use std::collections::HashMap;
use std::fmt;
use serde_json::Value;
use once_cell::sync::Lazy;
use bitvec::prelude::*;

static EXTENDED_SPEC_JSON: &str = include_str!("../format_spec/extended_fields.json");

#[derive(Debug, Clone)]
struct ExtSpecEntry {
    id: u8,
    ty: String,
}

static EXT_MAP: Lazy<HashMap<String, ExtSpecEntry>> = Lazy::new(|| {
    let mut map = HashMap::new();
    let v: Value = serde_json::from_str(EXTENDED_SPEC_JSON).expect("extended_fields.json parse");
    if let Value::Object(obj) = v {
        for (name, def) in obj {
            let id = def.get("id").and_then(|x| x.as_u64()).unwrap_or(0) as u8;
            let ty = def.get("type").and_then(|x| x.as_str()).unwrap_or("str").to_string();
            map.insert(name, ExtSpecEntry { id, ty });
        }
    }
    map
});

static EXT_MAP_REV: Lazy<HashMap<u8, String>> = Lazy::new(|| {
    let mut rev = HashMap::new();
    for (k, v) in EXT_MAP.iter() {
        rev.insert(v.id, k.clone());
    }
    rev
});

#[derive(Debug, Clone, PartialEq)]
pub enum FieldType {
    U8,
    U16,
    U32,
    I8,
    I16,
    I32,
    String,
    Bytes,
    Bool,
    F32,
    F64,
}

impl FieldType {
    pub fn size_hint(&self) -> Option<usize> {
        match self {
            FieldType::U8 | FieldType::I8 | FieldType::Bool => Some(1),
            FieldType::U16 | FieldType::I16 => Some(2),
            FieldType::U32 | FieldType::I32 | FieldType::F32 => Some(4),
            FieldType::F64 => Some(8),
            FieldType::String | FieldType::Bytes => None,
        }
    }
}

impl fmt::Display for FieldType {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            FieldType::U8 => write!(f, "u8"),
            FieldType::U16 => write!(f, "u16"),
            FieldType::U32 => write!(f, "u32"),
            FieldType::I8 => write!(f, "i8"),
            FieldType::I16 => write!(f, "i16"),
            FieldType::I32 => write!(f, "i32"),
            FieldType::String => write!(f, "string"),
            FieldType::Bytes => write!(f, "bytes"),
            FieldType::Bool => write!(f, "bool"),
            FieldType::F32 => write!(f, "f32"),
            FieldType::F64 => write!(f, "f64"),
        }
    }
}

#[derive(Debug, Clone)]
pub struct FieldDefinition {
    pub name: String,
    pub field_type: FieldType,
    pub offset: Option<usize>,
    pub bit_offset: Option<u8>,
    pub bit_length: Option<u8>,
    pub required: bool,
    pub default_value: Option<FieldValue>,
    pub description: Option<String>,
    pub validation_rule: Option<String>,
}

impl FieldDefinition {
    pub fn new(name: String, field_type: FieldType) -> Self {
        Self {
            name,
            field_type,
            offset: None,
            bit_offset: None,
            bit_length: None,
            required: false,
            default_value: None,
            description: None,
            validation_rule: None,
        }
    }

    pub fn with_offset(mut self, offset: usize) -> Self {
        self.offset = Some(offset);
        self
    }

    pub fn with_bit_range(mut self, bit_offset: u8, bit_length: u8) -> Self {
        self.bit_offset = Some(bit_offset);
        self.bit_length = Some(bit_length);
        self
    }

    pub fn required(mut self) -> Self {
        self.required = true;
        self
    }

    pub fn with_default(mut self, value: FieldValue) -> Self {
        self.default_value = Some(value);
        self
    }

    pub fn with_description(mut self, description: String) -> Self {
        self.description = Some(description);
        self
    }

    pub fn with_validation(mut self, rule: String) -> Self {
        self.validation_rule = Some(rule);
        self
    }
}

#[derive(Debug, Clone, PartialEq)]
pub enum FieldValue {
    U8(u8),
    U16(u16),
    U32(u32),
    I8(i8),
    I16(i16),
    I32(i32),
    String(String),
    Bytes(Vec<u8>),
    Bool(bool),
    F32(f32),
    F64(f64),
}

impl FieldValue {
    pub fn get_type(&self) -> FieldType {
        match self {
            FieldValue::U8(_) => FieldType::U8,
            FieldValue::U16(_) => FieldType::U16,
            FieldValue::U32(_) => FieldType::U32,
            FieldValue::I8(_) => FieldType::I8,
            FieldValue::I16(_) => FieldType::I16,
            FieldValue::I32(_) => FieldType::I32,
            FieldValue::String(_) => FieldType::String,
            FieldValue::Bytes(_) => FieldType::Bytes,
            FieldValue::Bool(_) => FieldType::Bool,
            FieldValue::F32(_) => FieldType::F32,
            FieldValue::F64(_) => FieldType::F64,
        }
    }

    pub fn serialize(&self) -> Vec<u8> {
        match self {
            FieldValue::U8(v) => vec![*v],
            FieldValue::U16(v) => v.to_le_bytes().to_vec(),
            FieldValue::U32(v) => v.to_le_bytes().to_vec(),
            FieldValue::I8(v) => vec![*v as u8],
            FieldValue::I16(v) => v.to_le_bytes().to_vec(),
            FieldValue::I32(v) => v.to_le_bytes().to_vec(),
            FieldValue::String(v) => {
                let bytes = v.as_bytes();
                let mut result = (bytes.len() as u16).to_le_bytes().to_vec();
                result.extend_from_slice(bytes);
                result
            }
            FieldValue::Bytes(v) => {
                let mut result = (v.len() as u16).to_le_bytes().to_vec();
                result.extend_from_slice(v);
                result
            }
            FieldValue::Bool(v) => vec![if *v { 1 } else { 0 }],
            FieldValue::F32(v) => v.to_le_bytes().to_vec(),
            FieldValue::F64(v) => v.to_le_bytes().to_vec(),
        }
    }

    pub fn deserialize(field_type: &FieldType, data: &[u8]) -> Result<(Self, usize), PacketParseError> {
        match field_type {
            FieldType::U8 => {
                if data.is_empty() {
                    return Err(PacketParseError::new("Not enough data for u8"));
                }
                Ok((FieldValue::U8(data[0]), 1))
            }
            FieldType::U16 => {
                if data.len() < 2 {
                    return Err(PacketParseError::new("Not enough data for u16"));
                }
                let value = u16::from_le_bytes([data[0], data[1]]);
                Ok((FieldValue::U16(value), 2))
            }
            FieldType::U32 => {
                if data.len() < 4 {
                    return Err(PacketParseError::new("Not enough data for u32"));
                }
                let value = u32::from_le_bytes([data[0], data[1], data[2], data[3]]);
                Ok((FieldValue::U32(value), 4))
            }
            FieldType::I8 => {
                if data.is_empty() {
                    return Err(PacketParseError::new("Not enough data for i8"));
                }
                Ok((FieldValue::I8(data[0] as i8), 1))
            }
            FieldType::I16 => {
                if data.len() < 2 {
                    return Err(PacketParseError::new("Not enough data for i16"));
                }
                let value = i16::from_le_bytes([data[0], data[1]]);
                Ok((FieldValue::I16(value), 2))
            }
            FieldType::I32 => {
                if data.len() < 4 {
                    return Err(PacketParseError::new("Not enough data for i32"));
                }
                let value = i32::from_le_bytes([data[0], data[1], data[2], data[3]]);
                Ok((FieldValue::I32(value), 4))
            }
            FieldType::String => {
                if data.len() < 2 {
                    return Err(PacketParseError::new("Not enough data for string length"));
                }
                let len = u16::from_le_bytes([data[0], data[1]]) as usize;
                if data.len() < 2 + len {
                    return Err(PacketParseError::new("Not enough data for string content"));
                }
                let string_bytes = &data[2..2 + len];
                let value = String::from_utf8(string_bytes.to_vec())
                    .map_err(|_| PacketParseError::new("Invalid UTF-8 in string"))?;
                Ok((FieldValue::String(value), 2 + len))
            }
            FieldType::Bytes => {
                if data.len() < 2 {
                    return Err(PacketParseError::new("Not enough data for bytes length"));
                }
                let len = u16::from_le_bytes([data[0], data[1]]) as usize;
                if data.len() < 2 + len {
                    return Err(PacketParseError::new("Not enough data for bytes content"));
                }
                let bytes = data[2..2 + len].to_vec();
                Ok((FieldValue::Bytes(bytes), 2 + len))
            }
            FieldType::Bool => {
                if data.is_empty() {
                    return Err(PacketParseError::new("Not enough data for bool"));
                }
                Ok((FieldValue::Bool(data[0] != 0), 1))
            }
            FieldType::F32 => {
                if data.len() < 4 {
                    return Err(PacketParseError::new("Not enough data for f32"));
                }
                let value = f32::from_le_bytes([data[0], data[1], data[2], data[3]]);
                Ok((FieldValue::F32(value), 4))
            }
            FieldType::F64 => {
                if data.len() < 8 {
                    return Err(PacketParseError::new("Not enough data for f64"));
                }
                let value = f64::from_le_bytes([
                    data[0], data[1], data[2], data[3],
                    data[4], data[5], data[6], data[7],
                ]);
                Ok((FieldValue::F64(value), 8))
            }
        }
    }

    pub fn validate(&self, rule: Option<&str>) -> Result<(), PacketParseError> {
        if let Some(rule) = rule {
            match self {
                FieldValue::String(s) => {
                    if rule.starts_with("min_length:") {
                        let min_len: usize = rule[11..].parse()
                            .map_err(|_| PacketParseError::new("Invalid min_length rule"))?;
                        if s.len() < min_len {
                            return Err(PacketParseError::new("String too short"));
                        }
                    } else if rule.starts_with("max_length:") {
                        let max_len: usize = rule[11..].parse()
                            .map_err(|_| PacketParseError::new("Invalid max_length rule"))?;
                        if s.len() > max_len {
                            return Err(PacketParseError::new("String too long"));
                        }
                    }
                }
                FieldValue::U32(v) => {
                    if rule.starts_with("max:") {
                        let max_val: u32 = rule[4..].parse()
                            .map_err(|_| PacketParseError::new("Invalid max rule"))?;
                        if *v > max_val {
                            return Err(PacketParseError::new("Value exceeds maximum"));
                        }
                    } else if rule.starts_with("min:") {
                        let min_val: u32 = rule[4..].parse()
                            .map_err(|_| PacketParseError::new("Invalid min rule"))?;
                        if *v < min_val {
                            return Err(PacketParseError::new("Value below minimum"));
                        }
                    }
                }
                _ => {}
            }
        }
        Ok(())
    }
}

/// Python準拠の拡張フィールドpack（10bit length + 6bit key ヘッダ）
pub fn pack_ext_fields(fields: &HashMap<String, FieldValue>) -> Vec<u8> {
    let mut out_bits = bitvec![u8, Lsb0; 0; 0];

    for (k, v) in fields {
        if let Some(spec) = EXT_MAP.get(k) {
            let (payload, _ty) = encode_value(k, v);
            let len = payload.len();
            if len > ((1 << 10) - 1) { continue; }
            let mut header = BitVec::<u16, Lsb0>::with_capacity(16);
            // 10bit length（バイト長）
            let len_u16 = len as u16 & 0x03FF;
            for i in 0..10 { header.push(((len_u16 >> i) & 1) != 0); }
            // 6bit key（拡張ID）
            let id = spec.id as u16 & 0x003F;
            for i in 0..6 { header.push(((id >> i) & 1) != 0); }
            // append header bits
            out_bits.extend(header);
            // append payload bytes
            let mut payload_bits = BitVec::<u8, Lsb0>::with_capacity(len * 8);
            for b in payload { payload_bits.extend_from_bitslice(BitSlice::<u8, Lsb0>::from_element(&b)); }
            out_bits.extend(payload_bits);
        }
    }

    // to bytes
    out_bits.into_vec()
}

fn encode_value(key: &str, v: &FieldValue) -> (Vec<u8>, String) {
    match key {
        // 座標は1e6倍の整数（LE, i32）
        "latitude" => {
            if let FieldValue::F64(f) = v { let scaled = (*f * 1_000_000f64).round() as i32; return (scaled.to_le_bytes().to_vec(), "coord".into()); }
        }
        "longitude" => {
            if let FieldValue::F64(f) = v { let scaled = (*f * 1_000_000f64).round() as i32; return (scaled.to_le_bytes().to_vec(), "coord".into()); }
        }
        // alert/disaster はCSV文字列
        "alert" | "disaster" => {
            if let FieldValue::String(s) = v { return (s.as_bytes().to_vec(), "str".into()); }
        }
        // source は "ip:port" をPython準拠の整数に変換してLE u32/u64で送る（安全のためu64）
        "source" => {
            if let FieldValue::String(s) = v {
                if let Some((ip, port)) = s.split_once(':') {
                    let encoded = encode_source_to_int(ip, port.parse().unwrap_or(0));
                    return (encoded.to_le_bytes().to_vec(), "source".into());
                }
            }
        }
        _ => {}
    }
    // fallback: serialize as bytes if possible
    match v {
        FieldValue::String(s) => (s.as_bytes().to_vec(), "str".into()),
        FieldValue::U8(n) => (vec![*n], "u8".into()),
        FieldValue::U16(n) => (n.to_le_bytes().to_vec(), "u16".into()),
        FieldValue::U32(n) => (n.to_le_bytes().to_vec(), "u32".into()),
        FieldValue::I8(n) => (vec![*n as u8], "i8".into()),
        FieldValue::I16(n) => (n.to_le_bytes().to_vec(), "i16".into()),
        FieldValue::I32(n) => (n.to_le_bytes().to_vec(), "i32".into()),
        FieldValue::F32(n) => (n.to_le_bytes().to_vec(), "f32".into()),
        FieldValue::F64(n) => (n.to_le_bytes().to_vec(), "f64".into()),
        FieldValue::Bool(b) => (vec![if *b {1} else {0}], "bool".into()),
        FieldValue::Bytes(b) => (b.clone(), "bytes".into()),
    }
}

fn encode_source_to_int(ip: &str, port: u16) -> u64 {
    // Pythonの _source_to_int と互換のdecimal concat方式
    let parts: Vec<&str> = ip.split('.').collect();
    if parts.len() != 4 { return 0; }
    let p1 = format!("{}", parts[0].parse::<u16>().unwrap_or(0));
    let p2 = format!("{:03}", parts[1].parse::<u16>().unwrap_or(0));
    let p3 = format!("{:03}", parts[2].parse::<u16>().unwrap_or(0));
    let p4 = format!("{:03}", parts[3].parse::<u16>().unwrap_or(0));
    let port_s = format!("{:05}", port);
    format!("{}{}{}{}{}", p1, p2, p3, p4, port_s).parse::<u64>().unwrap_or(0)
}

fn decode_source_from_int(val: u64) -> String {
    let s = val.to_string();
    if s.len() < 14 { return "0.0.0.0:0".into(); }
    let port: u16 = s[s.len()-5..].parse().unwrap_or(0);
    let p4 = s[s.len()-8..s.len()-5].parse::<u16>().unwrap_or(0);
    let p3 = s[s.len()-11..s.len()-8].parse::<u16>().unwrap_or(0);
    let p2 = s[s.len()-14..s.len()-11].parse::<u16>().unwrap_or(0);
    let p1 = s[..s.len()-14].parse::<u16>().unwrap_or(0);
    format!("{}.{}.{}.{}:{}", p1, p2, p3, p4, port)
}

/// Python準拠の拡張フィールドunpack（10bit length + 6bit key ヘッダ）
pub fn unpack_ext_fields(data: &[u8]) -> HashMap<String, FieldValue> {
    let mut out = HashMap::new();
    if data.is_empty() { return out; }
    let bits = BitSlice::<u8, Lsb0>::from_slice(data);
    let mut idx: usize = 0;
    while idx + 16 <= bits.len() {
        // read 10-bit length
        let mut len: u16 = 0;
        for i in 0..10 { if bits.get(idx + i).map(|b| *b).unwrap_or(false) { len |= 1 << i; } }
        idx += 10;
        // read 6-bit key
        let mut key: u8 = 0;
        for i in 0..6 { if bits.get(idx + i).map(|b| *b).unwrap_or(false) { key |= 1 << i; } }
        idx += 6;
        let byte_len = len as usize;
        if idx + byte_len * 8 > bits.len() { break; }
        // read payload bytes
        let mut payload = vec![0u8; byte_len];
        for b in 0..byte_len {
            let mut v: u8 = 0;
            for i in 0..8 { if bits[idx + b*8 + i] { v |= 1 << i; } }
            payload[b] = v;
        }
        idx += byte_len * 8;

        if let Some(name) = EXT_MAP_REV.get(&key).cloned() {
            let fv = decode_value(&name, &payload);
            out.insert(name, fv);
        }
    }
    out
}

fn decode_value(name: &str, payload: &[u8]) -> FieldValue {
    match name {
        "latitude" | "longitude" => {
            if payload.len() >= 4 {
                let mut arr = [0u8;4];
                arr.copy_from_slice(&payload[..4]);
                let v = i32::from_le_bytes(arr) as f64 / 1_000_000f64;
                FieldValue::F64(v)
            } else { FieldValue::Bytes(payload.to_vec()) }
        }
        "source" => {
            // assume u64 le
            if payload.len() >= 8 {
                let mut arr = [0u8;8];
                arr.copy_from_slice(&payload[..8]);
                let n = u64::from_le_bytes(arr);
                FieldValue::String(decode_source_from_int(n))
            } else { FieldValue::Bytes(payload.to_vec()) }
        }
        _ => {
            // default to string (utf-8) if possible
            if let Ok(s) = String::from_utf8(payload.to_vec()) {
                FieldValue::String(s)
            } else {
                FieldValue::Bytes(payload.to_vec())
            }
        }
    }
}

#[cfg(test)]
mod tests_pack {
    use super::*;

    #[test]
    fn pack_unpack_lat_lon() {
        let mut map = HashMap::new();
        map.insert("latitude".to_string(), FieldValue::F64(35.123456));
        map.insert("longitude".to_string(), FieldValue::F64(139.654321));
        let bytes = pack_ext_fields(&map);
        let out = unpack_ext_fields(&bytes);
        match out.get("latitude").unwrap() { FieldValue::F64(v) => assert!((*v-35.123456).abs() < 1e-6), _=>panic!() }
        match out.get("longitude").unwrap() { FieldValue::F64(v) => assert!((*v-139.654321).abs() < 1e-6), _=>panic!() }
    }

    #[test]
    fn pack_unpack_alert() {
        let mut map = HashMap::new();
        map.insert("alert".to_string(), FieldValue::String("A,B".into()));
        let bytes = pack_ext_fields(&map);
        let out = unpack_ext_fields(&bytes);
        assert_eq!(out.get("alert"), Some(&FieldValue::String("A,B".into())));
    }

    #[test]
    fn pack_unpack_source() {
        let mut map = HashMap::new();
        map.insert("source".to_string(), FieldValue::String("127.0.0.1:12345".into()));
        let bytes = pack_ext_fields(&map);
        let out = unpack_ext_fields(&bytes);
        assert_eq!(out.get("source"), Some(&FieldValue::String("127.0.0.1:12345".into())));
    }

    #[test]
    fn golden_pack_latitude_35_0() {
        // latitude=35.0 -> scaled 35_000_000 -> LE i32 = [0xC0,0x0E,0x16,0x02]
        // header: len=4 (10bit), id=33 (6bit) -> bytes [0x04, 0x84]
        let mut map = HashMap::new();
        map.insert("latitude".to_string(), FieldValue::F64(35.0));
        let bytes = pack_ext_fields(&map);
        assert_eq!(bytes, vec![0x04, 0x84, 0xC0, 0x0E, 0x16, 0x02]);
    }
}

impl fmt::Display for FieldValue {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            FieldValue::U8(v) => write!(f, "{}", v),
            FieldValue::U16(v) => write!(f, "{}", v),
            FieldValue::U32(v) => write!(f, "{}", v),
            FieldValue::I8(v) => write!(f, "{}", v),
            FieldValue::I16(v) => write!(f, "{}", v),
            FieldValue::I32(v) => write!(f, "{}", v),
            FieldValue::String(v) => write!(f, "\"{}\"", v),
            FieldValue::Bytes(v) => write!(f, "{:?}", v),
            FieldValue::Bool(v) => write!(f, "{}", v),
            FieldValue::F32(v) => write!(f, "{}", v),
            FieldValue::F64(v) => write!(f, "{}", v),
        }
    }
}

#[derive(Debug, Clone)]
pub struct ExtendedFieldManager {
    definitions: HashMap<String, FieldDefinition>,
    values: HashMap<String, FieldValue>,
}

impl ExtendedFieldManager {
    pub fn new() -> Self {
        Self {
            definitions: HashMap::new(),
            values: HashMap::new(),
        }
    }

    pub fn add_definition(&mut self, definition: FieldDefinition) {
        let name = definition.name.clone();
        self.definitions.insert(name, definition);
    }

    pub fn set_value(&mut self, name: String, value: FieldValue) -> Result<(), PacketParseError> {
        if let Some(def) = self.definitions.get(&name) {
            if def.field_type != value.get_type() {
                return Err(PacketParseError::new(&format!(
                    "Type mismatch for field '{}': expected {}, got {}",
                    name, def.field_type, value.get_type()
                )));
            }
            value.validate(def.validation_rule.as_deref())?;
            self.values.insert(name, value);
        } else {
            return Err(PacketParseError::new(&format!("Unknown field: {}", name)));
        }
        Ok(())
    }

    pub fn get_value(&self, name: &str) -> Option<&FieldValue> {
        self.values.get(name).or_else(|| {
            self.definitions.get(name)?.default_value.as_ref()
        })
    }

    pub fn get_definition(&self, name: &str) -> Option<&FieldDefinition> {
        self.definitions.get(name)
    }

    pub fn validate_all(&self) -> Result<(), PacketParseError> {
        for (name, def) in &self.definitions {
            if def.required && !self.values.contains_key(name) && def.default_value.is_none() {
                return Err(PacketParseError::new(&format!("Required field '{}' is missing", name)));
            }
        }
        Ok(())
    }

    pub fn serialize(&self) -> Result<Vec<u8>, PacketParseError> {
        self.validate_all()?;
        
        let mut buffer = Vec::new();
        let field_count = self.values.len() as u16;
        buffer.extend_from_slice(&field_count.to_le_bytes());
        
        for (name, value) in &self.values {
            let name_bytes = name.as_bytes();
            let name_len = name_bytes.len() as u16;
            buffer.extend_from_slice(&name_len.to_le_bytes());
            buffer.extend_from_slice(name_bytes);
            
            let type_id = value.get_type() as u8;
            buffer.push(type_id);
            
            let value_bytes = value.serialize();
            buffer.extend_from_slice(&value_bytes);
        }
        
        Ok(buffer)
    }

    pub fn deserialize(&mut self, data: &[u8]) -> Result<usize, PacketParseError> {
        if data.len() < 2 {
            return Err(PacketParseError::new("Not enough data for field count"));
        }
        
        let field_count = u16::from_le_bytes([data[0], data[1]]) as usize;
        let mut offset = 2;
        
        for _ in 0..field_count {
            if offset + 2 > data.len() {
                return Err(PacketParseError::new("Not enough data for field name length"));
            }
            
            let name_len = u16::from_le_bytes([data[offset], data[offset + 1]]) as usize;
            offset += 2;
            
            if offset + name_len > data.len() {
                return Err(PacketParseError::new("Not enough data for field name"));
            }
            
            let name = String::from_utf8(data[offset..offset + name_len].to_vec())
                .map_err(|_| PacketParseError::new("Invalid UTF-8 in field name"))?;
            offset += name_len;
            
            if offset >= data.len() {
                return Err(PacketParseError::new("Not enough data for field type"));
            }
            
            let type_id = data[offset];
            offset += 1;
            
            let field_type = match type_id {
                0 => FieldType::U8,
                1 => FieldType::U16,
                2 => FieldType::U32,
                3 => FieldType::I8,
                4 => FieldType::I16,
                5 => FieldType::I32,
                6 => FieldType::String,
                7 => FieldType::Bytes,
                8 => FieldType::Bool,
                9 => FieldType::F32,
                10 => FieldType::F64,
                _ => return Err(PacketParseError::new("Unknown field type")),
            };
            
            let (value, consumed) = FieldValue::deserialize(&field_type, &data[offset..])?;
            offset += consumed;
            
            self.values.insert(name, value);
        }
        
        Ok(offset)
    }

    pub fn clear(&mut self) {
        self.values.clear();
    }

    pub fn get_all_values(&self) -> &HashMap<String, FieldValue> {
        &self.values
    }

    pub fn get_all_definitions(&self) -> &HashMap<String, FieldDefinition> {
        &self.definitions
    }
}

impl Default for ExtendedFieldManager {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_field_value_serialization() {
        let value = FieldValue::String("test".to_string());
        let serialized = value.serialize();
        let (deserialized, consumed) = FieldValue::deserialize(&FieldType::String, &serialized).unwrap();
        assert_eq!(value, deserialized);
        assert_eq!(consumed, serialized.len());
    }

    #[test]
    fn test_extended_field_manager() {
        let mut manager = ExtendedFieldManager::new();
        
        let def = FieldDefinition::new("test_field".to_string(), FieldType::U32)
            .required()
            .with_validation("max:1000".to_string());
        manager.add_definition(def);
        
        manager.set_value("test_field".to_string(), FieldValue::U32(500)).unwrap();
        assert_eq!(manager.get_value("test_field"), Some(&FieldValue::U32(500)));
        
        assert!(manager.validate_all().is_ok());
        
        let serialized = manager.serialize().unwrap();
        let mut new_manager = ExtendedFieldManager::new();
        new_manager.deserialize(&serialized).unwrap();
        
        assert_eq!(new_manager.get_value("test_field"), Some(&FieldValue::U32(500)));
    }

    #[test]
    fn test_validation() {
        let value = FieldValue::String("test".to_string());
        assert!(value.validate(Some("min_length:3")).is_ok());
        assert!(value.validate(Some("min_length:5")).is_err());
        
        let value = FieldValue::U32(100);
        assert!(value.validate(Some("max:200")).is_ok());
        assert!(value.validate(Some("max:50")).is_err());
    }
}
