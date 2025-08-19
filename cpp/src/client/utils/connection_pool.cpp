#include "wiplib/client/utils/connection_pool.hpp"
#include <arpa/inet.h>
#include <netdb.h>
#include <sys/socket.h>
#include <unistd.h>
#include <cstring>
#include <random>

namespace wiplib::client::utils {

UDPConnectionPool::UDPConnectionPool(const PoolConfig& config, ConnectionFactory factory, HealthChecker health_checker)
    : config_(config), connection_factory_(std::move(factory)), health_checker_(std::move(health_checker)) {
    running_ = true;
    maintenance_thread_ = std::make_unique<std::thread>(&UDPConnectionPool::maintenance_loop, this);
}

UDPConnectionPool::~UDPConnectionPool() { close(); }

std::shared_ptr<ConnectionInfo> UDPConnectionPool::acquire_connection(const std::string& host, uint16_t port, std::chrono::milliseconds timeout) {
    HostKey key{host, port};
    auto deadline = std::chrono::steady_clock::now() + timeout;
    std::unique_lock<std::mutex> lk(connections_mutex_);
    for (;;) {
        auto& vec = connections_[key];
        for (auto& c : vec) {
            if (!c->is_in_use && c->state == ConnectionState::Connected) {
                c->is_in_use = true;
                c->use_count++;
                c->last_used_time = std::chrono::steady_clock::now();
                stats_.successful_acquisitions++;
                return c;
            }
        }
        // create if capacity not reached
        if (vec.size() < config_.max_connections) {
            auto c = create_connection(host, port);
            if (c) {
                c->is_in_use = true;
                vec.push_back(c);
                stats_.connections_created++;
                stats_.successful_acquisitions++;
                return c;
            }
            stats_.failed_acquisitions++;
        }
        if (std::chrono::steady_clock::now() >= deadline) {
            stats_.failed_acquisitions++;
            return nullptr;
        }
        connection_available_cv_.wait_for(lk, std::chrono::milliseconds(50));
    }
}

void UDPConnectionPool::release_connection(std::shared_ptr<ConnectionInfo> connection) {
    std::lock_guard<std::mutex> lk(connections_mutex_);
    if (!connection) return;
    connection->is_in_use = false;
    connection->last_used_time = std::chrono::steady_clock::now();
    connection_available_cv_.notify_one();
}

std::vector<std::shared_ptr<ConnectionInfo>> UDPConnectionPool::acquire_multiple_connections(const std::string& host, uint16_t port, size_t max_connections) {
    std::vector<std::shared_ptr<ConnectionInfo>> out;
    out.reserve(max_connections);
    for (size_t i = 0; i < max_connections; ++i) {
        auto c = acquire_connection(host, port, std::chrono::milliseconds{1000});
        if (!c) break; out.push_back(c);
    }
    return out;
}

size_t UDPConnectionPool::warmup_connections(const std::string& host, uint16_t port, size_t count) {
    size_t created = 0;
    std::lock_guard<std::mutex> lk(connections_mutex_);
    HostKey key{host, port};
    auto& vec = connections_[key];
    for (size_t i = 0; i < count && vec.size() < config_.max_connections; ++i) {
        auto c = create_connection(host, port);
        if (c) { vec.push_back(c); stats_.connections_created++; created++; }
    }
    return created;
}

void UDPConnectionPool::invalidate_connection(std::shared_ptr<ConnectionInfo> connection, const std::string&) {
    if (!connection) return;
    std::lock_guard<std::mutex> lk(connections_mutex_);
    connection->state = ConnectionState::Error;
    close_connection(connection);
}

size_t UDPConnectionPool::invalidate_host_connections(const std::string& host, uint16_t port) {
    std::lock_guard<std::mutex> lk(connections_mutex_);
    HostKey key{host, port};
    auto it = connections_.find(key);
    if (it == connections_.end()) return 0;
    size_t removed = 0;
    for (auto& c : it->second) { close_connection(c); removed++; }
    connections_.erase(it);
    return removed;
}

size_t UDPConnectionPool::cleanup_idle_connections() { return 0; }
size_t UDPConnectionPool::cleanup_error_connections() { return 0; }

void UDPConnectionPool::update_connection_quality(const std::string& connection_id, double quality_score) {
    auto it = connection_by_id_.find(connection_id);
    if (it != connection_by_id_.end()) it->second->quality_score = quality_score;
}

void UDPConnectionPool::record_connection_error(const std::string& connection_id, const std::string&) {
    auto it = connection_by_id_.find(connection_id);
    if (it != connection_by_id_.end()) it->second->error_count++;
}

size_t UDPConnectionPool::perform_health_check() { return 0; }

PoolStats UDPConnectionPool::get_statistics() const { return stats_; }
size_t UDPConnectionPool::get_active_connection_count() const { return stats_.active_connections; }
size_t UDPConnectionPool::get_available_connection_count() const { return stats_.idle_connections; }
std::vector<std::pair<std::string, uint16_t>> UDPConnectionPool::get_active_hosts() const { return {}; }
void UDPConnectionPool::update_config(const PoolConfig& new_config) { config_ = new_config; }

void UDPConnectionPool::reset_pool() { std::lock_guard<std::mutex> lk(connections_mutex_); for (auto& [k, vec] : connections_) { for (auto& c : vec) close_connection(c);} connections_.clear(); }

std::unordered_map<std::string, std::string> UDPConnectionPool::get_debug_info() const { return {}; }
void UDPConnectionPool::set_debug_enabled(bool enabled) { debug_enabled_ = enabled; }

void UDPConnectionPool::close() {
    running_ = false;
    if (maintenance_thread_ && maintenance_thread_->joinable()) maintenance_thread_->join();
    reset_pool();
}

void UDPConnectionPool::maintenance_loop() { while (running_) { std::this_thread::sleep_for(std::chrono::seconds(1)); } }

std::shared_ptr<ConnectionInfo> UDPConnectionPool::create_connection(const std::string& host, uint16_t port) {
    int sock = -1;
    if (connection_factory_) sock = connection_factory_(host, port);
    if (sock < 0) {
        // default UDP connect
        sock = ::socket(AF_INET, SOCK_DGRAM, 0);
        if (sock < 0) return nullptr;
        struct sockaddr_in addr{}; addr.sin_family = AF_INET; addr.sin_port = htons(port);
        if (::inet_pton(AF_INET, host.c_str(), &addr.sin_addr) != 1) {
            struct addrinfo hints{}; hints.ai_family = AF_INET; hints.ai_socktype = SOCK_DGRAM; struct addrinfo* res=nullptr;
            if (getaddrinfo(host.c_str(), nullptr, &hints, &res) != 0 || !res) { ::close(sock); return nullptr; }
            auto* a = reinterpret_cast<sockaddr_in*>(res->ai_addr);
            addr.sin_addr = a->sin_addr; freeaddrinfo(res);
        }
        if (::connect(sock, reinterpret_cast<sockaddr*>(&addr), sizeof(addr)) != 0) { ::close(sock); return nullptr; }
    }
    auto c = std::make_shared<ConnectionInfo>();
    c->socket_fd = sock; c->host = host; c->port = port; c->state = ConnectionState::Connected; c->created_time = std::chrono::steady_clock::now();
    c->last_used_time = c->created_time; c->last_activity_time = c->created_time; c->connection_id = generate_connection_id();
    connection_by_id_[c->connection_id] = c;
    stats_.total_connections++; stats_.idle_connections++;
    return c;
}

bool UDPConnectionPool::validate_connection(std::shared_ptr<ConnectionInfo> connection) { return connection && connection->state == ConnectionState::Connected; }

void UDPConnectionPool::close_connection(std::shared_ptr<ConnectionInfo> connection) {
    if (!connection) return; if (connection->socket_fd >= 0) { ::close(connection->socket_fd); connection->socket_fd = -1; }
    connection->state = ConnectionState::Closed; stats_.connections_destroyed++;
}

std::string UDPConnectionPool::generate_connection_id() {
    static std::mt19937 rng{std::random_device{}()}; static const char* hex = "0123456789abcdef"; std::string s(12, '0'); for (char& c : s) c = hex[rng() & 0xF]; return s;
}

int UDPConnectionPool::default_connection_factory(const std::string& host, uint16_t port) { (void)host; (void)port; return -1; }
bool UDPConnectionPool::default_health_checker(int) { return true; }
void UDPConnectionPool::log_debug(const std::string&) {}
void UDPConnectionPool::update_connection_activity(std::shared_ptr<ConnectionInfo> c) { if (c) c->last_activity_time = std::chrono::steady_clock::now(); }
bool UDPConnectionPool::should_remove_connection(std::shared_ptr<ConnectionInfo>) { return false; }
size_t UDPConnectionPool::get_host_connection_count(const HostKey& key) const { auto it = connections_.find(key); return it==connections_.end()?0:it->second.size(); }
double UDPConnectionPool::calculate_connection_quality(std::shared_ptr<ConnectionInfo> c) const { return c?c->quality_score:0.0; }

// TCP wrapper
TCPConnectionPool::TCPConnectionPool(const PoolConfig& config, ConnectionFactory factory, HealthChecker health_checker)
    : impl_(std::make_unique<UDPConnectionPool>(config, std::move(factory), std::move(health_checker))) {}
TCPConnectionPool::~TCPConnectionPool() { close(); }
std::shared_ptr<ConnectionInfo> TCPConnectionPool::acquire_connection(const std::string& host, uint16_t port, std::chrono::milliseconds timeout) { return impl_->acquire_connection(host, port, timeout); }
void TCPConnectionPool::release_connection(std::shared_ptr<ConnectionInfo> connection) { impl_->release_connection(std::move(connection)); }
PoolStats TCPConnectionPool::get_statistics() const { return impl_->get_statistics(); }
void TCPConnectionPool::close() { impl_->close(); }

// Factory
std::unique_ptr<UDPConnectionPool> ConnectionPoolFactory::create_udp_pool() { return std::make_unique<UDPConnectionPool>(); }
std::unique_ptr<UDPConnectionPool> ConnectionPoolFactory::create_high_performance_udp_pool() { PoolConfig c; c.max_connections = 1000; return std::make_unique<UDPConnectionPool>(c); }
std::unique_ptr<UDPConnectionPool> ConnectionPoolFactory::create_low_resource_udp_pool() { PoolConfig c; c.max_connections = 10; return std::make_unique<UDPConnectionPool>(c); }
std::unique_ptr<TCPConnectionPool> ConnectionPoolFactory::create_tcp_pool() { return std::make_unique<TCPConnectionPool>(); }
std::unique_ptr<UDPConnectionPool> ConnectionPoolFactory::create_custom_udp_pool(const PoolConfig& config, ConnectionFactory factory, HealthChecker health_checker) { return std::make_unique<UDPConnectionPool>(config, std::move(factory), std::move(health_checker)); }

} // namespace wiplib::client::utils
