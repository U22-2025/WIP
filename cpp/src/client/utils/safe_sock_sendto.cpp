#include "wiplib/client/utils/safe_sock_sendto.hpp"
#ifdef _WIN32
    #include <ws2tcpip.h>
    using ssize_t = long long;
#else
    #include <arpa/inet.h>
    #include <netdb.h>
    #include <sys/socket.h>
    #include <unistd.h>
#endif
#include <cstring>
#include <future>

namespace wiplib::client::utils {

SafeSockSendTo::SafeSockSendTo(int socket_fd, const SendConfig& config)
    : socket_fd_(socket_fd), config_(config) {}

SafeSockSendTo::~SafeSockSendTo() { close(); }

SendResult SafeSockSendTo::send_sync(const std::vector<uint8_t>& data, const struct sockaddr_in& destination) {
    SendResult r{};
    auto start = std::chrono::steady_clock::now();
    ssize_t sent = ::sendto(socket_fd_, reinterpret_cast<const char*>(data.data()), static_cast<int>(data.size()), 0,
                            reinterpret_cast<const struct sockaddr*>(&destination), sizeof(destination));
    if (sent < 0) {
        r.error_type = SendErrorType::NetworkError;
        r.error_message = std::strerror(errno);
        stats_.failed_sends++;
    } else {
        r.error_type = SendErrorType::Success;
        r.bytes_sent = sent;
        stats_.successful_sends++;
        stats_.bytes_sent += static_cast<uint64_t>(sent);
    }
    r.send_time = std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::steady_clock::now() - start);
    stats_.total_sends++;
    stats_.total_send_time_ms += static_cast<uint64_t>(r.send_time.count());
    return r;
}

std::future<SendResult> SafeSockSendTo::send_async(const std::vector<uint8_t>& data,
                                                   const struct sockaddr_in& destination,
                                                   std::chrono::milliseconds /*timeout*/) {
    return std::async(std::launch::async, [this, data, destination]() {
        return this->send_sync(data, destination);
    });
}

std::vector<std::future<SendResult>> SafeSockSendTo::send_multiple(
    const std::vector<std::pair<std::vector<uint8_t>, struct sockaddr_in>>& send_items,
    size_t /*max_concurrent*/) {
    std::vector<std::future<SendResult>> futs;
    futs.reserve(send_items.size());
    for (const auto& it : send_items) {
        futs.emplace_back(send_async(it.first, it.second));
    }
    return futs;
}

SendResult SafeSockSendTo::broadcast_send(const std::vector<uint8_t>& data, uint16_t port, const std::string& interface_addr) {
    struct sockaddr_in addr{};
    addr.sin_family = AF_INET;
    addr.sin_port = htons(port);
    addr.sin_addr.s_addr = inet_addr(interface_addr.empty() ? "255.255.255.255" : interface_addr.c_str());
    int opt = 1; wiplib::utils::platform_setsockopt(socket_fd_, SOL_SOCKET, SO_BROADCAST, &opt, sizeof(opt));
    return send_sync(data, addr);
}

SendResult SafeSockSendTo::multicast_send(const std::vector<uint8_t>& data, const std::string& multicast_addr, uint16_t port, uint8_t /*ttl*/) {
    struct sockaddr_in addr{};
    addr.sin_family = AF_INET;
    addr.sin_port = htons(port);
    addr.sin_addr.s_addr = inet_addr(multicast_addr.c_str());
    return send_sync(data, addr);
}

size_t SafeSockSendTo::get_queue_size() const { return 0; }
void SafeSockSendTo::set_max_queue_size(size_t) {}
void SafeSockSendTo::set_paused(bool) {}
size_t SafeSockSendTo::cancel_all_pending() { return 0; }
bool SafeSockSendTo::cancel_operation(const std::string&) { return false; }

SendStats SafeSockSendTo::get_statistics() const { return stats_; }

std::unordered_map<std::string, double> SafeSockSendTo::get_performance_metrics() const {
    return {
        {"bytes_per_ms", stats_.total_send_time_ms ? static_cast<double>(stats_.bytes_sent.load()) / static_cast<double>(stats_.total_send_time_ms.load()) : 0.0}
    };
}

bool SafeSockSendTo::optimize_socket_options() { return true; }
int SafeSockSendTo::get_send_buffer_size() const { int sz=0; socklen_t l=sizeof(sz); wiplib::utils::platform_getsockopt(socket_fd_, SOL_SOCKET, SO_SNDBUF, &sz, &l); return sz; }
bool SafeSockSendTo::set_send_buffer_size(int size) { return wiplib::utils::platform_setsockopt(socket_fd_, SOL_SOCKET, SO_SNDBUF, &size, sizeof(size)) == 0; }

double SafeSockSendTo::measure_network_quality(const struct sockaddr_in& destination, size_t test_data_size) {
    std::vector<uint8_t> data(test_data_size, 0xAA);
    auto res = send_sync(data, destination);
    if (res.error_type != SendErrorType::Success) return 0.0;
    return 1.0;
}

void SafeSockSendTo::set_debug_enabled(bool) {}

void SafeSockSendTo::close() {}

} // namespace wiplib::client::utils

