#ifndef WIP_CLIENTS_WEATHERCLIENT_HPP
#define WIP_CLIENTS_WEATHERCLIENT_HPP

#include <string>
#include <unordered_map>
#include "utils/PacketIDGenerator.hpp"

namespace wip {
namespace clients {

class WeatherClient {
public:
    WeatherClient(const std::string& host = "", int port = 0, bool debug = false);
    ~WeatherClient();
    std::unordered_map<std::string, std::string> get_weather_data(
        const std::string& area_code,
        bool weather = true,
        bool temperature = true,
        bool precipitation_prob = true,
        bool alert = false,
        bool disaster = false,
        int day = 0);
    std::unordered_map<std::string, std::string> get_weather_simple(
        const std::string& area_code, bool include_all = false, int day = 0);
private:
    std::string host_;
    int port_;
    bool debug_;
    int version_ = 1;
    utils::PacketIDGenerator12Bit pidg_;
    int sock_ = -1;
};

} // namespace clients
} // namespace wip

#endif // WIP_CLIENTS_WEATHERCLIENT_HPP
