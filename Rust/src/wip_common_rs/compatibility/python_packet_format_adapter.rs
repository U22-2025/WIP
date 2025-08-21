/*!
 * Python版パケット形式互換アダプター
 * Python版のパケット形式と完全互換性を提供
 */

use std::collections::HashMap;
use serde::{Deserialize, Serialize};
use crate::wip_common_rs::packet::core::format_base::FieldType;

/// Rustパケットフィールド定義
#[derive(Debug, Clone)]
pub struct PacketField {
    pub name: String,
    pub field_type: FieldType,
    pub bit_position: u32,
    pub bit_length: u32,
    pub description: String,
}

/// Python版パケット形式定義
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PythonPacketFormat {
    pub packet_size: u32,
    pub fields: Vec<PythonFieldDefinition>,
    pub version: String,
}

/// Python版フィールド定義
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PythonFieldDefinition {
    pub name: String,
    pub field_type: String,
    pub bit_position: u32,
    pub bit_length: u32,
    pub description: String,
    pub default_value: Option<serde_json::Value>,
}

/// Python版との互換性を提供するアダプター
pub struct PythonPacketFormatAdapter {
    format_map: HashMap<String, PythonPacketFormat>,
}

impl PythonPacketFormatAdapter {
    pub fn new() -> Self {
        let mut format_map = HashMap::new();
        
        // 基本パケット形式を登録
        format_map.insert("base".to_string(), Self::create_base_packet_format());
        format_map.insert("location".to_string(), Self::create_location_packet_format());
        format_map.insert("query".to_string(), Self::create_query_packet_format());
        format_map.insert("report".to_string(), Self::create_report_packet_format());
        
        Self { format_map }
    }

    /// 基本パケット形式定義
    fn create_base_packet_format() -> PythonPacketFormat {
        PythonPacketFormat {
            packet_size: 16,
            version: "1.0".to_string(),
            fields: vec![
                PythonFieldDefinition {
                    name: "version".to_string(),
                    field_type: "uint".to_string(),
                    bit_position: 0,
                    bit_length: 4,
                    description: "Packet version".to_string(),
                    default_value: Some(serde_json::Value::Number(serde_json::Number::from(1))),
                },
                PythonFieldDefinition {
                    name: "packet_id".to_string(),
                    field_type: "uint".to_string(),
                    bit_position: 4,
                    bit_length: 12,
                    description: "Packet identifier".to_string(),
                    default_value: None,
                },
                PythonFieldDefinition {
                    name: "packet_type".to_string(),
                    field_type: "uint".to_string(),
                    bit_position: 16,
                    bit_length: 3,
                    description: "Packet type".to_string(),
                    default_value: None,
                },
                PythonFieldDefinition {
                    name: "flags".to_string(),
                    field_type: "uint".to_string(),
                    bit_position: 19,
                    bit_length: 8,
                    description: "Packet flags".to_string(),
                    default_value: Some(serde_json::Value::Number(serde_json::Number::from(0))),
                },
                PythonFieldDefinition {
                    name: "day".to_string(),
                    field_type: "uint".to_string(),
                    bit_position: 27,
                    bit_length: 3,
                    description: "Day of week".to_string(),
                    default_value: None,
                },
                PythonFieldDefinition {
                    name: "timestamp".to_string(),
                    field_type: "uint".to_string(),
                    bit_position: 32,
                    bit_length: 64,
                    description: "Unix timestamp".to_string(),
                    default_value: None,
                },
                PythonFieldDefinition {
                    name: "area_code".to_string(),
                    field_type: "uint".to_string(),
                    bit_position: 96,
                    bit_length: 20,
                    description: "JMA area code".to_string(),
                    default_value: None,
                },
                PythonFieldDefinition {
                    name: "checksum".to_string(),
                    field_type: "uint".to_string(),
                    bit_position: 116,
                    bit_length: 12,
                    description: "Packet checksum".to_string(),
                    default_value: None,
                },
            ],
        }
    }

    /// ロケーションパケット形式定義
    fn create_location_packet_format() -> PythonPacketFormat {
        let mut base = Self::create_base_packet_format();
        base.fields.extend(vec![
            PythonFieldDefinition {
                name: "latitude".to_string(),
                field_type: "float".to_string(),
                bit_position: 128,
                bit_length: 32,
                description: "Latitude coordinate".to_string(),
                default_value: None,
            },
            PythonFieldDefinition {
                name: "longitude".to_string(),
                field_type: "float".to_string(),
                bit_position: 160,
                bit_length: 32,
                description: "Longitude coordinate".to_string(),
                default_value: None,
            },
        ]);
        base.packet_size = 24;
        base
    }

    /// クエリパケット形式定義
    fn create_query_packet_format() -> PythonPacketFormat {
        let mut base = Self::create_base_packet_format();
        base.fields.extend(vec![
            PythonFieldDefinition {
                name: "query_type".to_string(),
                field_type: "uint".to_string(),
                bit_position: 128,
                bit_length: 8,
                description: "Query type".to_string(),
                default_value: None,
            },
            PythonFieldDefinition {
                name: "weather_code".to_string(),
                field_type: "uint".to_string(),
                bit_position: 136,
                bit_length: 16,
                description: "Weather code".to_string(),
                default_value: None,
            },
        ]);
        base.packet_size = 20;
        base
    }

