#include "WeatherClient.hpp"
#include <cstdlib>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <unistd.h>

namespace wip {
namespace clients {

WeatherClient::WeatherClient(const std::string& host, int port, bool debug)
    : host_(host.empty() ? (std::getenv("WEATHER_SERVER_HOST") ? std::getenv("WEATHER_SERVER_HOST") : "localhost") : host),
      port_(port == 0 ? (std::getenv("WEATHER_SERVER_PORT") ? std::atoi(std::getenv("WEATHER_SERVER_PORT")) : 4110) : port),
      debug_(debug) {
    sock_ = socket(AF_INET, SOCK_DGRAM, 0);
}

WeatherClient::~WeatherClient() {
    if (sock_ >= 0) ::close(sock_);
}

std::unordered_map<std::string, std::string> WeatherClient::get_weather_data(
    const std::string& area_code, bool weather, bool temperature,
    bool precipitation_prob, bool alert, bool disaster, int day) {
    // TODO: send request and parse response
    (void)area_code; (void)weather; (void)temperature; (void)precipitation_prob;
    (void)alert; (void)disaster; (void)day;
    return {};
}

std::unordered_map<std::string, std::string> WeatherClient::get_weather_simple(
    const std::string& area_code, bool include_all, int day) {
    return get_weather_data(area_code, true, true, true, include_all, include_all, day);
}

} // namespace clients
} // namespace wip
