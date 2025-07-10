#include "ReportClient.hpp"
#include <cstdlib>
#include "../platform.hpp"
#include <sstream>
#include <iomanip>
#include <vector>
#include "../packet/types/ReportPacket.hpp"
#include "utils/Auth.hpp"

static wip::platform::SocketInitializer socket_init;
static std::string bytes_to_hex(const std::vector<unsigned char>& data) {
    std::ostringstream oss;
    for (unsigned char b : data) {
        oss << std::hex << std::setw(2) << std::setfill('0')
            << static_cast<int>(b);
    }
    return oss.str();
}

namespace wip {
namespace clients {

ReportClient::ReportClient(const std::string& host, int port, bool debug)
    : host_(host.empty() ? (std::getenv("WEATHER_SERVER_HOST") ? std::getenv("WEATHER_SERVER_HOST") : "localhost") : host),
      port_(port == 0 ? (std::getenv("WEATHER_SERVER_PORT") ? std::atoi(std::getenv("WEATHER_SERVER_PORT")) : 4110) : port),
      debug_(debug) {
    sock_ = ::socket(AF_INET, SOCK_DGRAM, 0);
    init_auth();
}

ReportClient::~ReportClient() {
    if (sock_ != wip::platform::invalid_socket)
        wip::platform::close_socket(sock_);
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
    sockaddr_in addr{};
    addr.sin_family = AF_INET;
    addr.sin_port = htons(port_);
    addr.sin_addr.s_addr = inet_addr(host_.c_str());

    auto req = wip::packet::ReportRequest::create_sensor_data_report(
        area_code_, weather_code_ >= 0 ? std::optional<int>(weather_code_) : std::nullopt,
        temperature_ != 0.0 ? std::optional<double>(temperature_) : std::nullopt,
        precipitation_prob_ >= 0 ? std::optional<int>(precipitation_prob_) : std::nullopt,
        alert_.empty() ? std::nullopt : std::optional<std::vector<std::string>>(alert_),
        disaster_.empty() ? std::nullopt : std::optional<std::vector<std::string>>(disaster_));
    if (auth_enabled_ && !auth_passphrase_.empty()) {
        req.request_auth = true;
        auto hash = WIPAuth::calculate_auth_hash(
            req.packet_id, req.timestamp, auth_passphrase_);
        req.ex_field.data["auth_hash"] = bytes_to_hex(hash);
    }
    auto bytes = req.to_bytes();
    sendto(sock_, reinterpret_cast<const char*>(bytes.data()), bytes.size(), 0,
           (sockaddr*)&addr, sizeof(addr));
    char buf[128]{};
    socklen_t len = sizeof(addr);
    ssize_t r = recvfrom(sock_, buf, sizeof(buf), 0, (sockaddr*)&addr, &len);
    std::unordered_map<std::string, std::string> result;
    if (r > 0) {
        std::vector<uint8_t> data(buf, buf + r);
        auto res = wip::packet::Response::from_bytes(data);
        result["area_code"] = res.area_code;
        result["packet_id"] = std::to_string(res.packet_id);
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