    /// レポートパケット形式定義
    fn create_report_packet_format() -> PythonPacketFormat {
        let mut base = Self::create_base_packet_format();
        base.fields.extend(vec![
            PythonFieldDefinition {
                name: "sensor_id".to_string(),
                field_type: "uint".to_string(),
                bit_position: 128,
                bit_length: 16,
                description: "Sensor identifier".to_string(),
                default_value: None,
            },
            PythonFieldDefinition {
                name: "temperature".to_string(),
                field_type: "int".to_string(),
                bit_position: 144,
                bit_length: 16,
                description: "Temperature in 0.1C".to_string(),
                default_value: None,
            },
            PythonFieldDefinition {
                name: "humidity".to_string(),
                field_type: "uint".to_string(),
                bit_position: 160,
                bit_length: 8,
                description: "Humidity percentage".to_string(),
                default_value: None,
            },
        ]);
        base.packet_size = 22;
        base
    }

    /// パケット形式を取得
    pub fn get_format(&self, packet_type: &str) -> Option<&PythonPacketFormat> {
        self.format_map.get(packet_type)
    }

    /// Python版フィールド定義をRust版に変換
    pub fn convert_to_rust_field(python_field: &PythonFieldDefinition) -> PacketField {
        let field_type = match python_field.field_type.as_str() {
            "uint" => FieldType::Int,
            "int" => FieldType::Int,
            "float" => FieldType::Float,
            "string" => FieldType::String,
            _ => FieldType::Int,
        };

        PacketField {
            name: python_field.name.clone(),
            field_type,
            bit_position: python_field.bit_position,
            bit_length: python_field.bit_length,
            description: python_field.description.clone(),
        }
    }

    /// Rust版フィールド定義をPython版に変換
    pub fn convert_from_rust_field(rust_field: &PacketField) -> PythonFieldDefinition {
        let field_type = match rust_field.field_type {
            FieldType::Int => "int",
            FieldType::Float => "float",
            FieldType::String => "string",
            FieldType::Bool => "bool",
        };

        PythonFieldDefinition {
            name: rust_field.name.clone(),
            field_type: field_type.to_string(),
            bit_position: rust_field.bit_position,
            bit_length: rust_field.bit_length,
            description: rust_field.description.clone(),
            default_value: None,
        }
    }

    /// パケット形式をJSONで出力（Python版互換）
    pub fn export_as_json(&self, packet_type: &str) -> Result<String, String> {
        match self.get_format(packet_type) {
            Some(format) => {
                serde_json::to_string_pretty(format)
                    .map_err(|e| format!("JSON serialization failed: {}", e))
            }
            None => Err(format!("Unknown packet type: {}", packet_type)),
        }
    }

    /// JSON形式からパケット形式を読み込み（Python版互換）
    pub fn import_from_json(&mut self, packet_type: String, json_data: &str) -> Result<(), String> {
        let format: PythonPacketFormat = serde_json::from_str(json_data)
            .map_err(|e| format!("JSON deserialization failed: {}", e))?;
        
        self.format_map.insert(packet_type, format);
        Ok(())
    }
}

impl Default for PythonPacketFormatAdapter {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_adapter_creation() {
        let adapter = PythonPacketFormatAdapter::new();
        assert!(adapter.get_format("base").is_some());
        assert!(adapter.get_format("location").is_some());
        assert!(adapter.get_format("query").is_some());
        assert!(adapter.get_format("report").is_some());
    }

    #[test]
    fn test_base_packet_format() {
        let adapter = PythonPacketFormatAdapter::new();
        let base_format = adapter.get_format("base").unwrap();
        
        assert_eq!(base_format.packet_size, 16);
        assert_eq!(base_format.fields.len(), 8);
        
        let version_field = &base_format.fields[0];
        assert_eq!(version_field.name, "version");
        assert_eq!(version_field.bit_position, 0);
        assert_eq!(version_field.bit_length, 4);
    }

    #[test]
    fn test_field_conversion() {
        let python_field = PythonFieldDefinition {
            name: "test_field".to_string(),
            field_type: "uint".to_string(),
            bit_position: 10,
            bit_length: 8,
            description: "Test field".to_string(),
            default_value: None,
        };

        let rust_field = PythonPacketFormatAdapter::convert_to_rust_field(&python_field);
        assert_eq!(rust_field.name, "test_field");
        assert_eq!(rust_field.bit_position, 10);
        assert_eq!(rust_field.bit_length, 8);

        let converted_back = PythonPacketFormatAdapter::convert_from_rust_field(&rust_field);
        assert_eq!(converted_back.name, python_field.name);
        assert_eq!(converted_back.field_type, python_field.field_type);
    }

    #[test]
    fn test_json_export_import() {
        let mut adapter = PythonPacketFormatAdapter::new();
        
        // JSONにエクスポート
        let json_str = adapter.export_as_json("base").unwrap();
        assert!(json_str.contains("packet_size"));
        assert!(json_str.contains("fields"));

        // 新しい形式をインポート
        let result = adapter.import_from_json("test_format".to_string(), &json_str);
        assert!(result.is_ok());
        assert!(adapter.get_format("test_format").is_some());
    }
}