#pragma once
#include <cstdint>
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

} // namespace packet
