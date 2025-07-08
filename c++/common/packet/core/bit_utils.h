#ifndef COMMON_PACKET_CORE_BIT_UTILS_H
#define COMMON_PACKET_CORE_BIT_UTILS_H

#include <cstdint>

namespace common {
namespace packet {
namespace core {

template <typename T>
inline T extract_bits(T bitstr, int start, int length) {
    T mask = ((T{1} << length) - 1);
    return (bitstr >> start) & mask;
}

template <typename T>
inline T extract_rest_bits(T bitstr, int start) {
    return bitstr >> start;
}

} // namespace core
} // namespace packet
} // namespace common

#endif
