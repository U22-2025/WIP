#include "wiplib/packet/format_base.hpp"
#include "wiplib/packet/bit_utils.hpp"
#include "wiplib/packet/checksum.hpp"
#include <algorithm>

namespace wiplib::packet {

void PacketFormatBase::add_field(const FieldDefinition& field) {
    fields_[field.name] = field;
    
    // Update packet size
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
    
    // Value range check
    uint64_t max_value = (1ULL << field.bit_length) - 1;
    if (field.type != FieldDefinition::FieldType::Int && value > max_value) {
        throw InvalidFieldError(field_name, "Value out of range");
    }
    
    set_bits(data, field.bit_offset, field.bit_length, value);
}

bool PacketFormatBase::validate(std::span<const uint8_t> data) const {
    if (data.size() < packet_size_) {
        return false;
    }
    
    // Basic validation
    for (const auto& [name, field] : fields_) {
        if (field.type == FieldDefinition::FieldType::Checksum) {
            continue; // Checksum verified later
        }
        
        try {
            uint64_t value = get_field_value(name, data);
            
            // Type-specific validation
            if (field.type == FieldDefinition::FieldType::UInt) {
                uint64_t max_value = (1ULL << field.bit_length) - 1;
                if (value > max_value) {
                    return false;
                }
            } else if (field.type == FieldDefinition::FieldType::Reserved) {
                if (value != 0) {
                    return false; // Reserved fields must be 0
                }
            }
        } catch (const std::exception&) {
            return false;
        }
    }
    
    return true;
}

uint16_t PacketFormatBase::calculate_checksum(std::span<const uint8_t> data) const {
    // Calculate checksum excluding checksum field
    std::vector<uint8_t> checksum_data(data.begin(), data.end());
    
    // Clear checksum field to 0
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
    // Define basic header fields
    add_field({"version", 0, 4, FieldDefinition::FieldType::UInt, "Protocol version"});
    add_field({"packet_id", 4, 12, FieldDefinition::FieldType::UInt, "Unique packet identifier"});
    add_field({"type", 16, 3, FieldDefinition::FieldType::Enum, "Packet type identifier"});
    add_field({"flags", 19, 8, FieldDefinition::FieldType::Flags, "Control flags"});
    add_field({"day", 27, 3, FieldDefinition::FieldType::UInt, "Day offset (0-7)"});
    add_field({"reserved1", 30, 2, FieldDefinition::FieldType::Reserved, "Reserved bits"});
    add_field({"timestamp", 32, 64, FieldDefinition::FieldType::Timestamp, "Unix timestamp"});
    add_field({"area_code", 96, 20, FieldDefinition::FieldType::UInt, "Geographic area code"});
    add_field({"checksum", 116, 12, FieldDefinition::FieldType::Checksum, "12-bit packet checksum"});
}

bool RequestPacketFormat::validate(std::span<const uint8_t> data) const {
    if (!PacketFormatBase::validate(data)) {
        return false;
    }
    
    // Request-specific validation
    uint64_t version = get_field_value("version", data);
    if (version != 1) {
        return false; // Currently only version 1 is supported
    }
    
    return true;
}

ResponsePacketFormat::ResponsePacketFormat() {
    // Define basic header fields
    add_field({"version", 0, 4, FieldDefinition::FieldType::UInt, "Protocol version"});
    add_field({"packet_id", 4, 12, FieldDefinition::FieldType::UInt, "Unique packet identifier"});
    add_field({"type", 16, 3, FieldDefinition::FieldType::Enum, "Packet type identifier"});
    add_field({"flags", 19, 8, FieldDefinition::FieldType::Flags, "Control flags"});
    add_field({"day", 27, 3, FieldDefinition::FieldType::UInt, "Day offset (0-7)"});
    add_field({"reserved1", 30, 2, FieldDefinition::FieldType::Reserved, "Reserved bits"});
    add_field({"timestamp", 32, 64, FieldDefinition::FieldType::Timestamp, "Unix timestamp"});
    add_field({"area_code", 96, 20, FieldDefinition::FieldType::UInt, "Geographic area code"});
    add_field({"checksum", 116, 12, FieldDefinition::FieldType::Checksum, "12-bit packet checksum"});
    
    // Response-specific fields
    add_field({"weather_code", 128, 16, FieldDefinition::FieldType::UInt, "Weather condition code"});
    add_field({"temperature", 144, 8, FieldDefinition::FieldType::Int, "Temperature (signed, +100 offset)"});
    add_field({"precipitation_prob", 152, 8, FieldDefinition::FieldType::UInt, "Precipitation probability percentage"});
}

bool ResponsePacketFormat::validate(std::span<const uint8_t> data) const {
    if (!PacketFormatBase::validate(data)) {
        return false;
    }
    
    // Response-specific validation
    uint64_t version = get_field_value("version", data);
    if (version != 1) {
        return false;
    }
    
    uint64_t precipitation_prob = get_field_value("precipitation_prob", data);
    if (precipitation_prob > 100) {
        return false; // Precipitation probability is 0-100%
    }
    
    return true;
}

} // namespace wiplib::packet
