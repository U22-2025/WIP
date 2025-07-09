#include "ReportClient.hpp"
#include <cstdlib>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <unistd.h>

namespace wip {
namespace clients {

ReportClient::ReportClient(const std::string& host, int port, bool debug)
    : host_(host.empty() ? (std::getenv("WEATHER_SERVER_HOST") ? std::getenv("WEATHER_SERVER_HOST") : "localhost") : host),
      port_(port == 0 ? (std::getenv("WEATHER_SERVER_PORT") ? std::atoi(std::getenv("WEATHER_SERVER_PORT")) : 4110) : port),
      debug_(debug) {
    sock_ = socket(AF_INET, SOCK_DGRAM, 0);
    init_auth();
}

ReportClient::~ReportClient() {
    if (sock_ >= 0) ::close(sock_);
}

void ReportClient::init_auth() {
    const char* enabled = std::getenv("REPORT_SERVER_REQUEST_AUTH_ENABLED");
    auth_enabled_ = enabled && std::string(enabled) == "true";
    const char* pass = std::getenv("REPORT_SERVER_PASSPHRASE");
    if (pass) auth_passphrase_ = pass;
}

void ReportClient::set_sensor_data(const std::string& area_code, int weather_code,
                                   double temperature, int precipitation_prob,
                                   const std::vector<std::string>& alert,
                                   const std::vector<std::string>& disaster) {
    area_code_ = area_code;
    weather_code_ = weather_code;
    temperature_ = temperature;
    precipitation_prob_ = precipitation_prob;
    alert_ = alert;
    disaster_ = disaster;
}

std::unordered_map<std::string, std::string> ReportClient::send_report_data() {
    // TODO: build packet from stored data and send
    sockaddr_in addr{};
    addr.sin_family = AF_INET;
    addr.sin_port = htons(port_);
    addr.sin_addr.s_addr = inet_addr(host_.c_str());
    sendto(sock_, "", 0, 0, (sockaddr*)&addr, sizeof(addr));
    char buf[128]{};
    socklen_t len = sizeof(addr);
    ssize_t r = recvfrom(sock_, buf, sizeof(buf), 0, (sockaddr*)&addr, &len);
    std::unordered_map<std::string, std::string> result;
    if (r > 0) {
        result["response"] = std::string(buf, r);
    }
    return result;
}

std::unordered_map<std::string, std::string> ReportClient::send_data_simple() {
    return send_report_data();
}

std::unordered_map<std::string, std::string> ReportClient::get_current_data() const {
    return {
        {"area_code", area_code_},
        {"weather_code", std::to_string(weather_code_)},
        {"temperature", std::to_string(temperature_)},
        {"precipitation_prob", std::to_string(precipitation_prob_)}
    };
}

void ReportClient::clear_data() {
    area_code_.clear();
    weather_code_ = -1;
    temperature_ = 0.0;
    precipitation_prob_ = -1;
    alert_.clear();
    disaster_.clear();
}

} // namespace clients
} // namespace wip
