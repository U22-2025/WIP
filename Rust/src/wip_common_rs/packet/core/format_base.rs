/// パケットフォーマットの基盤実装
/// Python版 format_base.py の機能をRustで実装

use super::bit_utils::{BitField, PacketFields, bytes_to_u128_le, u128_to_bytes_le};
use super::checksum::{calc_checksum12, verify_checksum12};
use super::exceptions::{WipResult, WipPacketError, PacketParseError, ChecksumError};
use serde_json::Value;
use std::collections::HashMap;

/// パケットフォーマットの基本trait
pub trait PacketFormat: Sized {
    /// パケットをバイト列に変換
    fn to_bytes(&self) -> Vec<u8>;
    
    /// バイト列からパケットを構築
    fn from_bytes(data: &[u8]) -> WipResult<Self>;
    
    /// パケットサイズを取得
    fn packet_size() -> usize;
    
    /// パケット型を取得
    fn packet_type() -> u8;
    
    /// バージョンを取得
    fn version(&self) -> u8;
    
    /// パケットIDを取得
    fn packet_id(&self) -> u16;
    
    /// チェックサムを計算（Python版互換）
    fn calculate_checksum(&self) -> u16 {
        let bytes = self.to_bytes();
        if let Some(checksum_field) = Self::get_checksum_field() {
            // Python版と同じ処理：リトルエンディアンでビット列に変換してからチェックサム部分を0にして計算
            let mut bitstr = 0u128;
            for (i, &byte) in bytes.iter().enumerate() {
                bitstr |= (byte as u128) << (i * 8);
            }
            
            let checksum_mask = ((1u128 << checksum_field.length) - 1) << checksum_field.start;
            let bitstr_without_checksum = bitstr & !checksum_mask;
            
            let mut data_for_checksum = vec![0u8; bytes.len()];
            for i in 0..data_for_checksum.len() {
                data_for_checksum[i] = ((bitstr_without_checksum >> (i * 8)) & 0xFF) as u8;
            }
            
            // 最小パケットサイズまで0パディング
            if data_for_checksum.len() < 16 {
                data_for_checksum.resize(16, 0);
            }
            
            calc_checksum12(&data_for_checksum)
        } else {
            calc_checksum12(&bytes)
        }
    }
    
    /// チェックサムを検証（Python版互換）
    fn verify_checksum(&self) -> bool {
        let bytes = self.to_bytes();
        if let Some(checksum_field) = Self::get_checksum_field() {
            verify_checksum12(&bytes, checksum_field.start, checksum_field.length)
        } else {
            false
        }
    }
    
    /// フィールド定義を取得
    fn get_field_definitions() -> &'static PacketFields;
    
    /// チェックサムフィールドを取得
    fn get_checksum_field() -> Option<&'static BitField>;
    
    /// バイト配列内のチェックサム部分をクリア
    fn clear_checksum_in_bytes(&self, bytes: &mut [u8], checksum_field: &BitField) {
        if bytes.len() >= (checksum_field.end() + 7) / 8 {
            let mut data = bytes_to_u128_le(bytes);
            checksum_field.set(&mut data, 0);
            u128_to_bytes_le(data, bytes);
        }
    }
}

/// パケットフィールド定義ビルダー
pub struct PacketDefinitionBuilder {
    fields: PacketFields,
    field_specs: HashMap<String, FieldSpec>,
}

/// フィールド仕様
#[derive(Debug, Clone)]
pub struct FieldSpec {
    pub length: usize,
    pub field_type: FieldType,
    pub required: bool,
    pub default: Option<u64>,
    pub min: Option<u64>,
    pub max: Option<u64>,
}

/// フィールド型
#[derive(Debug, Clone, PartialEq)]
pub enum FieldType {
    Int,
    String,
    Float,
    Bool,
}

impl PacketDefinitionBuilder {
    /// 新しいビルダーを作成
    pub fn new() -> Self {
        Self {
            fields: PacketFields::new(),
            field_specs: HashMap::new(),
        }
    }
    
    /// フィールドを追加
    pub fn add_field(&mut self, name: &str, spec: FieldSpec) -> &mut Self {
        self.fields.add_field(name, spec.length);
        self.field_specs.insert(name.to_string(), spec);
        self
    }
    
