#include "extended_field.h"
#include "bit_utils.h"

namespace common {
namespace packet {
namespace core {

void ExtendedField::set(const std::string &key, const std::string &value) {
    data_[key] = value;
}

std::optional<std::string> ExtendedField::get(const std::string &key) const {
    auto it = data_.find(key);
    if (it == data_.end()) return std::nullopt;
    return it->second;
}

uint64_t ExtendedField::toBits() const {
    // very simple encoding: count of fields + each key/value length and ascii bytes
    uint64_t bits = data_.size();
    // Not full implementation
    return bits << 32; // placeholder
}

ExtendedField ExtendedField::fromBits(uint64_t bits) {
    ExtendedField ex; // placeholder
    (void)bits;
    return ex;
}

} // namespace core
} // namespace packet
} // namespace common
