#include "QueryPacket.hpp"
#include <ctime>

namespace wip {
namespace packet {

QueryRequest QueryRequest::create_query_request(const std::string& area_code,
                                                uint16_t packet_id,
                                                bool weather,
                                                bool temperature,
                                                bool precipitation_prob,
                                                bool alert,
                                                bool disaster,
                                                uint8_t day,
                                                std::optional<std::pair<std::string,int>> source,
                                                uint8_t version) {
    QueryRequest req;
    req.version = version;
    req.packet_id = packet_id;
    req.type = 2;
    req.weather_flag = weather;
    req.temperature_flag = temperature;
    req.pop_flag = precipitation_prob;
    req.alert_flag = alert;
    req.disaster_flag = disaster;
    req.ex_flag = source ? 1 : 0;
    req.day = day;
    req.timestamp = static_cast<uint64_t>(std::time(nullptr));
    req.area_code = area_code;
    if (source) {
        req.ex_field.data["source_ip"] = source->first;
        req.ex_field.data["source_port"] = std::to_string(source->second);
    }
    return req;
}

QueryRequest QueryRequest::from_location_response(const Response& res,
                                                  std::optional<std::pair<std::string,int>> source) {
    return create_query_request(res.area_code,
                                res.packet_id,
                                res.weather_flag,
                                res.temperature_flag,
                                res.pop_flag,
                                res.alert_flag,
                                res.disaster_flag,
                                res.day,
                                source ? source : std::nullopt,
                                res.version);
}

QueryResponse QueryResponse::create_query_response(const QueryRequest& req,
                                                   uint8_t version) {
    QueryResponse res;
    res.version = version;
    res.packet_id = req.packet_id;
    res.type = 3;
    res.weather_flag = req.weather_flag;
    res.temperature_flag = req.temperature_flag;
    res.pop_flag = req.pop_flag;
    res.alert_flag = req.alert_flag;
    res.disaster_flag = req.disaster_flag;
    res.ex_flag = req.ex_flag;
    res.day = req.day;
    res.timestamp = static_cast<uint64_t>(std::time(nullptr));
    res.area_code = req.area_code;
    res.weather_code = 0;
    res.temperature = 0;
    res.pop = 0;
    res.ex_field = req.ex_field;
    return res;
}

} // namespace packet
} // namespace wip
