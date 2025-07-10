#include <cstdio>
#include <boost/multiprecision/cpp_int.hpp>
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
    using boost::multiprecision::uint128_t;
    uint128_t bits = 0;
    bits |= static_cast<uint128_t>(version & 0xF) << 0;
    bits |= static_cast<uint128_t>(packet_id & 0xFFF) << 4;
    bits |= static_cast<uint128_t>(type & 0x7) << 16;
    bits |= static_cast<uint128_t>(weather_flag & 0x1) << 19;
    bits |= static_cast<uint128_t>(temperature_flag & 0x1) << 20;
    bits |= static_cast<uint128_t>(pop_flag & 0x1) << 21;
    bits |= static_cast<uint128_t>(alert_flag & 0x1) << 22;
    bits |= static_cast<uint128_t>(disaster_flag & 0x1) << 23;
    bits |= static_cast<uint128_t>(ex_flag & 0x1) << 24;
    bits |= static_cast<uint128_t>(request_auth & 0x1) << 25;
    bits |= static_cast<uint128_t>(response_auth & 0x1) << 26;
    bits |= static_cast<uint128_t>(day & 0x7) << 27;
    bits |= static_cast<uint128_t>(reserved & 0x3) << 30;
    bits |= static_cast<uint128_t>(timestamp) << 32;
    uint32_t area = static_cast<uint32_t>(std::stoul(area_code));
    bits |= static_cast<uint128_t>(area & 0xFFFFF) << 96;
    // チェックサム計算用に一旦0
    uint128_t bits_no_checksum = bits;
    std::vector<uint8_t> bytes(16);
    for (int i = 0; i < 16; ++i) {
        bytes[i] = static_cast<uint8_t>(bits_no_checksum >> (i * 8));
    }
    checksum = calc_checksum12(bytes);
    bits |= static_cast<uint128_t>(checksum & 0xFFF) << 116;
    for (int i = 0; i < 16; ++i) {
        bytes[i] = static_cast<uint8_t>(bits >> (i * 8));
    }
    return bytes;
}

Request Request::from_bytes(const std::vector<uint8_t>& bytes) {
    using boost::multiprecision::uint128_t;
    Request req;
    if (bytes.size() < 16) return req;
    uint128_t bitstr = 0;
    for (size_t i = 0; i < 16; ++i) {
        bitstr |= static_cast<uint128_t>(bytes[i]) << (i * 8);
    }
    req.version = static_cast<uint8_t>((bitstr >> 0) & 0xF);
    req.packet_id = static_cast<uint16_t>((bitstr >> 4) & 0xFFF);
    req.type = static_cast<uint8_t>((bitstr >> 16) & 0x7);
    req.weather_flag = static_cast<bool>((bitstr >> 19) & 0x1);
    req.temperature_flag = static_cast<bool>((bitstr >> 20) & 0x1);
    req.pop_flag = static_cast<bool>((bitstr >> 21) & 0x1);
    req.alert_flag = static_cast<bool>((bitstr >> 22) & 0x1);
    req.disaster_flag = static_cast<bool>((bitstr >> 23) & 0x1);
    req.ex_flag = static_cast<bool>((bitstr >> 24) & 0x1);
    req.request_auth = static_cast<bool>((bitstr >> 25) & 0x1);
    req.response_auth = static_cast<bool>((bitstr >> 26) & 0x1);
    req.day = static_cast<uint8_t>((bitstr >> 27) & 0x7);
    req.reserved = static_cast<uint8_t>((bitstr >> 30) & 0x3);
    req.timestamp = static_cast<uint64_t>((bitstr >> 32) & 0xFFFFFFFFFFFFFFFFULL);
    uint32_t area = static_cast<uint32_t>((bitstr >> 96) & 0xFFFFF);
    char buf[7];
    snprintf(buf, sizeof(buf), "%06u", area);
    req.area_code = buf;
    req.checksum = static_cast<uint16_t>((bitstr >> 116) & 0xFFF);
    return req;
}

} // namespace packet
} // namespace wip
