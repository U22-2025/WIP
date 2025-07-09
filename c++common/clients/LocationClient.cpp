#include "LocationClient.hpp"
#include <cstdlib>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <unistd.h>

namespace wip {
namespace clients {

LocationClient::LocationClient(const std::string& host, int port, bool debug,
                               int cache_ttl_minutes)
    : host_(host.empty() ? (std::getenv("LOCATION_RESOLVER_HOST") ? std::getenv("LOCATION_RESOLVER_HOST") : "localhost") : host),
      port_(port == 0 ? (std::getenv("LOCATION_RESOLVER_PORT") ? std::atoi(std::getenv("LOCATION_RESOLVER_PORT")) : 4111) : port),
      debug_(debug),
      cache_("coordinate_cache.txt", std::chrono::minutes(cache_ttl_minutes)) {
    sock_ = socket(AF_INET, SOCK_DGRAM, 0);
    init_auth();
}

LocationClient::~LocationClient() {
    if (sock_ >= 0) ::close(sock_);
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
    // TODO: send request packet
    (void)weather; (void)temperature; (void)precipitation_prob; (void)alert; (void)disaster; (void)day;

    // Placeholder network interaction
    sockaddr_in addr{};
    addr.sin_family = AF_INET;
    addr.sin_port = htons(port_);
    addr.sin_addr.s_addr = inet_addr(host_.c_str());
    sendto(sock_, "", 0, 0, (sockaddr*)&addr, sizeof(addr));
    char buf[128]{};
    socklen_t len = sizeof(addr);
    ssize_t r = recvfrom(sock_, buf, sizeof(buf), 0, (sockaddr*)&addr, &len);
    if (r > 0) {
        area.assign(buf, r);
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
