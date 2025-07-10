#include "LocationPacket.hpp"
#include <ctime>

namespace wip {
namespace packet {

LocationRequest LocationRequest::create_coordinate_lookup(double latitude,
                                                         double longitude,
                                                         uint16_t packet_id,
                                                         bool weather,
                                                         bool temperature,
                                                         bool precipitation_prob,
                                                         bool alert,
                                                         bool disaster,
                                                         std::optional<std::pair<std::string,int>> source,
                                                         uint8_t day,
                                                         uint8_t version) {
    LocationRequest req;
    req.version = version;
    req.packet_id = packet_id;
    req.type = 0;
    req.weather_flag = weather;
    req.temperature_flag = temperature;
    req.pop_flag = precipitation_prob;
    req.alert_flag = alert;
    req.disaster_flag = disaster;
    req.ex_flag = 1;
    req.day = day;
    req.timestamp = static_cast<uint64_t>(std::time(nullptr));
    req.area_code = "000000";
    req.ex_field.data["latitude"] = std::to_string(latitude);
    req.ex_field.data["longitude"] = std::to_string(longitude);
    if (source) {
        req.ex_field.data["source_ip"] = source->first;
        req.ex_field.data["source_port"] = std::to_string(source->second);
    }
    return req;
}

LocationResponse LocationResponse::create_area_code_response(const LocationRequest& request,
                                                             const std::string& area_code,
                                                             uint8_t version) {
    LocationResponse res;
    res.version = version;
    res.packet_id = request.packet_id;
    res.type = 1;
    res.weather_flag = request.weather_flag;
    res.temperature_flag = request.temperature_flag;
    res.pop_flag = request.pop_flag;
    res.alert_flag = request.alert_flag;
    res.disaster_flag = request.disaster_flag;
    res.ex_flag = request.ex_flag;
    res.day = request.day;
    res.timestamp = static_cast<uint64_t>(std::time(nullptr));
    res.area_code = area_code;
    res.weather_code = 0;
    res.temperature = 0;
    res.pop = 0;
    res.ex_field = request.ex_field;
    return res;
}

} // namespace packet
} // namespace wip
