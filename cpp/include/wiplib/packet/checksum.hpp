#pragma once

#include <cstdint>
#include <span>

namespace wiplib::packet {

/**
 * @brief Calculate 12-bit checksum
 * @param data Data byte array
 * @return 12-bit checksum value
 */
uint16_t calc_checksum12(std::span<const uint8_t> data);

/**
 * @brief Verify 12-bit checksum
 * @param data Data byte array
 * @param expected_checksum Expected checksum value
 * @return true if checksum matches
 */
bool verify_checksum12(std::span<const uint8_t> data, uint16_t expected_checksum);

namespace detail {
    /**
     * @brief Carry fold implementation (optimized version)
     * @param value Value to calculate
     * @return Folded value
     */
    uint16_t carry_fold(uint32_t value);
}

} // namespace wiplib::packet