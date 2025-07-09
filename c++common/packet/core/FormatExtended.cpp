#include "FormatExtended.hpp"

namespace packet {

FormatExtended::FormatExtended() : FormatBase(), exField() {}

FormatExtended::FormatExtended(uint64_t bitstr) : FormatBase(bitstr) {
    if (get("ex_flag") == 1) {
        uint64_t ex_bits = extract_rest_bits(bitstr, getMinPacketSize()*8);
        exField = ExtendedField::fromBits(ex_bits, 0);
    }
}

FormatExtended::FormatExtended(const ExtendedField& ex, const std::map<std::string,uint64_t>& base)
    : FormatBase() , exField(ex) {
    for (auto& p: base) set(p.first, p.second);
}

uint64_t FormatExtended::toBits() const {
    uint64_t bits = FormatBase::toBits();
    if (get("ex_flag") == 1) {
        uint64_t ex_bits = exField.toBits();
        bits |= ex_bits << (getMinPacketSize()*8);
    }
    return bits;
}

void FormatExtended::fromBits(uint64_t bitstr) {
    FormatBase::fromBits(bitstr);
    if (get("ex_flag") == 1) {
        uint64_t ex_bits = extract_rest_bits(bitstr, getMinPacketSize()*8);
        exField = ExtendedField::fromBits(ex_bits,0);
    }
}

} // namespace packet
