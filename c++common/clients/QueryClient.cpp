#include "QueryClient.hpp"
#include <cstdlib>
#include <cstring>
#include <chrono>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <unistd.h>
#include <iostream>

namespace wip {
namespace clients {

QueryClient::QueryClient(const std::string& host, int port, bool debug,
                         int cache_ttl_minutes)
    : host_(host.empty() ? (std::getenv("QUERY_GENERATOR_HOST") ? std::getenv("QUERY_GENERATOR_HOST") : "localhost") : host),
      port_(port == 0 ? (std::getenv("QUERY_GENERATOR_PORT") ? std::atoi(std::getenv("QUERY_GENERATOR_PORT")) : 4112) : port),
      debug_(debug),
      cache_(std::chrono::minutes(cache_ttl_minutes)) {
    init_auth();
}

void QueryClient::init_auth() {
    const char* enabled = std::getenv("QUERY_GENERATOR_REQUEST_AUTH_ENABLED");
    auth_enabled_ = enabled && std::string(enabled) == "true";
    const char* pass = std::getenv("QUERY_SERVER_PASSPHRASE");
    if (pass) auth_passphrase_ = pass;
}

void QueryClient::close() {}

std::unordered_map<std::string, std::string> QueryClient::get_weather_data(
    const std::string& area_code, bool weather, bool temperature,
    bool precipitation_prob, bool alert, bool disaster,
    const std::pair<std::string, int>* /*source*/, double timeout,
    bool use_cache, int day, bool force_refresh) {
    std::unordered_map<std::string, std::string> result;
    std::string cache_key = "query:" + area_code + ":" + std::to_string(weather) +
                            std::to_string(temperature) +
                            std::to_string(precipitation_prob) +
                            std::to_string(alert) + std::to_string(disaster) +
                            ":" + std::to_string(day);
    std::string cached;
    if (use_cache && !force_refresh && cache_.get(cache_key, cached)) {
        result["source"] = "cache";
        result["data"] = cached;
        return result;
    }

    int sock = socket(AF_INET, SOCK_DGRAM, 0);
    if (sock < 0) return result;
    struct timeval tv{0};
    tv.tv_sec = static_cast<int>(timeout);
    tv.tv_usec = 0;
    setsockopt(sock, SOL_SOCKET, SO_RCVTIMEO, &tv, sizeof(tv));

    sockaddr_in addr{};
    addr.sin_family = AF_INET;
    addr.sin_port = htons(port_);
    addr.sin_addr.s_addr = inet_addr(host_.c_str());

    // TODO: construct request packet
    // Placeholder: send empty packet
    sendto(sock, "", 0, 0, (sockaddr*)&addr, sizeof(addr));

    char buf[1024]{};
    socklen_t len = sizeof(addr);
    ssize_t r = recvfrom(sock, buf, sizeof(buf), 0, (sockaddr*)&addr, &len);
    if (r > 0) {
        // TODO: parse response
        result["source"] = "network";
        result["data"] = std::string(buf, r);
        if (use_cache)
            cache_.set(cache_key, result["data"]);
    }

    ::close(sock);
    return result;
}

std::unordered_map<std::string, std::string> QueryClient::get_weather_simple(
    const std::string& area_code, bool include_all, double timeout,
    bool use_cache) {
    return get_weather_data(area_code, true, true, true, include_all, include_all,
                            nullptr, timeout, use_cache, 0, false);
}

std::unordered_map<std::string, std::string> QueryClient::get_cache_stats() const {
    return {
        {"cache_size", std::to_string(cache_.size())}
    };
}

void QueryClient::clear_cache() { cache_.clear(); }

} // namespace clients
} // namespace wip
