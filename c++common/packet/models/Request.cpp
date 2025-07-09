#include "Request.hpp"

namespace wip {
namespace packet {

uint16_t Request::calc_checksum12(const std::vector<uint8_t>& data) {
    uint32_t total = 0;
    for (uint8_t b : data) total += b;
    while (total >> 12) {
        total = (total & 0xFFF) + (total >> 12);
    }
    return static_cast<uint16_t>((~total) & 0xFFF);
}

std::vector<uint8_t> Request::to_bytes() {
    unsigned __int128 bits = 0;
    bits |= static_cast<unsigned __int128>(version & 0xF) << 0;
    bits |= static_cast<unsigned __int128>(packet_id & 0xFFF) << 4;
    bits |= static_cast<unsigned __int128>(type & 0x7) << 16;
    bits |= static_cast<unsigned __int128>(weather_flag & 0x1) << 19;
    bits |= static_cast<unsigned __int128>(temperature_flag & 0x1) << 20;
    bits |= static_cast<unsigned __int128>(pop_flag & 0x1) << 21;
    bits |= static_cast<unsigned __int128>(alert_flag & 0x1) << 22;
    bits |= static_cast<unsigned __int128>(disaster_flag & 0x1) << 23;
    bits |= static_cast<unsigned __int128>(ex_flag & 0x1) << 24;
    bits |= static_cast<unsigned __int128>(request_auth & 0x1) << 25;
    bits |= static_cast<unsigned __int128>(response_auth & 0x1) << 26;
    bits |= static_cast<unsigned __int128>(day & 0x7) << 27;
    bits |= static_cast<unsigned __int128>(reserved & 0x3) << 30;
    bits |= static_cast<unsigned __int128>(timestamp) << 32;
    uint32_t area = static_cast<uint32_t>(std::stoul(area_code));
    bits |= static_cast<unsigned __int128>(area & 0xFFFFF) << 96;
    // チェックサム計算用に一旦0
    unsigned __int128 bits_no_checksum = bits;
    std::vector<uint8_t> bytes(16);
    for (int i = 0; i < 16; ++i) {
        bytes[i] = static_cast<uint8_t>(bits_no_checksum >> (i * 8));
    }
    checksum = calc_checksum12(bytes);
    bits |= static_cast<unsigned __int128>(checksum & 0xFFF) << 116;
    for (int i = 0; i < 16; ++i) {
        bytes[i] = static_cast<uint8_t>(bits >> (i * 8));
    }
    return bytes;
}

Request Request::from_bytes(const std::vector<uint8_t>& bytes) {
    Request req;
    if (bytes.size() < 16) return req;
    unsigned __int128 bitstr = 0;
    for (size_t i = 0; i < 16; ++i) {
        bitstr |= static_cast<unsigned __int128>(bytes[i]) << (i * 8);
    }
    req.version = (bitstr >> 0) & 0xF;
    req.packet_id = (bitstr >> 4) & 0xFFF;
    req.type = (bitstr >> 16) & 0x7;
    req.weather_flag = (bitstr >> 19) & 0x1;
    req.temperature_flag = (bitstr >> 20) & 0x1;
    req.pop_flag = (bitstr >> 21) & 0x1;
    req.alert_flag = (bitstr >> 22) & 0x1;
    req.disaster_flag = (bitstr >> 23) & 0x1;
    req.ex_flag = (bitstr >> 24) & 0x1;
    req.request_auth = (bitstr >> 25) & 0x1;
    req.response_auth = (bitstr >> 26) & 0x1;
    req.day = (bitstr >> 27) & 0x7;
    req.reserved = (bitstr >> 30) & 0x3;
    req.timestamp = (bitstr >> 32) & 0xFFFFFFFFFFFFFFFFULL;
    uint32_t area = (bitstr >> 96) & 0xFFFFF;
    char buf[7];
    snprintf(buf, sizeof(buf), "%06u", area);
    req.area_code = buf;
    req.checksum = (bitstr >> 116) & 0xFFF;
    return req;
}

} // namespace packet
} // namespace wip
