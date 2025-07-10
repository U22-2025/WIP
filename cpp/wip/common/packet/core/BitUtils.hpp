#pragma once
#include <cstdint>
#ifdef _MSC_VER
#  include <intrin.h>
#endif
#include "Exceptions.hpp"

namespace packet {

inline uint64_t extract_bits(uint64_t bitstr, int start, int length) {
    if (length <= 0) {
        throw BitFieldError("length must be positive");
    }
    uint64_t mask = ((uint64_t)1 << length) - 1;
    return (bitstr >> start) & mask;
}

inline uint64_t extract_rest_bits(uint64_t bitstr, int start) {
    return bitstr >> start;
}

inline int bits_to_bytes(uint64_t bits) {
#ifdef _MSC_VER
    unsigned long idx;
    if (_BitScanReverse64(&idx, bits)) {
        return static_cast<int>((idx + 8) / 8);
    }
    return 1;
#else
    return bits ? static_cast<int>((64 - __builtin_clzll(bits) + 7) / 8) : 1;
#endif
}

} // namespace packet
