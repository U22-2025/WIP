use crate::wip_common_rs::packet::core::exceptions::PacketParseError;
use std::collections::HashMap;

#[derive(Debug, Clone)]
pub struct GenericRequest {
    packet_id: u16,
    packet_type: u8,
    data: Vec<u8>,
    fields: HashMap<String, Vec<u8>>,
}

impl GenericRequest {
    pub fn new(packet_type: u8) -> Self {
        Self {
            packet_id: 0,
            packet_type,
            data: Vec::new(),
            fields: HashMap::new(),
        }
    }

    pub fn with_id(mut self, id: u16) -> Self {
        self.packet_id = id;
        self
    }

    pub fn with_data(mut self, data: Vec<u8>) -> Self {
        self.data = data;
        self
    }

    pub fn add_field<T: AsRef<[u8]>>(mut self, name: String, value: T) -> Self {
        self.fields.insert(name, value.as_ref().to_vec());
        self
    }

    pub fn get_packet_id(&self) -> u16 {
        self.packet_id
    }

    pub fn get_packet_type(&self) -> u8 {
        self.packet_type
    }

    pub fn get_data(&self) -> &[u8] {
        &self.data
    }

    pub fn get_field(&self, name: &str) -> Option<&[u8]> {
        self.fields.get(name).map(|v| v.as_slice())
    }

    pub fn serialize(&self) -> Result<Vec<u8>, PacketParseError> {
        let mut buffer = Vec::new();
        
        buffer.extend_from_slice(&self.packet_id.to_le_bytes());
        buffer.push(self.packet_type);
        
        let data_len = self.data.len() as u16;
        buffer.extend_from_slice(&data_len.to_le_bytes());
        buffer.extend_from_slice(&self.data);
        
        let fields_count = self.fields.len() as u16;
        buffer.extend_from_slice(&fields_count.to_le_bytes());
        
        for (name, value) in &self.fields {
            let name_bytes = name.as_bytes();
            let name_len = name_bytes.len() as u16;
            buffer.extend_from_slice(&name_len.to_le_bytes());
            buffer.extend_from_slice(name_bytes);
            
            let value_len = value.len() as u16;
            buffer.extend_from_slice(&value_len.to_le_bytes());
            buffer.extend_from_slice(value);
        }
        
        Ok(buffer)
    }

    pub fn deserialize(data: &[u8]) -> Result<Self, PacketParseError> {
        if data.len() < 7 {
            return Err(PacketParseError::new("Data too short for GenericRequest"));
        }

        let mut offset = 0;
        
        let packet_id = u16::from_le_bytes([data[offset], data[offset + 1]]);
        offset += 2;
        
        let packet_type = data[offset];
        offset += 1;
        
        let data_len = u16::from_le_bytes([data[offset], data[offset + 1]]) as usize;
        offset += 2;
        
        if offset + data_len > data.len() {
            return Err(PacketParseError::new("Invalid data length"));
        }
        
        let packet_data = data[offset..offset + data_len].to_vec();
        offset += data_len;
        
        if offset + 2 > data.len() {
            return Err(PacketParseError::new("Missing fields count"));
        }
        
        let fields_count = u16::from_le_bytes([data[offset], data[offset + 1]]) as usize;
        offset += 2;
        
        let mut fields = HashMap::new();
        
        for _ in 0..fields_count {
            if offset + 2 > data.len() {
                return Err(PacketParseError::new("Missing field name length"));
            }
            
            let name_len = u16::from_le_bytes([data[offset], data[offset + 1]]) as usize;
            offset += 2;
            
            if offset + name_len > data.len() {
                return Err(PacketParseError::new("Invalid field name length"));
            }
            
            let name = String::from_utf8(data[offset..offset + name_len].to_vec())
                .map_err(|_| PacketParseError::new("Invalid UTF-8 in field name"))?;
            offset += name_len;
            
            if offset + 2 > data.len() {
                return Err(PacketParseError::new("Missing field value length"));
            }
            
            let value_len = u16::from_le_bytes([data[offset], data[offset + 1]]) as usize;
            offset += 2;
            
            if offset + value_len > data.len() {
                return Err(PacketParseError::new("Invalid field value length"));
            }
            
            let value = data[offset..offset + value_len].to_vec();
            offset += value_len;
            
            fields.insert(name, value);
        }
        
        Ok(Self {
            packet_id,
            packet_type,
            data: packet_data,
            fields,
        })
    }

    pub fn validate(&self) -> Result<(), PacketParseError> {
        if self.packet_type == 0 {
            return Err(PacketParseError::new("Invalid packet type"));
        }
        
        for (name, _) in &self.fields {
            if name.is_empty() {
                return Err(PacketParseError::new("Empty field name"));
            }
        }
        
        Ok(())
    }
}


#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_generic_request_creation() {
        let request = GenericRequest::new(5)
            .with_id(123)
            .with_data(vec![1, 2, 3, 4])
            .add_field("test_field".to_string(), vec![5, 6, 7]);

        assert_eq!(request.get_packet_id(), 123);
        assert_eq!(request.get_packet_type(), 5);
        assert_eq!(request.get_data(), &[1, 2, 3, 4]);
        assert_eq!(request.get_field("test_field"), Some([5, 6, 7].as_slice()));
    }

    #[test]
    fn test_serialization_deserialization() {
        let original = GenericRequest::new(10)
            .with_id(456)
            .with_data(vec![10, 20, 30])
            .add_field("field1".to_string(), vec![40, 50])
            .add_field("field2".to_string(), vec![60]);

        let serialized = original.serialize().unwrap();
        let deserialized = GenericRequest::deserialize(&serialized).unwrap();

        assert_eq!(deserialized.get_packet_id(), 456);
        assert_eq!(deserialized.get_packet_type(), 10);
        assert_eq!(deserialized.get_data(), &[10, 20, 30]);
        assert_eq!(deserialized.get_field("field1"), Some([40, 50].as_slice()));
        assert_eq!(deserialized.get_field("field2"), Some([60].as_slice()));
    }

    #[test]
    fn test_validation() {
        let valid_request = GenericRequest::new(1);
        assert!(valid_request.validate().is_ok());

        let invalid_request = GenericRequest::new(0);
        assert!(invalid_request.validate().is_err());
    }
}