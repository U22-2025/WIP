#include "wiplib/packet/format_base.hpp"
#include "wiplib/packet/bit_utils.hpp"
#include "wiplib/packet/checksum.hpp"
#include <algorithm>

namespace wiplib::packet {

void PacketFormatBase::add_field(const FieldDefinition& field) {
    fields_[field.name] = field;
    
    // パケットサイズを更新
    size_t field_end = (field.bit_offset + field.bit_length + 7) / 8;
    packet_size_ = std::max(packet_size_, field_end);
}

uint64_t PacketFormatBase::get_field_value(const std::string& field_name, std::span<const uint8_t> data) const {
    auto it = fields_.find(field_name);
    if (it == fields_.end()) {
        throw InvalidFieldError(field_name, "Field not found");
    }
    
    const auto& field = it->second;
    return extract_bits(data, field.bit_offset, field.bit_length);
}

void PacketFormatBase::set_field_value(const std::string& field_name, uint64_t value, std::span<uint8_t> data) const {
    auto it = fields_.find(field_name);
    if (it == fields_.end()) {
        throw InvalidFieldError(field_name, "Field not found");
    }
    
    const auto& field = it->second;
    
    // 値の範囲チェック
    uint64_t max_value = (1ULL << field.bit_length) - 1;
    if (field.type != "int" && value > max_value) {
        throw InvalidFieldError(field_name, "Value out of range");
    }
    
    set_bits(data, field.bit_offset, field.bit_length, value);
}

bool PacketFormatBase::validate(std::span<const uint8_t> data) const {
    if (data.size() < packet_size_) {
        return false;
    }
    
    // 基本的な検証
    for (const auto& [name, field] : fields_) {
        if (field.type == "checksum") {
            continue; // チェックサムは後で検証
        }
        
        try {
            uint64_t value = get_field_value(name, data);
            
            // 型別検証
            if (field.type == "uint") {
                uint64_t max_value = (1ULL << field.bit_length) - 1;
                if (value > max_value) {
                    return false;
                }
            } else if (field.type == "reserved") {
                if (value != 0) {
                    return false; // 予約フィールドは0である必要
                }
            }
        } catch (const std::exception&) {
            return false;
        }
    }
    
    return true;
}

uint16_t PacketFormatBase::calculate_checksum(std::span<const uint8_t> data) const {
    // チェックサムフィールドを除いたデータでチェックサム計算
    std::vector<uint8_t> checksum_data(data.begin(), data.end());
    
    // チェックサムフィールドを0でクリア
    auto checksum_field = fields_.find("checksum");
    if (checksum_field != fields_.end()) {
        set_bits(checksum_data, checksum_field->second.bit_offset, 
                checksum_field->second.bit_length, 0);
    }
    
    return calc_checksum12(checksum_data);
}

size_t PacketFormatBase::get_packet_size() const {
    return packet_size_;
}

const FieldDefinition* PacketFormatBase::get_field_definition(const std::string& field_name) const {
    auto it = fields_.find(field_name);
    return (it != fields_.end()) ? &it->second : nullptr;
}

RequestPacketFormat::RequestPacketFormat() {
    // 基本ヘッダーフィールドを定義
    add_field({"version", 0, 4, "uint", "Protocol version"});
    add_field({"packet_id", 4, 12, "uint", "Unique packet identifier"});
    add_field({"type", 16, 3, "enum", "Packet type identifier"});
    add_field({"flags", 19, 8, "flags", "Control flags"});
    add_field({"day", 27, 3, "uint", "Day offset (0-7)"});
    add_field({"reserved1", 30, 2, "reserved", "Reserved bits"});
    add_field({"timestamp", 32, 64, "timestamp", "Unix timestamp"});
    add_field({"area_code", 96, 20, "uint", "Geographic area code"});
    add_field({"checksum", 116, 12, "checksum", "12-bit packet checksum"});
}

bool RequestPacketFormat::validate(std::span<const uint8_t> data) const {
    if (!PacketFormatBase::validate(data)) {
        return false;
    }
    
    // リクエスト固有の検証
    uint64_t version = get_field_value("version", data);
    if (version != 1) {
        return false; // 現在はバージョン1のみサポート
    }
    
    return true;
}

ResponsePacketFormat::ResponsePacketFormat() {
    // 基本ヘッダーフィールドを定義
    add_field({"version", 0, 4, "uint", "Protocol version"});
    add_field({"packet_id", 4, 12, "uint", "Unique packet identifier"});
    add_field({"type", 16, 3, "enum", "Packet type identifier"});
    add_field({"flags", 19, 8, "flags", "Control flags"});
    add_field({"day", 27, 3, "uint", "Day offset (0-7)"});
    add_field({"reserved1", 30, 2, "reserved", "Reserved bits"});
    add_field({"timestamp", 32, 64, "timestamp", "Unix timestamp"});
    add_field({"area_code", 96, 20, "uint", "Geographic area code"});
    add_field({"checksum", 116, 12, "checksum", "12-bit packet checksum"});
    
    // レスポンス固有フィールド
    add_field({"weather_code", 128, 16, "uint", "Weather condition code"});
    add_field({"temperature", 144, 8, "int", "Temperature (signed, +100 offset)"});
    add_field({"precipitation_prob", 152, 8, "uint", "Precipitation probability percentage"});
}

bool ResponsePacketFormat::validate(std::span<const uint8_t> data) const {
    if (!PacketFormatBase::validate(data)) {
        return false;
    }
    
    // レスポンス固有の検証
    uint64_t version = get_field_value("version", data);
    if (version != 1) {
        return false;
    }
    
    uint64_t precipitation_prob = get_field_value("precipitation_prob", data);
    if (precipitation_prob > 100) {
        return false; // 降水確率は0-100%
    }
    
    return true;
}

} // namespace wiplib::packet