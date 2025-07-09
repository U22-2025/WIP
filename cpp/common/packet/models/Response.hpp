#pragma once
#include "Request.hpp"

namespace wip {
namespace packet {

class Response : public Request {
public:
    uint16_t weather_code{0};
    uint8_t temperature{0};
    uint8_t pop{0};

    std::vector<uint8_t> to_bytes();
    static Response from_bytes(const std::vector<uint8_t>& bytes);
};

} // namespace packet
} // namespace wip
