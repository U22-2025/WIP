#include "QueryClient.hpp"
#include <cstdlib>
#include <cstring>
#include <chrono>
#include "../platform.hpp"
#include <iostream>
#include <sstream>
#include <iomanip>
#include <vector>
#include <cerrno>
#ifdef _WIN32
#include <winsock2.h>
#endif
#include "../packet/types/QueryPacket.hpp"
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
        std::vector<uint8_t> bytes(cached.begin(), cached.end());
        auto res = wip::packet::Response::from_bytes(bytes);
        result["source"] = "cache";
        result["area_code"] = res.area_code;
        if (res.weather_flag)
            result["weather_code"] = std::to_string(res.weather_code);
        if (res.temperature_flag)
            result["temperature"] = std::to_string((int)res.temperature - 100);
        if (res.pop_flag)
            result["precipitation_prob"] = std::to_string(res.pop);
        return result;
    }

    wip::platform::socket_t sock = ::socket(AF_INET, SOCK_DGRAM, 0);
    if (sock == wip::platform::invalid_socket) {
        if (debug_) std::cerr << "[QueryClient] socket creation failed" << std::endl;
        result["error"] = "socket";
        return result;
    }
#ifdef _WIN32
    DWORD timeout_ms = static_cast<DWORD>(timeout * 1000);
    setsockopt(sock, SOL_SOCKET, SO_RCVTIMEO,
               reinterpret_cast<const char*>(&timeout_ms), sizeof(timeout_ms));
#else
    struct timeval tv{0};
    tv.tv_sec = static_cast<int>(timeout);
    tv.tv_usec = 0;
    setsockopt(sock, SOL_SOCKET, SO_RCVTIMEO, &tv, sizeof(tv));
#endif

    sockaddr_in addr{};
    addr.sin_family = AF_INET;
    addr.sin_port = htons(port_);
    addr.sin_addr.s_addr = inet_addr(host_.c_str());

    auto req = wip::packet::QueryRequest::create_query_request(
        area_code, pidg_.next_id(), weather, temperature,
        precipitation_prob, alert, disaster, static_cast<uint8_t>(day));
    if (auth_enabled_ && !auth_passphrase_.empty()) {
        req.request_auth = true;
        auto hash = WIPAuth::calculate_auth_hash(
            req.packet_id, req.timestamp, auth_passphrase_);
        req.ex_field.data["auth_hash"] = bytes_to_hex(hash);
    }
    auto bytes = req.to_bytes();
    ssize_t s = sendto(sock, reinterpret_cast<const char*>(bytes.data()), bytes.size(), 0,
           (sockaddr*)&addr, sizeof(addr));
    if (s < 0) {
        if (debug_) {
#ifdef _WIN32
            std::cerr << "[QueryClient] sendto failed: " << WSAGetLastError() << std::endl;
#else
            std::cerr << "[QueryClient] sendto failed: " << strerror(errno) << std::endl;
#endif
        }
        result["error"] = "send";
        wip::platform::close_socket(sock);
        return result;
    }

    char buf[1024]{};
    socklen_t len = sizeof(addr);
    ssize_t r = recvfrom(sock, buf, sizeof(buf), 0, (sockaddr*)&addr, &len);
    if (r > 0) {
        std::vector<uint8_t> data(buf, buf + r);
        auto res = wip::packet::Response::from_bytes(data);
        result["source"] = "network";
        result["area_code"] = res.area_code;
        if (res.weather_flag)
            result["weather_code"] = std::to_string(res.weather_code);
        if (res.temperature_flag)
            result["temperature"] = std::to_string((int)res.temperature - 100);
        if (res.pop_flag)
            result["precipitation_prob"] = std::to_string(res.pop);
        if (use_cache) {
            std::string store(reinterpret_cast<char*>(data.data()), data.size());
            cache_.set(cache_key, store);
        }
    } else {
        if (debug_) {
#ifdef _WIN32
            std::cerr << "[QueryClient] recvfrom failed: " << WSAGetLastError() << std::endl;
#else
            std::cerr << "[QueryClient] recvfrom failed: " << strerror(errno) << std::endl;
#endif
        }
        result["error"] = "recv";
    }

    wip::platform::close_socket(sock);
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
