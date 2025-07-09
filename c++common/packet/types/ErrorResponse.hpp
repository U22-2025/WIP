#pragma once
#include "../models/Response.hpp"
#include <optional>

namespace wip {
namespace packet {

class ErrorResponse : public Response {
public:
    ErrorResponse() { type = 7; ex_flag = 1; }
    static ErrorResponse create(uint16_t packet_id, int error_code);
    int error_code() const { return weather_code; }
    void set_error_code(int code) { weather_code = static_cast<uint16_t>(code); }
};

} // namespace packet
} // namespace wip
