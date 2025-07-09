#pragma once
#include "FormatBase.hpp"
#include "ExtendedField.hpp"

namespace packet {

class FormatExtended : public FormatBase {
public:
    FormatExtended();
    FormatExtended(uint64_t bitstr);
    FormatExtended(const ExtendedField& ex, const std::map<std::string,uint64_t>& base = {});

    ExtendedField exField;

    uint64_t toBits() const;
    void fromBits(uint64_t bitstr);
};

} // namespace packet
