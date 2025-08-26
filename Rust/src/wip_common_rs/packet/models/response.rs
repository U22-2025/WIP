use crate::wip_common_rs::packet::core::exceptions::PacketParseError;
use std::collections::HashMap;

#[derive(Debug, Clone)]
pub struct GenericResponse {
    packet_id: u16,
    packet_type: u8,
    status_code: u16,
    data: Vec<u8>,
    fields: HashMap<String, Vec<u8>>,
    error_message: Option<String>,
}

impl GenericResponse {
    pub fn new(packet_type: u8, status_code: u16) -> Self {
        Self {
            packet_id: 0,
            packet_type,
            status_code,
            data: Vec::new(),
            fields: HashMap::new(),
            error_message: None,
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

    pub fn with_error(mut self, error_message: String) -> Self {
        self.error_message = Some(error_message);
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

    pub fn get_status_code(&self) -> u16 {
        self.status_code
    }

    pub fn get_data(&self) -> &[u8] {
        &self.data
    }

    pub fn get_field(&self, name: &str) -> Option<&[u8]> {
        self.fields.get(name).map(|v| v.as_slice())
    }

    pub fn get_error_message(&self) -> Option<&str> {
        self.error_message.as_deref()
    }

    pub fn is_success(&self) -> bool {
        self.status_code < 400
    }

    pub fn is_error(&self) -> bool {
        self.status_code >= 400
    }

    pub fn serialize(&self) -> Result<Vec<u8>, PacketParseError> {
        let mut buffer = Vec::new();
        
        buffer.extend_from_slice(&self.packet_id.to_le_bytes());
        buffer.push(self.packet_type);
        buffer.extend_from_slice(&self.status_code.to_le_bytes());
        
        let data_len = self.data.len() as u16;
        buffer.extend_from_slice(&data_len.to_le_bytes());
        buffer.extend_from_slice(&self.data);
        
        let error_msg_bytes = self.error_message.as_deref().unwrap_or("").as_bytes();
        let error_len = error_msg_bytes.len() as u16;
        buffer.extend_from_slice(&error_len.to_le_bytes());
        buffer.extend_from_slice(error_msg_bytes);
        
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
        if data.len() < 9 {
            return Err(PacketParseError::new("Data too short for GenericResponse"));
        }

        let mut offset = 0;
        
        let packet_id = u16::from_le_bytes([data[offset], data[offset + 1]]);
        offset += 2;
        
        let packet_type = data[offset];
        offset += 1;
        
        let status_code = u16::from_le_bytes([data[offset], data[offset + 1]]);
        offset += 2;
        
        let data_len = u16::from_le_bytes([data[offset], data[offset + 1]]) as usize;
        offset += 2;
        
        if offset + data_len > data.len() {
            return Err(PacketParseError::new("Invalid data length"));
        }
        
        let packet_data = data[offset..offset + data_len].to_vec();
        offset += data_len;
        
        if offset + 2 > data.len() {
            return Err(PacketParseError::new("Missing error message length"));
        }
        
        let error_len = u16::from_le_bytes([data[offset], data[offset + 1]]) as usize;
        offset += 2;
        
        if offset + error_len > data.len() {
            return Err(PacketParseError::new("Invalid error message length"));
        }
        
        let error_message = if error_len > 0 {
            Some(String::from_utf8(data[offset..offset + error_len].to_vec())
                .map_err(|_| PacketParseError::new("Invalid UTF-8 in error message"))?)
        } else {
            None
        };
        offset += error_len;
        
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
            status_code,
            data: packet_data,
            fields,
            error_message,
        })
    }

    pub fn validate(&self) -> Result<(), PacketParseError> {
        if self.packet_type == 0 {
            return Err(PacketParseError::new("Invalid packet type"));
        }
        
        if self.is_error() && self.error_message.is_none() {
            return Err(PacketParseError::new("Error response must have error message"));
        }
        
        for (name, _) in &self.fields {
            if name.is_empty() {
                return Err(PacketParseError::new("Empty field name"));
            }
        }
        
        Ok(())
    }

    pub fn success(packet_type: u8) -> Self {
        Self::new(packet_type, 200)
    }

    pub fn error(packet_type: u8, status_code: u16, error_message: String) -> Self {
        Self::new(packet_type, status_code).with_error(error_message)
    }

    pub fn not_found(packet_type: u8) -> Self {
        Self::error(packet_type, 404, "Not Found".to_string())
    }

    pub fn internal_error(packet_type: u8) -> Self {
        Self::error(packet_type, 500, "Internal Server Error".to_string())
    }

    pub fn bad_request(packet_type: u8, message: String) -> Self {
        Self::error(packet_type, 400, message)
    }
}


#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_generic_response_creation() {
        let response = GenericResponse::new(5, 200)
            .with_id(123)
            .with_data(vec![1, 2, 3, 4])
            .add_field("test_field".to_string(), vec![5, 6, 7]);