    /// 整数フィールドを追加
    pub fn add_int_field(&mut self, name: &str, length: usize) -> &mut Self {
        let spec = FieldSpec {
            length,
            field_type: FieldType::Int,
            required: true,
            default: None,
            min: None,
            max: Some((1u64 << length) - 1),
        };
        self.add_field(name, spec)
    }
    
    /// 文字列フィールドを追加
    pub fn add_string_field(&mut self, name: &str, length: usize) -> &mut Self {
        let spec = FieldSpec {
            length,
            field_type: FieldType::String,
            required: true,
            default: None,
            min: None,
            max: None,
        };
        self.add_field(name, spec)
    }
    
    /// 定義を構築
    pub fn build(self) -> (PacketFields, HashMap<String, FieldSpec>) {
        (self.fields, self.field_specs)
    }
}

impl Default for PacketDefinitionBuilder {
    fn default() -> Self {
        Self::new()
    }
}

/// JSONからパケット仕様を読み込む
pub struct JsonPacketSpecLoader;

impl JsonPacketSpecLoader {
    /// JSONファイルからフィールド定義を読み込み
    pub fn load_from_json(json_str: &str) -> WipResult<(PacketFields, HashMap<String, FieldSpec>)> {
        let json: Value = serde_json::from_str(json_str)
            .map_err(|e| WipPacketError::Parse(PacketParseError::UnexpectedFormat(
                format!("JSON解析エラー: {}", e)
            )))?;
        
        let mut builder = PacketDefinitionBuilder::new();
        
        if let Value::Object(fields) = json {
            for (field_name, field_def) in fields {
                let spec = Self::parse_field_spec(&field_def)?;
                builder.add_field(&field_name, spec);
            }
        }
        
        Ok(builder.build())
    }
    
    /// フィールド仕様を解析
    fn parse_field_spec(field_def: &Value) -> WipResult<FieldSpec> {
        let length = field_def["length"].as_u64()
            .ok_or_else(|| WipPacketError::Parse(PacketParseError::UnexpectedFormat(
                "length フィールドが見つかりません".to_string()
            )))? as usize;
        
        let type_str = field_def["type"].as_str()
            .ok_or_else(|| WipPacketError::Parse(PacketParseError::UnexpectedFormat(
                "type フィールドが見つかりません".to_string()
            )))?;
        
        let field_type = match type_str {
            "int" => FieldType::Int,
            "str" => FieldType::String,
            "float" => FieldType::Float,
            "bool" => FieldType::Bool,
            _ => return Err(WipPacketError::Parse(PacketParseError::UnexpectedFormat(
                format!("不明なフィールド型: {}", type_str)
            ))),
        };
        
        Ok(FieldSpec {
            length,
            field_type,
            required: field_def["required"].as_bool().unwrap_or(true),
            default: field_def["default"].as_u64(),
            min: field_def["min"].as_u64(),
            max: field_def["max"].as_u64(),
        })
    }
}

/// パケット検証器
pub struct PacketValidator {
    field_specs: HashMap<String, FieldSpec>,
}

impl PacketValidator {
    /// 新しい検証器を作成
    pub fn new(field_specs: HashMap<String, FieldSpec>) -> Self {
        Self { field_specs }
    }
    
    /// フィールド値を検証
    pub fn validate_field(&self, field_name: &str, value: u64) -> WipResult<()> {
        if let Some(spec) = self.field_specs.get(field_name) {
            // 最大値チェック
            if let Some(max) = spec.max {
                if value > max {
                    return Err(WipPacketError::Parse(PacketParseError::field_out_of_range(
                        field_name, value as u128, max as u128
                    )));
                }
            }
            
            // 最小値チェック
            if let Some(min) = spec.min {
                if value < min {
                    return Err(WipPacketError::Parse(PacketParseError::field_out_of_range(
                        field_name, value as u128, min as u128
                    )));
                }
            }
            
            Ok(())
        } else {
            Err(WipPacketError::Field(
                super::exceptions::InvalidFieldError::UnknownField(field_name.to_string())
            ))
        }
    }
    
