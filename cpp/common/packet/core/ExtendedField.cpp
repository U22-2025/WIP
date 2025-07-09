#include "ExtendedField.hpp"
#include "BitUtils.hpp"
#include <cstring>

namespace packet {

ExtendedField::ExtendedField(const std::map<std::string, std::string>& data) : data_(data) {}

void ExtendedField::set(const std::string& key, const std::string& value) {
    data_[key] = value;
}

std::string ExtendedField::get(const std::string& key) const {
    auto it = data_.find(key);
    if (it == data_.end()) return "";
    return it->second;
}

std::map<std::string, std::string> ExtendedField::toDict() const {
    return data_;
}

uint64_t ExtendedField::toBits() const {
    // Simplified: encode one key only
    if (data_.empty()) return 0;
    auto it = data_.begin();
    uint64_t key = loadExtendedFields().at(it->first).length; // use id as length
    const std::string& val = it->second;
    uint64_t len = val.size();
    uint64_t header = (key << 10) | (len & 0x3FF);
    uint64_t value = 0;
    for (size_t i = 0; i < val.size() && i < 8; ++i) {
        value |= ((uint64_t)(uint8_t)val[i]) << (i*8);
    }
    return (value << 16) | header;
}

ExtendedField ExtendedField::fromBits(uint64_t bits, int /*totalBits*/) {
    ExtendedField ex;
    uint64_t header = bits & 0xFFFF;
    uint64_t key = header >> 10;
    uint64_t len = header & 0x3FF;
    uint64_t valueBits = bits >> 16;
    std::string val;
    for (size_t i = 0; i < len && i < sizeof(uint64_t); ++i) {
        char c = (valueBits >> (i*8)) & 0xFF;
        val.push_back(c);
    }
    auto spec = loadExtendedFields();
    for (const auto& p : spec) {
        if (p.second.length == (int)key) {
            ex.data_[p.first] = val;
            break;
        }
    }
    return ex;
}

} // namespace packet
