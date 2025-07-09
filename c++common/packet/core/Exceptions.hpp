#pragma once
#include <stdexcept>
#include <string>

namespace packet {
class BitFieldError : public std::runtime_error {
public:
    explicit BitFieldError(const std::string& msg) : std::runtime_error(msg) {}
};
} // namespace packet
