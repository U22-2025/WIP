#include "FormatBase.hpp"
#include <vector>
#include <cstring>

namespace packet {

FieldSpec FormatBase::FIELD_SPEC = loadBaseFields();
std::map<std::string,int> FormatBase::FIELD_LENGTH;
std::map<std::string,std::string> FormatBase::FIELD_TYPE;
std::map<std::string,int> FormatBase::FIELD_POSITION;
std::map<std::string,std::pair<int,int>> FormatBase::BIT_FIELDS;

void FormatBase::initFieldSpec() {
    int pos = 0;
    FIELD_LENGTH.clear();
    FIELD_TYPE.clear();
    FIELD_POSITION.clear();
    BIT_FIELDS.clear();
    for (const auto& p : FIELD_SPEC) {
        FIELD_LENGTH[p.first] = p.second.length;
        FIELD_TYPE[p.first] = p.second.type;
        FIELD_POSITION[p.first] = pos;
        BIT_FIELDS[p.first] = {pos, p.second.length};
        pos += p.second.length;
    }
}

void FormatBase::reloadFieldSpec(const std::string& fileName) {
    FIELD_SPEC = loadBaseFields(fileName);
    initFieldSpec();
}

FormatBase::FormatBase() {
    if (FIELD_POSITION.empty()) initFieldSpec();
    for (const auto& p : FIELD_LENGTH) {
        fields_[p.first] = 0;
    }
}

FormatBase::FormatBase(uint64_t bitstr) : FormatBase() {
    fromBits(bitstr);
}

void FormatBase::fromBits(uint64_t bitstr) {
    for (const auto& p : BIT_FIELDS) {
        fields_[p.first] = extract_bits(bitstr, p.second.first, p.second.second);
    }
}

uint64_t FormatBase::toBits() const {
    uint64_t result = 0;
    for (const auto& p : BIT_FIELDS) {
        uint64_t value = fields_.at(p.first);
        uint64_t mask = ((uint64_t)1 << p.second.second) - 1;
        result |= (value & mask) << p.second.first;
    }
    return result;
}

std::vector<uint8_t> FormatBase::toBytes() {
    uint64_t bits = toBits();
    int bytes = bits_to_bytes(bits);
    std::vector<uint8_t> buf(bytes,0);
    for (int i=0;i<bytes;i++) buf[i]= (bits>>(i*8)) & 0xFF;
    return buf;
}

FormatBase FormatBase::fromBytes(const std::vector<uint8_t>& data) {
    uint64_t bitstr = 0;
    for (size_t i=0;i<data.size();++i) {
        bitstr |= ((uint64_t)data[i]) << (i*8);
    }
    return FormatBase(bitstr);
}

uint64_t FormatBase::get(const std::string& name) const {
    auto it = fields_.find(name);
    if (it == fields_.end()) throw BitFieldError("unknown field: " + name);
    return it->second;
}

void FormatBase::set(const std::string& name, uint64_t value) {
    auto it = fields_.find(name);
    if (it == fields_.end()) throw BitFieldError("unknown field: " + name);
    it->second = value;
    recalcChecksum();
}

int FormatBase::getMinPacketSize() const {
    int bits=0;
    for (const auto& p : FIELD_LENGTH) bits += p.second;
    return bits/8;
}

static uint16_t calc_checksum12(const std::vector<uint8_t>& data) {
    uint32_t total=0;
    for(uint8_t b: data) total+=b;
    while (total>>12) {
        total = (total & 0xFFF) + (total >>12);
    }
    return static_cast<uint16_t>(~total) & 0xFFF;
}

void FormatBase::recalcChecksum() {
    auto it = fields_.find("checksum");
    if (it==fields_.end()) return;
    uint64_t original = it->second;
    it->second = 0;
    auto bytes = toBytes();
    it->second = calc_checksum12(bytes);
}

} // namespace packet