    /// 必須フィールドの存在をチェック
    pub fn validate_required_fields(&self, present_fields: &[&str]) -> WipResult<()> {
        for (field_name, spec) in &self.field_specs {
            if spec.required && !present_fields.contains(&field_name.as_str()) {
                return Err(WipPacketError::Field(
                    super::exceptions::InvalidFieldError::RequiredFieldEmpty(field_name.clone())
                ));
            }
        }
        Ok(())
    }
}

/// 自動チェックサム機能付きパケット
pub trait AutoChecksumPacket: PacketFormat {
    /// チェックサムを自動設定してバイト列に変換（Python版互換）
    fn to_bytes_with_checksum(&self) -> Vec<u8> {
        let mut bytes = self.to_bytes();
        
        if let Some(checksum_field) = Self::get_checksum_field() {
            // Python版と同じ処理でチェックサムを埋め込み
            super::checksum::embed_checksum12_at(&mut bytes, checksum_field.start, checksum_field.length);
        }
        
        bytes
    }
    
    /// チェックサム検証付きでバイト列から構築
    fn from_bytes_with_verification(data: &[u8]) -> WipResult<Self> {
        let packet = Self::from_bytes(data)?;
        
        if !packet.verify_checksum() {
            let expected = packet.calculate_checksum();
            let actual = if let Some(checksum_field) = Self::get_checksum_field() {
                let data_value = bytes_to_u128_le(data);
                checksum_field.extract(data_value) as u16
            } else {
                0
            };
            
            return Err(WipPacketError::Checksum(ChecksumError::mismatch(expected, actual)));
        }
        
        Ok(packet)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_packet_definition_builder() {
        let mut builder = PacketDefinitionBuilder::new();
        builder.add_int_field("version", 4);
        builder.add_int_field("packet_id", 12);
        builder.add_string_field("data", 32);
        
        let (fields, specs) = builder.build();
        
        assert_eq!(fields.total_bits(), 48); // 4 + 12 + 32
        assert_eq!(specs.len(), 3);
        
        let version_spec = &specs["version"];
        assert_eq!(version_spec.field_type, FieldType::Int);
        assert_eq!(version_spec.length, 4);
    }

    #[test]
    fn test_json_spec_loader() {
        let json = r#"{
            "version": {"length": 4, "type": "int"},
            "packet_id": {"length": 12, "type": "int"},
            "type": {"length": 3, "type": "int"}
        }"#;
        
        let (fields, specs) = JsonPacketSpecLoader::load_from_json(json).unwrap();
        
        assert_eq!(fields.total_bits(), 19); // 4 + 12 + 3
        assert_eq!(specs.len(), 3);
        
        assert!(specs.contains_key("version"));
        assert!(specs.contains_key("packet_id"));
        assert!(specs.contains_key("type"));
    }

    #[test]
    fn test_packet_validator() {
        let mut specs = HashMap::new();
        specs.insert("version".to_string(), FieldSpec {
            length: 4,
            field_type: FieldType::Int,
            required: true,
            default: None,
            min: Some(1),
            max: Some(15),
        });
        
        let validator = PacketValidator::new(specs);
        
        // 有効な値
        assert!(validator.validate_field("version", 5).is_ok());
        
        // 範囲外の値
        assert!(validator.validate_field("version", 16).is_err());
        assert!(validator.validate_field("version", 0).is_err());
        
        // 不明なフィールド
        assert!(validator.validate_field("unknown", 1).is_err());
    }

    #[test]
    fn test_required_fields_validation() {
        let mut specs = HashMap::new();
        specs.insert("version".to_string(), FieldSpec {
            length: 4,
            field_type: FieldType::Int,
            required: true,
            default: None,
            min: None,
            max: None,
        });
        specs.insert("optional_field".to_string(), FieldSpec {
            length: 8,
            field_type: FieldType::Int,
            required: false,
            default: None,
            min: None,
            max: None,
        });
        
        let validator = PacketValidator::new(specs);
        
        // 必須フィールドが存在
        assert!(validator.validate_required_fields(&["version", "optional_field"]).is_ok());
        assert!(validator.validate_required_fields(&["version"]).is_ok());
        
        // 必須フィールドが不足
        assert!(validator.validate_required_fields(&["optional_field"]).is_err());
        assert!(validator.validate_required_fields(&[]).is_err());
    }
}