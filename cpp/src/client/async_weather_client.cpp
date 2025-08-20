#include "wiplib/client/async_weather_client.hpp"
#include "wiplib/packet/request.hpp"
#include "wiplib/packet/response.hpp"
#include "wiplib/packet/extended_field.hpp"
#include "wiplib/utils/platform_compat.hpp"
#include <cstring>
#include <random>
#include <sstream>
#include <iomanip>
#include <iostream>

namespace wiplib::client {

// ConnectionPool implementation
ConnectionPool::ConnectionPool(size_t max_connections) 
    : max_connections_(max_connections) {
    connections_.reserve(max_connections);
}

ConnectionPool::~ConnectionPool() {
    close_all();
}

int ConnectionPool::acquire_connection(const std::string& host, uint16_t port) {
    std::lock_guard<std::mutex> lock(mutex_);
    
    // 既存の利用可能な接続を探す
    for (auto& conn : connections_) {
        if (!conn.in_use && conn.host == host && conn.port == port) {
            if (is_connection_valid(conn.socket_fd)) {
                conn.in_use = true;
                conn.last_used = std::chrono::steady_clock::now();
                return conn.socket_fd;
            } else {
                // 無効な接続を削除
                platform_close_socket(conn.socket_fd);
                conn.socket_fd = -1;
            }
        }
    }
    
    // 新しい接続を作成
    int sock = socket(AF_INET, SOCK_DGRAM, 0);
    if (sock < 0) {
        return -1;
    }
    
    struct sockaddr_in server_addr;
    memset(&server_addr, 0, sizeof(server_addr));
    server_addr.sin_family = AF_INET;
    server_addr.sin_port = htons(port);
    
    struct hostent* server = gethostbyname(host.c_str());
    if (!server) {
        platform_close_socket(sock);
        return -1;
    }
    
    memcpy(&server_addr.sin_addr.s_addr, server->h_addr, server->h_length);
    
    if (connect(sock, (struct sockaddr*)&server_addr, sizeof(server_addr)) < 0) {
        platform_close_socket(sock);
        return -1;
    }
    
    // プールに追加
    if (connections_.size() < max_connections_) {
        connections_.push_back({
            sock, host, port, 
            std::chrono::steady_clock::now(), 
            true
        });
    }
    
    return sock;
}

void ConnectionPool::release_connection(int socket_fd) {
    std::lock_guard<std::mutex> lock(mutex_);
    
    for (auto& conn : connections_) {
        if (conn.socket_fd == socket_fd) {
            conn.in_use = false;
            conn.last_used = std::chrono::steady_clock::now();
            break;
        }
    }
}

void ConnectionPool::close_all() {
    std::lock_guard<std::mutex> lock(mutex_);
    
    for (auto& conn : connections_) {
        if (conn.socket_fd >= 0) {
            platform_close_socket(conn.socket_fd);
        }
    }
    connections_.clear();
}

size_t ConnectionPool::get_active_connections() const {
    std::lock_guard<std::mutex> lock(mutex_);
    return std::count_if(connections_.begin(), connections_.end(),
                        [](const Connection& conn) { return conn.in_use; });
}

size_t ConnectionPool::get_available_connections() const {
    std::lock_guard<std::mutex> lock(mutex_);
    return std::count_if(connections_.begin(), connections_.end(),
                        [](const Connection& conn) { return !conn.in_use; });
}

bool ConnectionPool::is_connection_valid(int socket_fd) const {
    int error = 0;
    socklen_t len = sizeof(error);
    int retval = wiplib::utils::platform_getsockopt(socket_fd, SOL_SOCKET, SO_ERROR, &error, &len);
    return (retval == 0 && error == 0);
}

// AsyncWeatherClient implementation
AsyncWeatherClient::AsyncWeatherClient(const std::string& host, uint16_t port, size_t max_concurrent_requests)
    : host_(host), port_(port), max_concurrent_requests_(max_concurrent_requests) {
    
    connection_pool_ = std::make_unique<ConnectionPool>(max_concurrent_requests / 2);
    worker_thread_ = std::make_unique<std::thread>(&AsyncWeatherClient::worker_loop, this);
}

AsyncWeatherClient::~AsyncWeatherClient() {
    close();
}

AsyncResult<WeatherData> AsyncWeatherClient::get_weather_async(uint32_t area_code, 
                                                              std::chrono::milliseconds timeout) {
    // キャッシュチェック
    if (cache_enabled_) {
        auto cached_data = get_cached_data(area_code);
        if (cached_data) {
            std::promise<WeatherData> promise;
            auto future = promise.get_future();
            promise.set_value(*cached_data);
            
            return AsyncResult<WeatherData>{
                std::move(future),
                generate_request_id(),
                std::chrono::steady_clock::now(),
                timeout
            };
        }
    }
    
    // リクエスト作成
    auto context = std::make_unique<RequestContext>();
    context->request_id = generate_request_id();
    context->start_time = std::chrono::steady_clock::now();
    context->timeout = timeout;
    context->retry_count = 0;
    
    // パケット作成
    context->request.set_header(
        packet::request_utils::generate_packet_id(),
        proto::PacketType::WeatherRequest,
        area_code
    );
    context->request.set_current_timestamp();
    context->request.calculate_and_set_checksum();
    
    auto future = context->promise.get_future();
    auto request_id = context->request_id;
    
    // リクエストキューに追加
    {
        std::lock_guard<std::mutex> lock(queue_mutex_);
        request_queue_.push(std::move(context));
    }
    queue_cv_.notify_one();
    
    stats_.total_requests++;
    
    return AsyncResult<WeatherData>{
        std::move(future),
        request_id,
        std::chrono::steady_clock::now(),
        timeout
    };
}

AsyncResult<WeatherData> AsyncWeatherClient::get_weather_by_coordinates_async(
    float latitude, float longitude, std::chrono::milliseconds timeout) {
    
    auto context = std::make_unique<RequestContext>();
    context->request_id = generate_request_id();
    context->start_time = std::chrono::steady_clock::now();
    context->timeout = timeout;
    context->retry_count = 0;
    
    // 座標を拡張フィールドに追加
    packet::ExtendedCoordinate coord{latitude, longitude};
    auto& mutable_packet = const_cast<proto::Packet&>(context->request.get_packet());
    packet::ExtendedFieldManager::add_field(
        mutable_packet,
        packet::ExtendedFieldKey::Coordinate,
        coord
    );
    
    context->request.set_header(
        packet::request_utils::generate_packet_id(),
        proto::PacketType::CoordinateRequest
    );
    context->request.set_current_timestamp();
    context->request.calculate_and_set_checksum();
    
    auto future = context->promise.get_future();
    auto request_id = context->request_id;
    
    {
        std::lock_guard<std::mutex> lock(queue_mutex_);
        request_queue_.push(std::move(context));
    }
    queue_cv_.notify_one();
    
    stats_.total_requests++;
    
    return AsyncResult<WeatherData>{
        std::move(future),
        request_id,
        std::chrono::steady_clock::now(),
        timeout
    };
}

std::vector<AsyncResult<WeatherData>> AsyncWeatherClient::get_multiple_weather_async(
    const std::vector<uint32_t>& area_codes, std::chrono::milliseconds timeout) {
    
    std::vector<AsyncResult<WeatherData>> results;
    results.reserve(area_codes.size());
    
    for (uint32_t area_code : area_codes) {
        results.push_back(get_weather_async(area_code, timeout));
    }
    
    return results;
}

void AsyncWeatherClient::set_cache_enabled(bool enabled, std::chrono::seconds default_ttl) {
    cache_enabled_ = enabled;
    default_cache_ttl_ = default_ttl;
    
    if (!enabled) {
        clear_cache();
    }
}

void AsyncWeatherClient::set_retry_policy(uint8_t max_retries, 
                                         std::chrono::milliseconds base_delay,
                                         std::chrono::milliseconds max_delay) {
    max_retries_ = max_retries;
    base_retry_delay_ = base_delay;
    max_retry_delay_ = max_delay;
}

void AsyncWeatherClient::set_debug_enabled(bool enabled) {
    debug_enabled_ = enabled;
}

ConnectionStats AsyncWeatherClient::get_stats() const {
    ConnectionStats result;
    result.total_requests = stats_.total_requests.load();
    result.successful_requests = stats_.successful_requests.load();
    result.failed_requests = stats_.failed_requests.load();
    result.timeout_requests = stats_.timeout_requests.load();
    result.retry_count = stats_.retry_count.load();
    result.bytes_sent = stats_.bytes_sent.load();
    result.bytes_received = stats_.bytes_received.load();
    result.connection_start_time = stats_.connection_start_time;
    return result;
}

void AsyncWeatherClient::clear_cache() {
    std::lock_guard<std::mutex> lock(cache_mutex_);
    cache_.clear();
}

void AsyncWeatherClient::cancel_all_requests() {
    std::lock_guard<std::mutex> lock(active_requests_mutex_);
    for (auto& [id, context] : active_requests_) {
        context->promise.set_exception(
            std::make_exception_ptr(std::runtime_error("Request cancelled"))
        );
    }
    active_requests_.clear();
}

void AsyncWeatherClient::close() {
    running_ = false;
    queue_cv_.notify_all();
    
    if (worker_thread_ && worker_thread_->joinable()) {
        worker_thread_->join();
    }
    
    cancel_all_requests();
    
    if (connection_pool_) {
        connection_pool_->close_all();
    }
}

void AsyncWeatherClient::worker_loop() {
    while (running_) {
        std::unique_ptr<RequestContext> context;
        
        {
            std::unique_lock<std::mutex> lock(queue_mutex_);
            queue_cv_.wait(lock, [this] { return !request_queue_.empty() || !running_; });
            
            if (!running_) break;
            
            if (!request_queue_.empty()) {
                context = std::move(request_queue_.front());
                request_queue_.pop();
            }
        }
        
        if (context) {
            process_request(std::move(context));
        }
    }
}

void AsyncWeatherClient::process_request(std::unique_ptr<RequestContext> context) {
    try {
        log_debug("Processing request: " + context->request_id);
        
        // タイムアウトチェック
        auto elapsed = std::chrono::steady_clock::now() - context->start_time;
        if (elapsed > context->timeout) {
            stats_.timeout_requests++;
            context->promise.set_exception(
                std::make_exception_ptr(std::runtime_error("Request timeout"))
            );
            return;
        }
        
        // アクティブリクエストに追加
        {
            std::lock_guard<std::mutex> lock(active_requests_mutex_);
            active_requests_[context->request_id] = std::move(context);
        }
        
        // リクエスト送信
        auto data = send_request_sync(context->request);
        
        // 成功時の処理
        stats_.successful_requests++;
        if (cache_enabled_ && data.area_code != 0) {
            cache_data(data.area_code, data);
        }
        
        context->promise.set_value(data);
        
    } catch (const std::exception& e) {
        log_debug("Request failed: " + std::string(e.what()));
        
        // リトライ判定
        if (context->retry_count < max_retries_ && should_retry(e)) {
            context->retry_count++;
            stats_.retry_count++;
            
            // リトライ遅延
            auto delay = calculate_retry_delay(context->retry_count);
            std::this_thread::sleep_for(delay);
            
            // リクエストを再キューイング
            {
                std::lock_guard<std::mutex> lock(queue_mutex_);
                request_queue_.push(std::move(context));
            }
            queue_cv_.notify_one();
            return;
        }
        
        // 最終的な失敗
        stats_.failed_requests++;
        context->promise.set_exception(std::current_exception());
    }
    
    // アクティブリクエストから削除
    {
        std::lock_guard<std::mutex> lock(active_requests_mutex_);
        active_requests_.erase(context->request_id);
    }
}

WeatherData AsyncWeatherClient::send_request_sync(const packet::GenericRequest& request) {
    int sock = connection_pool_->acquire_connection(host_, port_);
    if (sock < 0) {
        throw std::runtime_error("Failed to acquire connection");
    }
    
    try {
        // リクエスト送信
        auto request_data = request.encode();
        ssize_t sent = wiplib::utils::platform_send(sock, request_data.data(), request_data.size(), 0);
        if (sent < 0) {
            throw std::runtime_error("Failed to send request");
        }
        
        stats_.bytes_sent += sent;
        
        // レスポンス受信
        std::vector<uint8_t> response_buffer(1024);
        ssize_t received = wiplib::utils::platform_recv(sock, response_buffer.data(), response_buffer.size(), 0);
        if (received < 0) {
            throw std::runtime_error("Failed to receive response");
        }
        
        stats_.bytes_received += received;
        response_buffer.resize(received);
        
        // レスポンス解析
        auto response = packet::GenericResponse::decode(response_buffer);
        if (!response) {
            throw std::runtime_error("Failed to decode response");
        }
        
        return parse_response(*response);
        
    } catch (...) {
        connection_pool_->release_connection(sock);
        throw;
    }
    
    connection_pool_->release_connection(sock);
}

std::optional<WeatherData> AsyncWeatherClient::get_cached_data(uint32_t area_code) const {
    std::lock_guard<std::mutex> lock(cache_mutex_);
    
    auto it = cache_.find(area_code);
    if (it != cache_.end() && !it->second.is_expired()) {
        return it->second.data;
    }
    
    return std::nullopt;
}

void AsyncWeatherClient::cache_data(uint32_t area_code, const WeatherData& data) {
    std::lock_guard<std::mutex> lock(cache_mutex_);
    
    cache_[area_code] = CacheEntry{
        data,
        std::chrono::steady_clock::now(),
        default_cache_ttl_
    };
}

void AsyncWeatherClient::log_debug(const std::string& message) const {
    if (debug_enabled_) {
        auto now = std::chrono::system_clock::now();
        auto time_t = std::chrono::system_clock::to_time_t(now);
        
        std::ostringstream ss;
        ss << "[" << std::put_time(std::localtime(&time_t), "%Y-%m-%d %H:%M:%S") << "] "
           << "AsyncWeatherClient: " << message << std::endl;
        
        std::cout << ss.str();
    }
}

std::string AsyncWeatherClient::generate_request_id() const {
    static std::random_device rd;
    static std::mt19937 gen(rd());
    static std::uniform_int_distribution<> dis(0, 15);
    
    std::ostringstream ss;
    for (int i = 0; i < 8; ++i) {
        ss << std::hex << dis(gen);
    }
    
    return ss.str();
}

std::chrono::milliseconds AsyncWeatherClient::calculate_retry_delay(uint8_t retry_count) const {
    // Exponential backoff with jitter
    auto delay = base_retry_delay_ * (1 << (retry_count - 1));
    delay = (std::min)(delay, max_retry_delay_);
    
    // Add jitter (±25%)
    static std::random_device rd;
    static std::mt19937 gen(rd());
    std::uniform_real_distribution<> dis(0.75, 1.25);
    
    return std::chrono::milliseconds(static_cast<long>(delay.count() * dis(gen)));
}

bool AsyncWeatherClient::should_retry(const std::exception& e) const {
    std::string error_msg = e.what();
    
    // ネットワークエラーはリトライ可能
    return error_msg.find("Failed to send") != std::string::npos ||
           error_msg.find("Failed to receive") != std::string::npos ||
           error_msg.find("Connection") != std::string::npos;
}

WeatherData AsyncWeatherClient::parse_response(const packet::GenericResponse& response) const {
    WeatherData data;
    
    const auto& header = response.get_header();
    data.area_code = header.area_code;
    data.timestamp = header.timestamp;
    
    if (auto fields = response.get_response_fields()) {
        data.weather_code = fields->weather_code;
        data.temperature = fields->temperature;
        data.precipitation_prob = fields->precipitation_prob;
    }
    
    // 拡張フィールドから追加データを取得
    auto all_fields = packet::ExtendedFieldManager::get_all_fields(response.get_packet());
    
    if (auto alerts_field = all_fields.find(packet::ExtendedFieldKey::Alert); 
        alerts_field != all_fields.end()) {
        if (auto alerts = std::get_if<std::vector<std::string>>(&alerts_field->second)) {
            data.alerts = *alerts;
        }
    }
    
    if (auto disasters_field = all_fields.find(packet::ExtendedFieldKey::Disaster); 
        disasters_field != all_fields.end()) {
        if (auto disasters = std::get_if<std::vector<std::string>>(&disasters_field->second)) {
            data.disasters = *disasters;
        }
    }
    
    // データ品質を計算
    const auto& quality_info = response.get_data_quality();
    data.data_quality = static_cast<float>(packet::response_utils::calculate_quality_score(quality_info));
    
    return data;
}

// AsyncWeatherClientFactory implementation
std::unique_ptr<AsyncWeatherClient> AsyncWeatherClientFactory::create_default() {
    auto client = std::make_unique<AsyncWeatherClient>("localhost", 4110, 50);
    client->set_cache_enabled(true, std::chrono::seconds{300});
    client->set_retry_policy(3);
    return client;
}

std::unique_ptr<AsyncWeatherClient> AsyncWeatherClientFactory::create_high_performance() {
    auto client = std::make_unique<AsyncWeatherClient>("localhost", 4110, 200);
    client->set_cache_enabled(true, std::chrono::seconds{600});
    client->set_retry_policy(5, std::chrono::milliseconds{500}, std::chrono::milliseconds{10000});
    return client;
}

std::unique_ptr<AsyncWeatherClient> AsyncWeatherClientFactory::create_low_resource() {
    auto client = std::make_unique<AsyncWeatherClient>("localhost", 4110, 10);
    client->set_cache_enabled(false);
    client->set_retry_policy(1);
    return client;
}

std::unique_ptr<AsyncWeatherClient> AsyncWeatherClientFactory::create_custom(
    const std::string& host, uint16_t port, size_t max_concurrent_requests,
    bool enable_cache, std::chrono::seconds cache_ttl) {
    
    auto client = std::make_unique<AsyncWeatherClient>(host, port, max_concurrent_requests);
    client->set_cache_enabled(enable_cache, cache_ttl);
    return client;
}

} // namespace wiplib::client
