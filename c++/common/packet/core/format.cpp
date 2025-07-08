#include "format.h"

namespace common {
namespace packet {
namespace core {

u128 Format::toBits() const {
    u128 bits = FormatBase::toBits();
    bits |= static_cast<u128>(ex_field.toBits()); // placeholder
    return bits;
}

void Format::fromBits(u128 bits) {
    FormatBase::fromBits(bits);
    ex_field = ExtendedField::fromBits(static_cast<uint64_t>(bits)); // placeholder
}

} // namespace core
} // namespace packet
} // namespace common
