#include "Response.hpp"

namespace wip {
namespace packet {

std::vector<uint8_t> Response::to_bytes() {
    auto bytes = Request::to_bytes();
    bytes.push_back(static_cast<uint8_t>(weather_code & 0xFF));
    bytes.push_back(static_cast<uint8_t>((weather_code >> 8) & 0xFF));
    bytes.push_back(static_cast<uint8_t>(temperature));
    bytes.push_back(static_cast<uint8_t>(pop));
    return bytes;
}

Response Response::from_bytes(const std::vector<uint8_t>& bytes) {
    Response res;
    if (bytes.size() < 20) return res;
    Request base = Request::from_bytes({bytes.begin(), bytes.begin() + 16});
    static_cast<Request&>(res) = base;
    res.weather_code = static_cast<uint16_t>(bytes[16]) | (static_cast<uint16_t>(bytes[17]) << 8);
    res.temperature = bytes[18];
    res.pop = bytes[19];
    return res;
}

} // namespace packet
} // namespace wip
