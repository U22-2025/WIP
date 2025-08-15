use crate::wip_common_rs::packet::core::exceptions::PacketParseError;
use std::collections::HashMap;
use std::fmt;

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