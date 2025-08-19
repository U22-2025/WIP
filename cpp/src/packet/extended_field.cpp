#include "wiplib/packet/extended_field.hpp"
#include "wiplib/packet/bit_utils.hpp"
#include <algorithm>
#include <cstring>

namespace wiplib::packet {

// ExtendedCoordinate implementation
std::vector<uint8_t> ExtendedCoordinate::pack() const {
    std::vector<uint8_t> data(8);
    
    // IEEE 754 float32形式でパック
    uint32_t lat_bits, lon_bits;
    std::memcpy(&lat_bits, &latitude, sizeof(float));
    std::memcpy(&lon_bits, &longitude, sizeof(float));
    
    // little-endian で格納（codecと一致）
    write_le32(data.data(), lat_bits);
    write_le32(data.data() + 4, lon_bits);
    
    return data;
}

std::optional<ExtendedCoordinate> ExtendedCoordinate::unpack(std::span<const uint8_t> data) {
    if (data.size() < 8) return std::nullopt;
    
    ExtendedCoordinate coord;
    
    uint32_t lat_bits = read_le32(data.data());
    uint32_t lon_bits = read_le32(data.data() + 4);
    
    std::memcpy(&coord.latitude, &lat_bits, sizeof(float));
    std::memcpy(&coord.longitude, &lon_bits, sizeof(float));
    
    return coord;
}

// SourceInfo implementation
std::vector<uint8_t> SourceInfo::pack() const {
    std::vector<uint8_t> data(6);
    
    data[0] = source_id;
    write_le32(data.data() + 1, timestamp);
    data[5] = quality;
    
    return data;
}

std::optional<SourceInfo> SourceInfo::unpack(std::span<const uint8_t> data) {
    if (data.size() < 6) return std::nullopt;
    
    SourceInfo info;
    info.source_id = data[0];
    info.timestamp = read_le32(data.data() + 1);
    info.quality = data[5];
    
    return info;
}

// ExtendedFieldHeader implementation
std::array<uint8_t, 2> ExtendedFieldHeader::pack() const {
    std::array<uint8_t, 2> data;
    
    // 16bit: 10bit length + 6bit key
    uint16_t packed = (length & 0x3FF) | ((key & 0x3F) << 10);
    // little-endian で格納
    data[0] = static_cast<uint8_t>(packed & 0xFF);
    data[1] = static_cast<uint8_t>((packed >> 8) & 0xFF);
    
    return data;
}

ExtendedFieldHeader ExtendedFieldHeader::unpack(std::span<const uint8_t> data) {
    if (data.size() < 2) return {};
    
    // little-endian で読み取り
    uint16_t packed = static_cast<uint16_t>(data[0] | (static_cast<uint16_t>(data[1]) << 8));
    
    ExtendedFieldHeader header;
    header.length = static_cast<unsigned>(packed & 0x03FFu);
    header.key = static_cast<unsigned>((packed >> 10) & 0x3Fu);
    
    return header;
}

// ExtendedFieldProcessor implementation
proto::ExtendedField ExtendedFieldProcessor::create_field(ExtendedFieldKey key, const ExtendedFieldValue& value) {
    proto::ExtendedField field;
    field.data_type = static_cast<uint8_t>(key);

    ExtendedDataType data_type = key_to_data_type(key);
    std::vector<uint8_t> packed_value = pack_value(data_type, value);
    // In-memory representation stores value only (codec prepends header when encoding)
    field.data = std::move(packed_value);
    
    return field;
}

ExtendedFieldHeader ExtendedFieldProcessor::extract_header(const proto::ExtendedField& field) {
    // In-memory: header is implicit (length = data.size, key = data_type)
    return ExtendedFieldHeader{static_cast<uint16_t>(field.data.size() & 0x3FFu),
                               static_cast<uint8_t>(field.data_type & 0x3Fu)};
}

std::optional<ExtendedFieldValue> ExtendedFieldProcessor::extract_value(const proto::ExtendedField& field) {
    ExtendedFieldHeader header = extract_header(field);
    ExtendedDataType data_type = key_to_data_type(static_cast<ExtendedFieldKey>(header.key));
    std::span<const uint8_t> value_data{field.data.data(), field.data.size()};
    return unpack_value(data_type, value_data);
}

std::vector<uint8_t> ExtendedFieldProcessor::pack_value(ExtendedDataType type, const ExtendedFieldValue& value) {
    switch (type) {
        case ExtendedDataType::StringList:
            if (auto* strings = std::get_if<std::vector<std::string>>(&value)) {
                return pack_string_list(*strings);
            }
            break;
        case ExtendedDataType::Coordinate:
            if (auto* coord = std::get_if<ExtendedCoordinate>(&value)) {
                return coord->pack();
            }
            break;
        case ExtendedDataType::Source:
            if (auto* source = std::get_if<SourceInfo>(&value)) {
                return source->pack();
            }
            break;
        case ExtendedDataType::Binary:
            if (auto* binary = std::get_if<std::vector<uint8_t>>(&value)) {
                return *binary;
            }
            break;
        case ExtendedDataType::Float32:
            if (auto* f = std::get_if<float>(&value)) {
                return pack_float32(*f);
            }
            break;
        case ExtendedDataType::Json:
            if (auto* json = std::get_if<std::string>(&value)) {
                return std::vector<uint8_t>(json->begin(), json->end());
            }
            break;
        case ExtendedDataType::Integer:
            if (auto* i = std::get_if<int64_t>(&value)) {
                return pack_integer(*i);
            }
            break;
        case ExtendedDataType::Boolean:
            if (auto* b = std::get_if<bool>(&value)) {
                return pack_boolean(*b);
            }
            break;
    }
    return {};
}

std::optional<ExtendedFieldValue> ExtendedFieldProcessor::unpack_value(ExtendedDataType type, std::span<const uint8_t> data) {
    switch (type) {
        case ExtendedDataType::StringList:
            if (auto strings = unpack_string_list(data)) {
                return *strings;
            }
            break;
        case ExtendedDataType::Coordinate:
            if (auto coord = ExtendedCoordinate::unpack(data)) {
                return *coord;
            }
            break;
        case ExtendedDataType::Source:
            if (auto source = SourceInfo::unpack(data)) {
                return *source;
            }
            break;
        case ExtendedDataType::Binary:
            return std::vector<uint8_t>(data.begin(), data.end());
        case ExtendedDataType::Float32:
            if (auto f = unpack_float32(data)) {
                return *f;
            }
            break;
        case ExtendedDataType::Json:
            return std::string(data.begin(), data.end());
        case ExtendedDataType::Integer:
            if (auto i = unpack_integer(data)) {
                return *i;
            }
            break;
        case ExtendedDataType::Boolean:
            if (auto b = unpack_boolean(data)) {
                return *b;
            }
            break;
    }
    return std::nullopt;
}

bool ExtendedFieldProcessor::validate_field(const proto::ExtendedField& field) {
    ExtendedFieldHeader header = extract_header(field);
    if (header.length > 1023) return false;
    if (header.key > 63) return false;
    return true;
}

size_t ExtendedFieldProcessor::calculate_extensions_size(const std::vector<proto::ExtendedField>& fields) {
    size_t total_size = 0;
    for (const auto& field : fields) {
        // On-wire size: 2 bytes header + value length
        total_size += 2 + field.data.size();
    }
    return total_size;
}

// Private helper methods
ExtendedDataType ExtendedFieldProcessor::key_to_data_type(ExtendedFieldKey key) {
    switch (key) {
        case ExtendedFieldKey::Alert:
        case ExtendedFieldKey::Disaster:
            return ExtendedDataType::StringList;
        case ExtendedFieldKey::Coordinate:
            return ExtendedDataType::Coordinate;
        case ExtendedFieldKey::AuthHash:
            return ExtendedDataType::Json;
        case ExtendedFieldKey::SourceInfo:
            return ExtendedDataType::Source;
        case ExtendedFieldKey::CustomData:
            return ExtendedDataType::Binary;
        case ExtendedFieldKey::SensorReading:
            return ExtendedDataType::Float32;
        case ExtendedFieldKey::Metadata:
            return ExtendedDataType::Json;
        default:
            return ExtendedDataType::Binary;
    }
}

std::vector<uint8_t> ExtendedFieldProcessor::pack_string_list(const std::vector<std::string>& strings) {
    std::vector<uint8_t> data;
    
    // 文字列数（2バイト）
    uint16_t count = static_cast<uint16_t>(strings.size());
    data.push_back(static_cast<uint8_t>((count >> 8) & 0xFF));
    data.push_back(static_cast<uint8_t>(count & 0xFF));
    
    // 各文字列（長さ + データ）
    for (const auto& str : strings) {
        uint16_t len = static_cast<uint16_t>(str.length());
        data.push_back(static_cast<uint8_t>((len >> 8) & 0xFF));
        data.push_back(static_cast<uint8_t>(len & 0xFF));
        data.insert(data.end(), str.begin(), str.end());
    }
    
    return data;
}

std::optional<std::vector<std::string>> ExtendedFieldProcessor::unpack_string_list(std::span<const uint8_t> data) {
    if (data.size() < 2) return std::nullopt;
    
    uint16_t count = (static_cast<uint16_t>(data[0]) << 8) | data[1];
    std::vector<std::string> strings;
    strings.reserve(count);
    
    size_t offset = 2;
    for (uint16_t i = 0; i < count && offset < data.size(); ++i) {
        if (offset + 2 > data.size()) return std::nullopt;
        
        uint16_t len = (static_cast<uint16_t>(data[offset]) << 8) | data[offset + 1];
        offset += 2;
        
        if (offset + len > data.size()) return std::nullopt;
        
        strings.emplace_back(data.data() + offset, data.data() + offset + len);
        offset += len;
    }
    
    return strings;
}

std::vector<uint8_t> ExtendedFieldProcessor::pack_float32(float value) {
    std::vector<uint8_t> data(4);
    uint32_t bits;
    std::memcpy(&bits, &value, sizeof(float));
    write_le32(data.data(), bits);
    return data;
}

std::optional<float> ExtendedFieldProcessor::unpack_float32(std::span<const uint8_t> data) {
    if (data.size() < 4) return std::nullopt;
    
    uint32_t bits = read_le32(data.data());
    float value;
    std::memcpy(&value, &bits, sizeof(float));
    return value;
}

std::vector<uint8_t> ExtendedFieldProcessor::pack_integer(int64_t value) {
    std::vector<uint8_t> data(8);
    write_le64(data.data(), static_cast<uint64_t>(value));
    return data;
}

std::optional<int64_t> ExtendedFieldProcessor::unpack_integer(std::span<const uint8_t> data) {
    if (data.size() < 8) return std::nullopt;
    
    uint64_t bits = read_le64(data.data());
    return static_cast<int64_t>(bits);
}

std::vector<uint8_t> ExtendedFieldProcessor::pack_boolean(bool value) {
    return {value ? uint8_t(1) : uint8_t(0)};
}

std::optional<bool> ExtendedFieldProcessor::unpack_boolean(std::span<const uint8_t> data) {
    if (data.size() < 1) return std::nullopt;
    return data[0] != 0;
}

// ExtendedFieldManager implementation
void ExtendedFieldManager::add_field(proto::Packet& packet, ExtendedFieldKey key, const ExtendedFieldValue& value) {
    // 既存の同じキーのフィールドを削除
    remove_field(packet, key);
    
    // 新しいフィールドを追加
    auto field = ExtendedFieldProcessor::create_field(key, value);
    packet.extensions.push_back(std::move(field));
}

std::optional<ExtendedFieldValue> ExtendedFieldManager::get_field(const proto::Packet& packet, ExtendedFieldKey key) {
    for (const auto& field : packet.extensions) {
        if (field.data_type == static_cast<uint8_t>(key)) {
            return ExtendedFieldProcessor::extract_value(field);
        }
    }
    return std::nullopt;
}

bool ExtendedFieldManager::remove_field(proto::Packet& packet, ExtendedFieldKey key) {
    auto it = std::remove_if(packet.extensions.begin(), packet.extensions.end(),
        [key](const proto::ExtendedField& field) {
            return field.data_type == static_cast<uint8_t>(key);
        });
    
    bool removed = (it != packet.extensions.end());
    packet.extensions.erase(it, packet.extensions.end());
    return removed;
}

std::unordered_map<ExtendedFieldKey, ExtendedFieldValue> ExtendedFieldManager::get_all_fields(const proto::Packet& packet) {
    std::unordered_map<ExtendedFieldKey, ExtendedFieldValue> fields;
    
    for (const auto& field : packet.extensions) {
        auto value = ExtendedFieldProcessor::extract_value(field);
        if (value) {
            fields[static_cast<ExtendedFieldKey>(field.data_type & 0x3Fu)] = *value;
        }
    }
    
    return fields;
}

bool ExtendedFieldManager::has_field(const proto::Packet& packet, ExtendedFieldKey key) {
    return get_field(packet, key).has_value();
}

size_t ExtendedFieldManager::get_field_count(const proto::Packet& packet) {
    return packet.extensions.size();
}

bool ExtendedFieldManager::validate_extensions(const proto::Packet& packet) {
    if (packet.extensions.size() > 16) return false; // 最大16個
    
    for (const auto& field : packet.extensions) {
        if (!ExtendedFieldProcessor::validate_field(field)) {
            return false;
        }
    }
    
    return true;
}

} // namespace wiplib::packet
