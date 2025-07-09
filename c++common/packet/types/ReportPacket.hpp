#pragma once
#include "../models/Response.hpp"
#include <optional>
#include <vector>

namespace wip {
namespace packet {

class ReportRequest : public Response {
public:
    static ReportRequest create_sensor_data_report(const std::string& area_code,
                                                   std::optional<int> weather_code = std::nullopt,
                                                   std::optional<double> temperature = std::nullopt,
                                                   std::optional<int> precipitation_prob = std::nullopt,
                                                   std::optional<std::vector<std::string>> alert = std::nullopt,
                                                   std::optional<std::vector<std::string>> disaster = std::nullopt,
                                                   uint8_t version = 1);
};

class ReportResponse : public Response {
public:
    static ReportResponse create_ack_response(const ReportRequest& req,
                                              uint8_t version = 1);
};

class PacketIDGenerator12Bit {
    uint16_t current{0};
public:
    PacketIDGenerator12Bit();
    uint16_t next_id();
};

} // namespace packet
} // namespace wip
