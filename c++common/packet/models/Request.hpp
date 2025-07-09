#pragma once
#include <cstdint>
#include <string>
#include <vector>
#include <unordered_map>

namespace wip {
namespace packet {

class ExtendedField {
public:
    std::unordered_map<std::string, std::string> data;
};

class Request {
public:
    uint8_t version{1};
    uint16_t packet_id{0};
    uint8_t type{0};
    bool weather_flag{false};
    bool temperature_flag{false};
    bool pop_flag{false};
    bool alert_flag{false};
    bool disaster_flag{false};
    bool ex_flag{false};
    bool request_auth{false};
    bool response_auth{false};
    uint8_t day{0};
    uint8_t reserved{0};
    uint64_t timestamp{0};
    std::string area_code{"000000"};
    uint16_t checksum{0};
    ExtendedField ex_field;

    Request() = default;

    std::vector<uint8_t> to_bytes();
    static Request from_bytes(const std::vector<uint8_t>& bytes);

private:
    static uint16_t calc_checksum12(const std::vector<uint8_t>& data);
};

} // namespace packet
} // namespace wip