        assert_eq!(response.get_packet_id(), 123);
        assert_eq!(response.get_packet_type(), 5);
        assert_eq!(response.get_status_code(), 200);
        assert_eq!(response.get_data(), &[1, 2, 3, 4]);
        assert_eq!(response.get_field("test_field"), Some([5, 6, 7].as_slice()));
        assert!(response.is_success());
        assert!(!response.is_error());
    }

    #[test]
    fn test_error_response() {
        let response = GenericResponse::error(10, 404, "Not found".to_string())
            .with_id(456);

        assert_eq!(response.get_packet_id(), 456);
        assert_eq!(response.get_packet_type(), 10);
        assert_eq!(response.get_status_code(), 404);
        assert_eq!(response.get_error_message(), Some("Not found"));
        assert!(!response.is_success());
        assert!(response.is_error());
    }

    #[test]
    fn test_serialization_deserialization() {
        let original = GenericResponse::new(10, 200)
            .with_id(456)
            .with_data(vec![10, 20, 30])
            .with_error("Test error".to_string())
            .add_field("field1".to_string(), vec![40, 50])
            .add_field("field2".to_string(), vec![60]);

        let serialized = original.serialize().unwrap();
        let deserialized = GenericResponse::deserialize(&serialized).unwrap();

        assert_eq!(deserialized.get_packet_id(), 456);
        assert_eq!(deserialized.get_packet_type(), 10);
        assert_eq!(deserialized.get_status_code(), 200);
        assert_eq!(deserialized.get_data(), &[10, 20, 30]);
        assert_eq!(deserialized.get_error_message(), Some("Test error"));
        assert_eq!(deserialized.get_field("field1"), Some([40, 50].as_slice()));
        assert_eq!(deserialized.get_field("field2"), Some([60].as_slice()));
    }

    #[test]
    fn test_convenience_methods() {
        let success = GenericResponse::success(1);
        assert!(success.is_success());
        assert_eq!(success.get_status_code(), 200);

        let not_found = GenericResponse::not_found(2);
        assert!(not_found.is_error());
        assert_eq!(not_found.get_status_code(), 404);

        let internal_error = GenericResponse::internal_error(3);
        assert!(internal_error.is_error());
        assert_eq!(internal_error.get_status_code(), 500);

        let bad_request = GenericResponse::bad_request(4, "Invalid input".to_string());
        assert!(bad_request.is_error());
        assert_eq!(bad_request.get_status_code(), 400);
        assert_eq!(bad_request.get_error_message(), Some("Invalid input"));
    }

    #[test]
    fn test_validation() {
        let valid_response = GenericResponse::new(1, 200);
        assert!(valid_response.validate().is_ok());

        let invalid_response = GenericResponse::new(0, 200);
        assert!(invalid_response.validate().is_err());

        let error_without_message = GenericResponse::new(1, 500);
        assert!(error_without_message.validate().is_err());

        let error_with_message = GenericResponse::error(1, 500, "Error".to_string());
        assert!(error_with_message.validate().is_ok());
    }
}