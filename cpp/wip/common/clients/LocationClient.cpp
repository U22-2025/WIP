#include "LocationClient.hpp"
#include <cstdlib>
#include "../platform.hpp"
#include <sstream>
#include <iomanip>
#include <vector>
#include "../packet/types/LocationPacket.hpp"
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

LocationClient::LocationClient(const std::string& host, int port, bool debug,
                               int cache_ttl_minutes)
    : host_(host.empty() ? (std::getenv("LOCATION_RESOLVER_HOST") ? std::getenv("LOCATION_RESOLVER_HOST") : "localhost") : host),
      port_(port == 0 ? (std::getenv("LOCATION_RESOLVER_PORT") ? std::atoi(std::getenv("LOCATION_RESOLVER_PORT")) : 4111) : port),
      debug_(debug),
      cache_("coordinate_cache.txt",
             std::chrono::minutes(cache_ttl_minutes)) {
    sock_ = ::socket(AF_INET, SOCK_DGRAM, 0);
    init_auth();
}

LocationClient::~LocationClient() {
    if (sock_ != wip::platform::invalid_socket)
        wip::platform::close_socket(sock_);
}

void LocationClient::init_auth() {
    const char* enabled = std::getenv("LOCATION_RESOLVER_REQUEST_AUTH_ENABLED");
    auth_enabled_ = enabled && std::string(enabled) == "true";
    const char* pass = std::getenv("LOCATION_SERVER_PASSPHRASE");
    if (pass) auth_passphrase_ = pass;
}

std::pair<std::string, double> LocationClient::get_location_data(
    double latitude, double longitude, bool use_cache, bool weather,
    bool temperature, bool precipitation_prob, bool alert, bool disaster, int day,
    bool force_refresh) {
    std::string key = "coord:" + std::to_string(latitude) + "," + std::to_string(longitude);
    std::string area;
    if (use_cache && !force_refresh && cache_.get(key, area)) {
        return {area, 0.0};
    }

    sockaddr_in addr{};
    addr.sin_family = AF_INET;
    addr.sin_port = htons(port_);
    addr.sin_addr.s_addr = inet_addr(host_.c_str());

    auto req = wip::packet::LocationRequest::create_coordinate_lookup(
        latitude, longitude, pidg_.next_id(), weather, temperature,
        precipitation_prob, alert, disaster, std::nullopt,
        static_cast<uint8_t>(day));
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
    if (r > 0) {
        std::vector<uint8_t> data(buf, buf + r);
        auto res = wip::packet::Response::from_bytes(data);
        area = res.area_code;
        if (use_cache) cache_.set(key, area);
    }
    return {area, 0.0};
}

std::string LocationClient::get_area_code_simple(double latitude, double longitude,
                                                 bool use_cache) {
    auto pair = get_location_data(latitude, longitude, use_cache);
    return pair.first;
}

void LocationClient::clear_cache() { cache_.clear(); }

std::unordered_map<std::string, std::string> LocationClient::get_cache_stats() const {
    return {
        {"cache_size", std::to_string(cache_.size())}
    };
}

} // namespace clients
} // namespace wip
