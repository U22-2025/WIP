#pragma once

#include <cstdint>
#include <span>

namespace wiplib::packet {

/**
 * @brief Extract specified bit range
 * @param data Data
 * @param bit_offset Bit offset (starting from 0)
 * @param bit_length Bit length
 * @return Extracted bit value
 */
uint64_t extract_bits(uint64_t data, uint8_t bit_offset, uint8_t bit_length);

/**
 * @brief Extract specified bit range from byte array
 * @param data Byte array
 * @param bit_offset Bit offset (starting from 0)
 * @param bit_length Bit length
 * @return Extracted bit value
 */
uint64_t extract_bits(std::span<const uint8_t> data, uint32_t bit_offset, uint8_t bit_length);

/**
 * @brief Set value to specified bit range
 * @param data Target data
 * @param bit_offset Bit offset (starting from 0)
 * @param bit_length Bit length
 * @param value Value to set
 * @return Data after setting
 */
uint64_t set_bits(uint64_t data, uint8_t bit_offset, uint8_t bit_length, uint64_t value);

/**
 * @brief Set value to specified bit range in byte array
 * @param data Byte array
 * @param bit_offset Bit offset (starting from 0)
 * @param bit_length Bit length
 * @param value Value to set
 */
void set_bits(std::span<uint8_t> data, uint32_t bit_offset, uint8_t bit_length, uint64_t value);

/**
 * @brief Read 16-bit value in little-endian format
 * @param data Data pointer
 * @return 16-bit value
 */
uint16_t read_le16(const uint8_t* data);

/**
 * @brief Read 32-bit value in little-endian format
 * @param data Data pointer
 * @return 32-bit value
 */
uint32_t read_le32(const uint8_t* data);

/**
 * @brief Read 64-bit value in little-endian format
 * @param data Data pointer
 * @return 64-bit value
 */
uint64_t read_le64(const uint8_t* data);

/**
 * @brief Write 16-bit value in little-endian format
 * @param data Data pointer
 * @param value Value to write
 */
void write_le16(uint8_t* data, uint16_t value);

/**
 * @brief Write 32-bit value in little-endian format
 * @param data Data pointer
 * @param value Value to write
 */
void write_le32(uint8_t* data, uint32_t value);

/**
 * @brief Write 64-bit value in little-endian format
 * @param data Data pointer
 * @param value Value to write
 */
void write_le64(uint8_t* data, uint64_t value);

} // namespace wiplib::packet