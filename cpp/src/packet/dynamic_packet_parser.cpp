#include "wiplib/packet/dynamic_packet_parser.hpp"
#include <iostream>
#include <iomanip>
#include <sstream>
#include <algorithm>
#include <cstring>
#include <cmath>

namespace wiplib::packet {

// DynamicPacketResult実装
std::optional<DynamicFieldValue> DynamicPacketResult::get_field(const std::string& field_name) const {
    for (const auto& field : fields) {
        if (field.field_name == field_name) {
            return field;
        }
    }
    return std::nullopt;
}

std::optional<DynamicFieldValue> DynamicPacketResult::get_extended_field(uint8_t field_key) const {
    // 拡張フィールドキーは名前に含まれているとして検索
    for (const auto& field : extended_fields) {
        // キーをフィールド名から推測（実装を簡略化）
        if (field.field_name.find(std::to_string(field_key)) != std::string::npos) {
            return field;
        }
    }
    return std::nullopt;
}

std::unordered_map<std::string, DynamicFieldValue> DynamicPacketResult::get_all_fields() const {
    std::unordered_map<std::string, DynamicFieldValue> result;
    
    for (const auto& field : fields) {
        result[field.field_name] = field;
    }
    
    for (const auto& field : extended_fields) {
        result[field.field_name] = field;
    }
    
    return result;
}

// DynamicPacketParser実装
DynamicPacketParser::DynamicPacketParser(const std::string& spec_directory) 
    : spec_directory_(spec_directory) {
    
    // デフォルトハンドラーを設定
    custom_parsers_[FieldType::StringList] = [this](std::span<const uint8_t> data) -> DynamicFieldValue {
        DynamicFieldValue value("string_list", FieldType::StringList);
        value.string_value = std::string(reinterpret_cast<const char*>(data.data()), data.size());
        return value;
    };
    
    custom_parsers_[FieldType::Binary] = [this](std::span<const uint8_t> data) -> DynamicFieldValue {
        DynamicFieldValue value("binary", FieldType::Binary);
        value.binary_value.assign(data.begin(), data.end());
        return value;
    };
    
    custom_parsers_[FieldType::Float32] = [this](std::span<const uint8_t> data) -> DynamicFieldValue {
        DynamicFieldValue value("float32", FieldType::Float32);
        if (data.size() >= 4) {
            float f_value;
            std::memcpy(&f_value, data.data(), sizeof(float));
            value.float_value = f_value;
        }
        return value;
    };
    
    custom_parsers_[FieldType::Json] = [this](std::span<const uint8_t> data) -> DynamicFieldValue {
        DynamicFieldValue value("json", FieldType::Json);
        value.string_value = std::string(reinterpret_cast<const char*>(data.data()), data.size());
        return value;
    };
}

bool DynamicPacketParser::load_packet_spec(const std::string& packet_type) {
    std::string file_path = get_spec_file_path(packet_type);
    
    std::optional<PacketSpecification> spec;
    if (packet_type == "request") {
        spec = FormatParser::load_request_spec(file_path);
    } else if (packet_type == "response") {
        spec = FormatParser::load_response_spec(file_path);
    } else if (packet_type == "extended") {
        spec = FormatParser::load_extended_spec(file_path);
    } else {
        return false;
    }
    
    if (spec) {
        loaded_specs_[packet_type] = *spec;
        return true;
    }
    
    return false;
}

DynamicPacketResult DynamicPacketParser::parse_packet(std::span<const uint8_t> data, const std::string& packet_type) const {
    DynamicPacketResult result;
    result.packet_type = packet_type;
    
    total_parsed_packets_++;
    
    if (!ensure_spec_loaded(packet_type)) {
        record_parsing_error("Specification not loaded for packet type: " + packet_type);
        result.error_message = "Specification not loaded";
        return result;
    }
    
    const auto& spec = loaded_specs_.at(packet_type);
    
    try {
        // 基本フィールドを解析
        for (const auto& field_def : spec.fields) {
            if (data.size() * 8 < field_def.bit_offset + field_def.bit_length) {
                record_parsing_error("Insufficient data for field: " + field_def.name);
                continue;
            }
            
            auto field_value = parse_field_value(field_def, data);
            result.fields.push_back(field_value);
        }
        
        // 拡張フィールドを解析（拡張仕様の場合）
        if (packet_type == "extended") {
            for (const auto& ext_field_def : spec.extended_fields) {
                // 実際の実装では、拡張フィールドのデータ位置を正確に計算する必要がある
                // ここでは簡略化
                auto field_value = parse_extended_field_value(ext_field_def, data);
                result.extended_fields.push_back(field_value);
            }
        }
        
        result.is_valid = true;
        
    } catch (const std::exception& e) {
        record_parsing_error("Exception during parsing: " + std::string(e.what()));
        result.error_message = e.what();
        result.is_valid = false;
    }
    
    return result;
}

std::optional<DynamicFieldValue> DynamicPacketParser::parse_extended_field(std::span<const uint8_t> data, uint8_t field_key) const {
    if (!ensure_spec_loaded("extended")) {
        return std::nullopt;
    }
    
    const auto& spec = loaded_specs_.at("extended");
    auto ext_field = FormatParser::find_extended_field_by_key(spec, field_key);
    
    if (!ext_field) {
        return std::nullopt;
    }
    
    return parse_extended_field_value(*ext_field, data);
}

std::vector<uint8_t> DynamicPacketParser::build_packet(const std::string& packet_type, 
                                                       const std::unordered_map<std::string, DynamicFieldValue>& field_values) const {
    total_built_packets_++;
    
    if (!ensure_spec_loaded(packet_type)) {
        return {};
    }
    
    const auto& spec = loaded_specs_.at(packet_type);
    
    // パケットサイズを計算
    size_t packet_size = spec.total_size_bytes > 0 ? spec.total_size_bytes : 64; // デフォルトサイズ
    std::vector<uint8_t> packet_data(packet_size, 0);
    
    // フィールド値を書き込み
    for (const auto& field_def : spec.fields) {
        auto it = field_values.find(field_def.name);
        if (it != field_values.end()) {
            write_field_value(field_def, it->second, packet_data);
        } else if (field_def.default_value != 0) {
            // デフォルト値を設定
            DynamicFieldValue default_val(field_def.name, FieldType::UInt);
            default_val.uint_value = field_def.default_value;
            write_field_value(field_def, default_val, packet_data);
        }
    }
    
    return packet_data;
}

bool DynamicPacketParser::validate_fields(const std::string& packet_type, 
                                         const std::unordered_map<std::string, DynamicFieldValue>& field_values) const {
    if (!ensure_spec_loaded(packet_type)) {
        record_validation_error("Specification not loaded for validation");
        return false;
    }
    
    const auto& spec = loaded_specs_.at(packet_type);
    
    // 必須フィールドチェック
    for (const auto& field_def : spec.fields) {
        if (!field_def.is_optional) {
            auto it = field_values.find(field_def.name);
            if (it == field_values.end()) {
                record_validation_error("Required field missing: " + field_def.name);
                return false;
            }
        }
    }
    
    // フィールド値の範囲チェック
    for (const auto& [field_name, field_value] : field_values) {
        // 対応するフィールド定義を検索
        auto field_def = FormatParser::find_field(spec, field_name);
        if (field_def) {
            // ビット長に基づく値範囲チェック
            if (field_def->type == FieldDefinition::FieldType::UInt) {
                uint64_t max_value = (1ULL << field_def->bit_length) - 1;
                if (field_value.uint_value > max_value) {
                    record_validation_error("Field value out of range: " + field_name);
                    return false;
                }
            }
        }
    }
    
    return true;
}

std::string DynamicPacketParser::debug_dump(const DynamicPacketResult& result) const {
    std::ostringstream oss;
    
    oss << "=== Packet Analysis Result ===" << std::endl;
    oss << "Packet Type: " << result.packet_type << std::endl;
    oss << "Valid: " << (result.is_valid ? "Yes" : "No") << std::endl;
    
    if (!result.error_message.empty()) {
        oss << "Error: " << result.error_message << std::endl;
    }
    
    oss << "\nBasic Fields (" << result.fields.size() << "):" << std::endl;
    for (const auto& field : result.fields) {
        oss << "  " << field.field_name << " = " 
            << dynamic_utils::field_value_to_string(field) << std::endl;
    }
    
    if (!result.extended_fields.empty()) {
        oss << "\nExtended Fields (" << result.extended_fields.size() << "):" << std::endl;
        for (const auto& field : result.extended_fields) {
            oss << "  " << field.field_name << " = " 
                << dynamic_utils::field_value_to_string(field) << std::endl;
        }
    }
    
    oss << "===========================" << std::endl;
    
    return oss.str();
}

void DynamicPacketParser::set_custom_field_handler(FieldType field_type,
                                                   std::function<DynamicFieldValue(std::span<const uint8_t>)> parser_func,
                                                   std::function<std::vector<uint8_t>(const DynamicFieldValue&)> builder_func) {
    custom_parsers_[field_type] = std::move(parser_func);
    custom_builders_[field_type] = std::move(builder_func);
}

std::unordered_map<std::string, uint64_t> DynamicPacketParser::get_performance_stats() const {
    return {
        {"total_parsed_packets", total_parsed_packets_.load()},
        {"total_built_packets", total_built_packets_.load()},
        {"parsing_errors", parsing_errors_.load()},
        {"validation_errors", validation_errors_.load()}
    };
}

void DynamicPacketParser::reset_performance_stats() {
    total_parsed_packets_ = 0;
    total_built_packets_ = 0;
    parsing_errors_ = 0;
    validation_errors_ = 0;
}

// プライベートメソッド実装
DynamicFieldValue DynamicPacketParser::parse_field_value(const FieldDefinition& field_def, std::span<const uint8_t> data) const {
    DynamicFieldValue value(field_def.name, FieldType::UInt); // 基本フィールドはUIntとして扱う
    
    uint64_t extracted_value = extract_bits(data, field_def.bit_offset, field_def.bit_length);
    
    switch (field_def.type) {
        case FieldDefinition::FieldType::UInt:
        case FieldDefinition::FieldType::Enum:
        case FieldDefinition::FieldType::Flags:
        case FieldDefinition::FieldType::Timestamp:
        case FieldDefinition::FieldType::Checksum:
            value.uint_value = extracted_value;
            break;
            
        case FieldDefinition::FieldType::Int:
            // 符号拡張処理
            if (field_def.bit_length < 64 && (extracted_value & (1ULL << (field_def.bit_length - 1)))) {
                // 負の値の場合
                value.int_value = static_cast<int64_t>(extracted_value | (~((1ULL << field_def.bit_length) - 1)));
            } else {
                value.int_value = static_cast<int64_t>(extracted_value);
            }
            break;
            
        case FieldDefinition::FieldType::Reserved:
            value.uint_value = extracted_value;
            break;
    }
    
    return value;
}

DynamicFieldValue DynamicPacketParser::parse_extended_field_value(const ExtendedFieldDefinition& field_def, std::span<const uint8_t> data) const {
    DynamicFieldValue value(field_def.name, field_def.type);
    
    // カスタムパーサーがある場合はそれを使用
    auto parser_it = custom_parsers_.find(field_def.type);
    if (parser_it != custom_parsers_.end()) {
        return parser_it->second(data);
    }
    
    // デフォルト処理
    switch (field_def.type) {
        case FieldType::Coordinate:
            if (data.size() >= 8) {
                float lat, lon;
                std::memcpy(&lat, data.data(), sizeof(float));
                std::memcpy(&lon, data.data() + 4, sizeof(float));
                value.string_value = std::to_string(lat) + "," + std::to_string(lon);
            }
            break;
            
        case FieldType::Source:
            if (data.size() >= 6) {
                uint8_t source_id = data[0];
                uint32_t timestamp;
                uint8_t quality = data[5];
                std::memcpy(&timestamp, data.data() + 1, sizeof(uint32_t));
                value.string_value = "source:" + std::to_string(source_id) + 
                                   ",ts:" + std::to_string(timestamp) + 
                                   ",q:" + std::to_string(quality);
            }
            break;
            
        default:
            value.binary_value.assign(data.begin(), data.end());
            break;
    }
    
    return value;
}

void DynamicPacketParser::write_field_value(const FieldDefinition& field_def, const DynamicFieldValue& value, std::span<uint8_t> data) const {
    uint64_t write_value = 0;
    
    switch (field_def.type) {
        case FieldDefinition::FieldType::UInt:
        case FieldDefinition::FieldType::Enum:
        case FieldDefinition::FieldType::Flags:
        case FieldDefinition::FieldType::Timestamp:
        case FieldDefinition::FieldType::Checksum:
        case FieldDefinition::FieldType::Reserved:
            write_value = value.uint_value;
            break;
            
        case FieldDefinition::FieldType::Int:
            write_value = static_cast<uint64_t>(value.int_value);
            break;
    }
    
    insert_bits(data, field_def.bit_offset, field_def.bit_length, write_value);
}

std::vector<uint8_t> DynamicPacketParser::build_extended_field_value(const ExtendedFieldDefinition& field_def, const DynamicFieldValue& value) const {
    // カスタムビルダーがある場合はそれを使用
    auto builder_it = custom_builders_.find(field_def.type);
    if (builder_it != custom_builders_.end()) {
        return builder_it->second(value);
    }
    
    // デフォルト処理
    return value.binary_value;
}

uint64_t DynamicPacketParser::extract_bits(std::span<const uint8_t> data, uint32_t bit_offset, uint8_t bit_length) const {
    uint64_t result = 0;
    
    for (uint8_t i = 0; i < bit_length; ++i) {
        uint32_t current_bit = bit_offset + i;
        uint32_t byte_index = current_bit / 8;
        uint8_t bit_index = current_bit % 8;
        
        if (byte_index < data.size()) {
            uint8_t bit_value = (data[byte_index] >> bit_index) & 1;
            result |= (static_cast<uint64_t>(bit_value) << i);
        }
    }
    
    return result;
}

void DynamicPacketParser::insert_bits(std::span<uint8_t> data, uint32_t bit_offset, uint8_t bit_length, uint64_t value) const {
    for (uint8_t i = 0; i < bit_length; ++i) {
        uint32_t current_bit = bit_offset + i;
        uint32_t byte_index = current_bit / 8;
        uint8_t bit_index = current_bit % 8;
        
        if (byte_index < data.size()) {
            uint8_t bit_value = (value >> i) & 1;
            if (bit_value) {
                data[byte_index] |= (1 << bit_index);
            } else {
                data[byte_index] &= ~(1 << bit_index);
            }
        }
    }
}

std::string DynamicPacketParser::get_spec_file_path(const std::string& packet_type) const {
    if (packet_type == "request") {
        return spec_directory_ + "request_fields.json";
    } else if (packet_type == "response") {
        return spec_directory_ + "response_fields.json";
    } else if (packet_type == "extended") {
        return spec_directory_ + "extended_fields.json";
    }
    return "";
}

bool DynamicPacketParser::ensure_spec_loaded(const std::string& packet_type) const {
    auto it = loaded_specs_.find(packet_type);
    if (it == loaded_specs_.end()) {
        // 仕様が読み込まれていない場合、動的に読み込みを試行
        const_cast<DynamicPacketParser*>(this)->load_packet_spec(packet_type);
        return loaded_specs_.find(packet_type) != loaded_specs_.end();
    }
    return true;
}

void DynamicPacketParser::record_parsing_error(const std::string& error_message) const {
    parsing_errors_++;
    // デバッグ出力（実際の実装ではロガーを使用）
    std::cerr << "Parsing error: " << error_message << std::endl;
}

void DynamicPacketParser::record_validation_error(const std::string& error_message) const {
    validation_errors_++;
    // デバッグ出力（実際の実装ではロガーを使用）
    std::cerr << "Validation error: " << error_message << std::endl;
}

// ファクトリー実装
std::unique_ptr<DynamicPacketParser> DynamicPacketParserFactory::create_standard() {
    return std::make_unique<DynamicPacketParser>();
}

std::unique_ptr<DynamicPacketParser> DynamicPacketParserFactory::create_fast() {
    auto parser = std::make_unique<DynamicPacketParser>();
    // 高速化設定を追加
    return parser;
}

std::unique_ptr<DynamicPacketParser> DynamicPacketParserFactory::create_debug() {
    auto parser = std::make_unique<DynamicPacketParser>();
    // デバッグ設定を追加
    return parser;
}

std::unique_ptr<DynamicPacketParser> DynamicPacketParserFactory::create_with_specs(const std::string& spec_directory) {
    return std::make_unique<DynamicPacketParser>(spec_directory);
}

// ユーティリティ実装
namespace dynamic_utils {
    std::string field_value_to_string(const DynamicFieldValue& value) {
        std::ostringstream oss;
        
        switch (value.field_type) {
            case FieldType::UInt:
            case FieldType::Enum:
            case FieldType::Flags:
            case FieldType::Timestamp:
            case FieldType::Checksum:
                oss << value.uint_value;
                break;
                
            case FieldType::Int:
                oss << value.int_value;
                break;
                
            case FieldType::Float32:
                oss << value.float_value;
                break;
                
            case FieldType::StringList:
            case FieldType::Json:
                oss << "\"" << value.string_value << "\"";
                break;
                
            case FieldType::Coordinate:
            case FieldType::Source:
                oss << value.string_value;
                break;
                
            case FieldType::Binary:
                oss << "binary[" << value.binary_value.size() << " bytes]";
                break;
                
            default:
                oss << "unknown";
                break;
        }
        
        return oss.str();
    }
    
