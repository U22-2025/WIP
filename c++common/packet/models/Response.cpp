#include "Response.hpp"

namespace wip {
namespace packet {

std::vector<uint8_t> Response::to_bytes() {
    auto base = Request::to_bytes();
    unsigned __int128 bitstr = 0;
    for (int i = 0; i < 16; ++i) bitstr |= static_cast<unsigned __int128>(base[i]) << (i*8);
    bitstr |= static_cast<unsigned __int128>(weather_code & 0xFFFF) << 128;
    bitstr |= static_cast<unsigned __int128>(temperature & 0xFF) << 144;
    bitstr |= static_cast<unsigned __int128>(pop & 0xFF) << 152;
    std::vector<uint8_t> bytes(20);
    for (int i = 0; i < 20; ++i) {
        bytes[i] = static_cast<uint8_t>(bitstr >> (i*8));
    }
    return bytes;
}

Response Response::from_bytes(const std::vector<uint8_t>& bytes) {
    Response res;
    if (bytes.size() < 20) return res;
    Request base = Request::from_bytes({bytes.begin(), bytes.begin()+16});
    res = static_cast<Response&>(base);
    unsigned __int128 bitstr = 0;
    for (int i = 0; i < 20; ++i) bitstr |= static_cast<unsigned __int128>(bytes[i]) << (i*8);
    res.weather_code = (bitstr >> 128) & 0xFFFF;
    res.temperature = (bitstr >> 144) & 0xFF;
    res.pop = (bitstr >> 152) & 0xFF;
    return res;
}

} // namespace packet
} // namespace wip
