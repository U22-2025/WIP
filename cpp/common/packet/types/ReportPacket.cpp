#include "ReportPacket.hpp"
#include <ctime>

namespace wip {
namespace packet {

PacketIDGenerator12Bit::PacketIDGenerator12Bit() {
    current = static_cast<uint16_t>(std::time(nullptr)) & 0xFFF;
}

uint16_t PacketIDGenerator12Bit::next_id() {
    uint16_t id = current;
    current = (current + 1) & 0xFFF;
    return id;
}

static PacketIDGenerator12Bit PIDG;

ReportRequest ReportRequest::create_sensor_data_report(const std::string& area_code,
                                                      std::optional<int> weather_code,
                                                      std::optional<double> temperature,
                                                      std::optional<int> precipitation_prob,
                                                      std::optional<std::vector<std::string>> alert,
                                                      std::optional<std::vector<std::string>> disaster,
                                                      uint8_t version) {
    ReportRequest req;
    req.version = version;
    req.packet_id = PIDG.next_id();
    req.type = 4;
    req.area_code = area_code;
    req.timestamp = static_cast<uint64_t>(std::time(nullptr));
    req.weather_flag = weather_code.has_value();
    req.temperature_flag = temperature.has_value();
    req.pop_flag = precipitation_prob.has_value();
    req.alert_flag = alert.has_value();
    req.disaster_flag = disaster.has_value();
    req.ex_flag = (alert || disaster) ? 1 : 0;
    if (weather_code) req.weather_code = *weather_code;
    if (temperature) req.temperature = static_cast<uint8_t>(*temperature + 100);
    if (precipitation_prob) req.pop = static_cast<uint8_t>(*precipitation_prob);
    return req;
}

ReportResponse ReportResponse::create_ack_response(const ReportRequest& req,
                                                   uint8_t version) {
    ReportResponse res;
    res.version = version;
    res.packet_id = req.packet_id;
    res.type = 5;
    res.weather_flag = req.weather_flag;
    res.temperature_flag = req.temperature_flag;
    res.pop_flag = req.pop_flag;
    res.alert_flag = req.alert_flag;
    res.disaster_flag = req.disaster_flag;
    res.ex_flag = req.ex_flag;
    res.day = req.day;
    res.timestamp = static_cast<uint64_t>(std::time(nullptr));
    res.area_code = req.area_code;
    res.weather_code = req.weather_code;
    res.temperature = req.temperature;
    res.pop = req.pop;
    res.ex_field = req.ex_field;
    return res;
}

} // namespace packet
} // namespace wip
