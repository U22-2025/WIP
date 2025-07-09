#include "ErrorResponse.hpp"
#include <ctime>

namespace wip {
namespace packet {

ErrorResponse ErrorResponse::create(uint16_t packet_id, int error_code) {
    ErrorResponse err;
    err.packet_id = packet_id;
    err.timestamp = static_cast<uint64_t>(std::time(nullptr));
    err.weather_code = static_cast<uint16_t>(error_code);
    return err;
}

} // namespace packet
} // namespace wip