    DynamicFieldValue string_to_field_value(const std::string& str_value, FieldType field_type, const std::string& field_name) {
        DynamicFieldValue value(field_name, field_type);
        
        switch (field_type) {
            case FieldType::UInt:
            case FieldType::Enum:
            case FieldType::Flags:
            case FieldType::Timestamp:
            case FieldType::Checksum:
                value.uint_value = std::stoull(str_value);
                break;
                
            case FieldType::Int:
                value.int_value = std::stoll(str_value);
                break;
                
            case FieldType::Float32:
                value.float_value = std::stof(str_value);
                break;
                
            case FieldType::StringList:
            case FieldType::Json:
            case FieldType::Coordinate:
            case FieldType::Source:
                value.string_value = str_value;
                break;
                
            case FieldType::Binary:
                // ヘキサ文字列として解釈
                for (size_t i = 0; i < str_value.length(); i += 2) {
                    std::string byte_str = str_value.substr(i, 2);
                    uint8_t byte_val = static_cast<uint8_t>(std::stoul(byte_str, nullptr, 16));
                    value.binary_value.push_back(byte_val);
                }
                break;
        }
        
        return value;
    }
    
    std::string hex_dump(std::span<const uint8_t> data, size_t bytes_per_line) {
        std::ostringstream oss;
        
        for (size_t i = 0; i < data.size(); i += bytes_per_line) {
            oss << std::setfill('0') << std::setw(8) << std::hex << i << ": ";
            
            // ヘキサダンプ
            for (size_t j = 0; j < bytes_per_line; ++j) {
                if (i + j < data.size()) {
                    oss << std::setfill('0') << std::setw(2) << std::hex 
                        << static_cast<unsigned>(data[i + j]) << " ";
                } else {
                    oss << "   ";
                }
            }
            
            oss << " ";
            
            // ASCII表示
            for (size_t j = 0; j < bytes_per_line && i + j < data.size(); ++j) {
                char c = static_cast<char>(data[i + j]);
                oss << (std::isprint(c) ? c : '.');
            }
            
            oss << std::endl;
        }
        
        return oss.str();
    }
    
    std::string result_to_json(const DynamicPacketResult& result) {
        std::ostringstream oss;
        oss << "{";
        oss << "\"packet_type\":\"" << result.packet_type << "\",";
        oss << "\"is_valid\":" << (result.is_valid ? "true" : "false") << ",";
        oss << "\"fields\":[";
        
        for (size_t i = 0; i < result.fields.size(); ++i) {
            if (i > 0) oss << ",";
            const auto& field = result.fields[i];
            oss << "{\"name\":\"" << field.field_name << "\",";
            oss << "\"value\":\"" << field_value_to_string(field) << "\"}";
        }
        
        oss << "]";
        oss << "}";
        
        return oss.str();
    }
    
    std::optional<DynamicPacketResult> json_to_result(const std::string& json_str) {
        // 簡易JSON解析（実際の実装では専用ライブラリを使用）
        DynamicPacketResult result;
        // 解析処理は省略
        return result;
    }
}

} // namespace wiplib::packet