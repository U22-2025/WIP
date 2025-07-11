#include "WeatherClient.hpp"
#include <cstdlib>
#include "../platform.hpp"
#include <vector>
#include "../packet/types/QueryPacket.hpp"
#include "../utils/NetUtils.hpp"

static wip::platform::SocketInitializer socket_init;

namespace wip {
namespace clients {

WeatherClient::WeatherClient(const std::string& host, int port, bool debug)
    : host_(host.empty() ? (std::getenv("WEATHER_SERVER_HOST") ? std::getenv("WEATHER_SERVER_HOST") : "localhost") : host),
      port_(port == 0 ? (std::getenv("WEATHER_SERVER_PORT") ? std::atoi(std::getenv("WEATHER_SERVER_PORT")) : 4110) : port),
      debug_(debug) {
    sock_ = ::socket(AF_INET, SOCK_DGRAM, 0);
}

WeatherClient::~WeatherClient() {
    if (sock_ != wip::platform::invalid_socket)
        wip::platform::close_socket(sock_);
}

std::unordered_map<std::string, std::string> WeatherClient::get_weather_data(
    const std::string& area_code, bool weather, bool temperature,
    bool precipitation_prob, bool alert, bool disaster, int day) {
    std::unordered_map<std::string, std::string> result;
    sockaddr_in addr{};
    addr.sin_family = AF_INET;
    addr.sin_port = htons(port_);
    addr.sin_addr = wip::utils::resolve_hostname(host_);

    auto req = wip::packet::QueryRequest::create_query_request(
        area_code, pidg_.next_id(), weather, temperature,
        precipitation_prob, alert, disaster, static_cast<uint8_t>(day));
    auto bytes = req.to_bytes();
    sendto(sock_, reinterpret_cast<const char*>(bytes.data()), bytes.size(), 0,
           (sockaddr*)&addr, sizeof(addr));

    char buf[1024]{};
    socklen_t len = sizeof(addr);
    ssize_t r = recvfrom(sock_, buf, sizeof(buf), 0, (sockaddr*)&addr, &len);
    if (r > 0) {
        std::vector<uint8_t> data(buf, buf + r);
        auto res = wip::packet::Response::from_bytes(data);
        result["area_code"] = res.area_code;
        if (res.weather_flag)
            result["weather_code"] = std::to_string(res.weather_code);
        if (res.temperature_flag)
            result["temperature"] = std::to_string((int)res.temperature - 100);
        if (res.pop_flag)
            result["precipitation_prob"] = std::to_string(res.pop);
    }
    return result;
}

std::unordered_map<std::string, std::string> WeatherClient::get_weather_simple(
    const std::string& area_code, bool include_all, int day) {
    return get_weather_data(area_code, true, true, true, include_all, include_all, day);
}

} // namespace clients
} // namespace wip
