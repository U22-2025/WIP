#include "wiplib/packet/checksum.hpp"
#include <numeric>

namespace wiplib::packet {

namespace detail {
    uint16_t carry_fold(uint32_t value) {
        // Carry fold: add upper bits to lower bits
        while (value > 0xFFFF) {
            value = (value & 0xFFFF) + (value >> 16);
        }
        return static_cast<uint16_t>(value);
    }
}

uint16_t calc_checksum12(std::span<const uint8_t> data) {
    // Internet checksum algorithm adapted for 12-bit
    uint32_t sum = 0;
    
    // Process 2 bytes at a time
    for (size_t i = 0; i < data.size(); i += 2) {
        uint16_t word = 0;
        if (i + 1 < data.size()) {
            // Combine 2 bytes in big-endian
            word = (static_cast<uint16_t>(data[i]) << 8) | data[i + 1];
        } else {
            // For odd bytes, use upper byte only
            word = static_cast<uint16_t>(data[i]) << 8;
        }
        sum += word;
    }
    
    // Carry fold
    uint16_t folded = detail::carry_fold(sum);
    
    // Take one's complement and mask to 12 bits
    uint16_t checksum = (~folded) & 0x0FFF;
    
    return checksum;
}

bool verify_checksum12(std::span<const uint8_t> data, uint16_t expected_checksum) {
    uint16_t calculated = calc_checksum12(data);
    return calculated == expected_checksum;
}

} // namespace wiplib::packet