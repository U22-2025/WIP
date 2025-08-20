#pragma once

#include <stdexcept>
#include <string>

namespace wiplib::packet {

/**
 * @brief パケット解析エラー
 */
class PacketParseError : public std::runtime_error {
public:
    explicit PacketParseError(const std::string& message)
        : std::runtime_error("PacketParseError: " + message) {}
};

/**
 * @brief チェックサム不一致エラー
 */
class ChecksumError : public PacketParseError {
public:
    ChecksumError(uint16_t expected, uint16_t actual)
        : PacketParseError("Checksum mismatch - expected: " + std::to_string(expected) +
                          ", actual: " + std::to_string(actual)) {}
};

/**
 * @brief フィールド値エラー
 */
class InvalidFieldError : public PacketParseError {
public:
    explicit InvalidFieldError(const std::string& field_name, const std::string& reason)
        : PacketParseError("Invalid field '" + field_name + "': " + reason) {}
    
    explicit InvalidFieldError(const std::string& field_name, uint64_t value)
        : PacketParseError("Invalid field '" + field_name + "' value: " + std::to_string(value)) {}
};

} // namespace wiplib::packet