#ifndef COMMON_PACKET_CORE_FORMAT_H
#define COMMON_PACKET_CORE_FORMAT_H

#include "format_base.h"
#include "extended_field.h"

namespace common {
namespace packet {
namespace core {

class Format : public FormatBase {
public:
    using FormatBase::u128;
    ExtendedField ex_field;
    u128 toBits() const;
    void fromBits(u128 bits);
};

} // namespace core
} // namespace packet
} // namespace common

#endif
