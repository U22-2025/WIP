#include "wiplib/utils/redis_log_handler.hpp"
#include <iostream>
#include <sstream>
#include <iomanip>
#include <random>
#include <algorithm>
#include <cstring>

// Redis C++クライアントライブラリのスタブ実装
// 実際の実装ではhiredisやredis-plus-plusを使用
namespace {
    struct RedisContextStub {
        bool connected = false;
        std::string last_error;
    };
    
    RedisContextStub* redisConnect(const char* host, int port) {
        auto* ctx = new RedisContextStub();
        // 実際の接続ロジックをここに実装
        ctx->connected = true;
        return ctx;
    }
    
    void redisFree(RedisContextStub* ctx) {
        delete ctx;
    }
    
    struct RedisReply {
        int type = 1; // REDIS_REPLY_STRING
        std::string str;
    };
    
    RedisReply* redisCommand(RedisContextStub* ctx, const char* format, ...) {
        if (!ctx || !ctx->connected) {
            return nullptr;
        }
        
        auto* reply = new RedisReply();
        reply->str = "OK";
        return reply;
    }
    
    void freeReplyObject(RedisReply* reply) {
        delete reply;
    }
}

namespace wiplib::utils {

// RedisConnection実装
RedisConnection::RedisConnection(const RedisConfig& config) 
    : config_(config), redis_context_(nullptr) {
}

RedisConnection::~RedisConnection() {
    disconnect();
}

bool RedisConnection::connect() {
    std::lock_guard<std::mutex> lock(connection_mutex_);
    
    if (redis_context_) {
        disconnect();
    }
    
    try {
        // 実際の実装ではhiredisを使用
        redis_context_ = redisConnect(config_.host.c_str(), config_.port);
        auto* ctx = static_cast<RedisContextStub*>(redis_context_);
        
        if (!ctx || !ctx->connected) {
            set_error("Failed to connect to Redis server");
            return false;
        }
        
        // パスワード認証
        if (!config_.password.empty()) {
            auto* reply = redisCommand(ctx, "AUTH %s", config_.password.c_str());
            if (!reply) {
                set_error("Authentication failed");
                return false;
            }
            freeReplyObject(reply);
        }
        
        // データベース選択
        if (config_.database != 0) {
            auto* reply = redisCommand(ctx, "SELECT %d", config_.database);
            if (!reply) {
                set_error("Database selection failed");
                return false;
            }
            freeReplyObject(reply);
        }
        
        return true;
        
    } catch (const std::exception& e) {
        set_error("Connection error: " + std::string(e.what()));
        return false;
    }
}

void RedisConnection::disconnect() {
    std::lock_guard<std::mutex> lock(connection_mutex_);
    
    if (redis_context_) {
        redisFree(static_cast<RedisContextStub*>(redis_context_));
        redis_context_ = nullptr;
    }
}

bool RedisConnection::is_connected() const {
    std::lock_guard<std::mutex> lock(connection_mutex_);
    return redis_context_ != nullptr;
}

bool RedisConnection::health_check() {
    if (!is_connected()) {
        return false;
    }
    
    auto result = execute_command("PING");
    return result && *result == "PONG";
}

std::optional<std::string> RedisConnection::execute_command(const std::string& command, const std::vector<std::string>& args) {
    std::lock_guard<std::mutex> lock(connection_mutex_);
    
    if (!redis_context_) {
        set_error("Not connected to Redis");
        return std::nullopt;
    }
    
    try {
        std::string cmd = command;
        for (const auto& arg : args) {
            cmd += " " + arg;
        }
        
        auto* ctx = static_cast<RedisContextStub*>(redis_context_);
        auto* reply = redisCommand(ctx, cmd.c_str());
        
        if (!reply) {
            set_error("Command execution failed");
            return std::nullopt;
        }
        
        std::string result = reply->str;
        freeReplyObject(reply);
        
        return result;
        
    } catch (const std::exception& e) {
        set_error("Command error: " + std::string(e.what()));
        return std::nullopt;
    }
}

std::optional<std::string> RedisConnection::xadd(const std::string& stream_name, const std::unordered_map<std::string, std::string>& fields) {
    std::vector<std::string> args;
    args.push_back(stream_name);
    args.push_back("*"); // auto-generate ID
    
    for (const auto& [key, value] : fields) {
        args.push_back(key);
        args.push_back(value);
    }
    
    return execute_command("XADD", args);
}

bool RedisConnection::lpush(const std::string& list_name, const std::string& value) {
    auto result = execute_command("LPUSH", {list_name, value});
    return result.has_value();
}

int RedisConnection::publish(const std::string& channel, const std::string& message) {
    auto result = execute_command("PUBLISH", {channel, message});
    if (result) {
        try {
            return std::stoi(*result);
        } catch (...) {
            return 0;
        }
    }
    return 0;
}

std::string RedisConnection::get_last_error() const {
    std::lock_guard<std::mutex> lock(connection_mutex_);
    return last_error_;
}

void RedisConnection::set_error(const std::string& error) {
    last_error_ = error;
}

// RedisConnectionPool実装
RedisConnectionPool::RedisConnectionPool(const RedisConfig& redis_config, const RedisPoolConfig& pool_config)
    : redis_config_(redis_config), pool_config_(pool_config) {
    
    // 最小接続数を作成
    for (size_t i = 0; i < pool_config_.min_connections; ++i) {
        auto connection = create_connection();
        if (connection && connection->connect()) {
            available_connections_.push(connection);
            total_connections_created_++;
        }
    }
    
    // ヘルスチェックスレッド開始
    if (pool_config_.enable_health_check) {
        health_check_thread_ = std::make_unique<std::thread>(&RedisConnectionPool::health_check_loop, this);
    }
}

RedisConnectionPool::~RedisConnectionPool() {
    running_ = false;
    
    if (health_check_thread_ && health_check_thread_->joinable()) {
        health_check_thread_->join();
    }
    
    std::lock_guard<std::mutex> lock(pool_mutex_);
    while (!available_connections_.empty()) {
        available_connections_.pop();
    }
}

std::shared_ptr<RedisConnection> RedisConnectionPool::acquire_connection(std::chrono::milliseconds timeout) {
    std::unique_lock<std::mutex> lock(pool_mutex_);
    
    connection_requests_++;
    
    auto deadline = std::chrono::steady_clock::now() + timeout;
    
    while (available_connections_.empty() && std::chrono::steady_clock::now() < deadline) {
        if (active_connections_ < pool_config_.max_connections) {
            // 新しい接続を作成
            auto connection = create_connection();
            if (connection && connection->connect()) {
                total_connections_created_++;
                active_connections_++;
                return connection;
            }
        }
        
        // 利用可能な接続を待機
        pool_cv_.wait_until(lock, deadline);
    }
    
    if (available_connections_.empty()) {
        connection_timeouts_++;
        return nullptr;
    }
    
    auto connection = available_connections_.front();
    available_connections_.pop();
    active_connections_++;
    
    return connection;
}

void RedisConnectionPool::release_connection(std::shared_ptr<RedisConnection> connection) {
    if (!connection) return;
    
    std::lock_guard<std::mutex> lock(pool_mutex_);
    
    if (connection->is_connected()) {
        available_connections_.push(connection);
        connection_timestamps_[connection.get()] = std::chrono::steady_clock::now();
    }
    
    active_connections_--;
    pool_cv_.notify_one();
}

std::unordered_map<std::string, uint64_t> RedisConnectionPool::get_pool_statistics() const {
    std::lock_guard<std::mutex> lock(pool_mutex_);
    
    return {
        {"total_connections_created", total_connections_created_.load()},
        {"active_connections", active_connections_.load()},
        {"available_connections", available_connections_.size()},
        {"connection_requests", connection_requests_.load()},
        {"connection_timeouts", connection_timeouts_.load()}
    };
}

void RedisConnectionPool::health_check() {
    std::lock_guard<std::mutex> lock(pool_mutex_);
    cleanup_expired_connections();
}

std::shared_ptr<RedisConnection> RedisConnectionPool::create_connection() {
    return std::make_shared<RedisConnection>(redis_config_);
}

void RedisConnectionPool::health_check_loop() {
    while (running_) {
        std::this_thread::sleep_for(pool_config_.health_check_interval);
        if (running_) {
            health_check();
        }
    }
}

void RedisConnectionPool::cleanup_expired_connections() {
    auto now = std::chrono::steady_clock::now();
    std::queue<std::shared_ptr<RedisConnection>> valid_connections;
    
    while (!available_connections_.empty()) {
        auto connection = available_connections_.front();
        available_connections_.pop();
        
        auto it = connection_timestamps_.find(connection.get());
        if (it != connection_timestamps_.end()) {
            auto age = now - it->second;
            if (age < pool_config_.connection_lifetime && connection->health_check()) {
                valid_connections.push(connection);
            } else {
                connection_timestamps_.erase(it);
            }
        }
    }
    
    available_connections_ = std::move(valid_connections);
}

// RedisLogHandler実装
RedisLogHandler::RedisLogHandler(
    const RedisConfig& redis_config,
    const LogDeliveryConfig& delivery_config,
    const std::optional<RedisPoolConfig>& pool_config)
    : redis_config_(redis_config), delivery_config_(delivery_config), pool_config_(pool_config) {
    
    if (pool_config_) {
        connection_pool_ = std::make_unique<RedisConnectionPool>(redis_config_, *pool_config_);
    } else {
        single_connection_ = std::make_unique<RedisConnection>(redis_config_);
        single_connection_->connect();
    }
    
    last_batch_time_ = std::chrono::steady_clock::now();
    
    // デフォルトフォーマッター設定
    formatter_ = [](const LogEntry& entry) -> std::string {
        std::ostringstream oss;
        oss << "[" << entry.logger_name << "] " 
            << entry.message;
        return oss.str();
    };
}

RedisLogHandler::~RedisLogHandler() {
    close();
}

void RedisLogHandler::write(const LogEntry& entry) {
    if (filter_ && !filter_(entry)) {
        return;
    }
    
    if (should_drop_message(entry)) {
        stats_.messages_dropped++;
        return;
    }
    
    if (async_enabled_) {
        std::lock_guard<std::mutex> lock(queue_mutex_);
        if (log_queue_.size() < delivery_config_.max_queue_size) {
            log_queue_.push({entry, std::chrono::steady_clock::now()});
            stats_.messages_queued++;
            queue_cv_.notify_one();
        } else {
            stats_.messages_dropped++;
        }
    } else {
        process_log_entry(entry);
    }
}

void RedisLogHandler::flush() {
    if (async_enabled_) {
        // 非同期モードでは強制フラッシュ
        flush_buffer();
    } else {
        // 同期モードでは保留中のバッチを送信
        std::lock_guard<std::mutex> lock(batch_mutex_);
        if (!batch_buffer_.empty()) {
            send_batch();
        }
    }
}

void RedisLogHandler::close() {
    running_ = false;
    
    // ワーカースレッド終了待ち
    queue_cv_.notify_all();
    for (auto& thread : worker_threads_) {
        if (thread && thread->joinable()) {
            thread->join();
        }
    }
    worker_threads_.clear();
    
    // 残りのメッセージを処理
    flush();
    
    // 接続クローズ
    if (single_connection_) {
        single_connection_->disconnect();
    }
}

void RedisLogHandler::set_async_enabled(bool enabled, size_t worker_threads) {
    async_enabled_ = enabled;
    
    if (enabled && worker_threads_.empty()) {
        for (size_t i = 0; i < worker_threads; ++i) {
            worker_threads_.push_back(
                std::make_unique<std::thread>(&RedisLogHandler::worker_loop, this)
            );
        }
    }
}

void RedisLogHandler::set_filter(std::function<bool(const LogEntry&)> filter) {
    filter_ = std::move(filter);
}

void RedisLogHandler::set_formatter(std::function<std::string(const LogEntry&)> formatter) {
    formatter_ = std::move(formatter);
}

void RedisLogHandler::update_delivery_config(const LogDeliveryConfig& config) {
    delivery_config_ = config;
}

RedisLogStats RedisLogHandler::get_statistics() const {
    RedisLogStats result;
    result.messages_sent = stats_.messages_sent.load();
    result.messages_failed = stats_.messages_failed.load();
    result.messages_queued = stats_.messages_queued.load();
    result.messages_dropped = stats_.messages_dropped.load();
    result.reconnection_attempts = stats_.reconnection_attempts.load();
    result.successful_reconnections = stats_.successful_reconnections.load();
    result.total_bytes_sent = stats_.total_bytes_sent.load();
    result.compression_savings = stats_.compression_savings.load();
    result.start_time = stats_.start_time;
    return result;
}

void RedisLogHandler::reset_statistics() {
    stats_.messages_sent = 0;
    stats_.messages_failed = 0;
    stats_.messages_queued = 0;
    stats_.messages_dropped = 0;
    stats_.reconnection_attempts = 0;
    stats_.successful_reconnections = 0;
    stats_.total_bytes_sent = 0;
    stats_.compression_savings = 0;
    stats_.start_time = std::chrono::steady_clock::now();
}

bool RedisLogHandler::is_connected() const {
    if (single_connection_) {
        return single_connection_->is_connected();
    }
    
    if (connection_pool_) {
        auto connection = connection_pool_->acquire_connection(std::chrono::milliseconds{100});
        if (connection) {
            bool connected = connection->is_connected();
            connection_pool_->release_connection(connection);
            return connected;
        }
    }
    
    return false;
}

size_t RedisLogHandler::flush_buffer() {
    std::lock_guard<std::mutex> lock(batch_mutex_);
    size_t flushed = batch_buffer_.size();
    if (!batch_buffer_.empty()) {
        send_batch();
    }
    return flushed;
}

void RedisLogHandler::enable_performance_monitoring(bool enabled, std::function<void(const std::unordered_map<std::string, double>&)> callback) {
    performance_monitoring_enabled_ = enabled;
    performance_callback_ = std::move(callback);
}

void RedisLogHandler::worker_loop() {
    while (running_) {
        std::unique_lock<std::mutex> lock(queue_mutex_);
        queue_cv_.wait(lock, [this] { return !log_queue_.empty() || !running_; });
        
        if (!running_) break;
        
        std::vector<QueuedLogEntry> batch;
        size_t batch_size = std::min(delivery_config_.batch_size, log_queue_.size());
        
        for (size_t i = 0; i < batch_size && !log_queue_.empty(); ++i) {
            batch.push_back(log_queue_.front());
            log_queue_.pop();
        }
        
        lock.unlock();
        
        // バッチ処理
        for (const auto& queued_entry : batch) {
            process_log_entry(queued_entry.entry);
        }
    }
}

void RedisLogHandler::process_log_entry(const LogEntry& entry) {
    std::lock_guard<std::mutex> lock(batch_mutex_);
    batch_buffer_.push_back(entry);
    
    // バッチサイズまたはタイムアウトに達したら送信
    check_and_flush_batch();
}

void RedisLogHandler::send_batch() {
    if (batch_buffer_.empty()) return;
    
    auto start_time = std::chrono::steady_clock::now();
    bool success = false;
    
    if (delivery_config_.use_stream) {
        success = send_to_stream(batch_buffer_);
    } else if (delivery_config_.use_list) {
        success = send_to_list(batch_buffer_);
    } else if (delivery_config_.use_pub_sub) {
        success = send_to_pubsub(batch_buffer_);
    }
    
    auto end_time = std::chrono::steady_clock::now();
    auto duration = std::chrono::duration_cast<std::chrono::milliseconds>(end_time - start_time);
    
    size_t message_count = batch_buffer_.size();
    size_t bytes_sent = 0;
    
    for (const auto& entry : batch_buffer_) {
        bytes_sent += format_log_entry(entry).size();
    }
    
    update_statistics(success, message_count, bytes_sent);
    record_performance_metric("batch_send_time_ms", duration.count());
    
    batch_buffer_.clear();
    last_batch_time_ = std::chrono::steady_clock::now();
}

bool RedisLogHandler::send_to_stream(const std::vector<LogEntry>& entries) {
    auto connection = get_connection();
    if (!connection) return false;
    
    for (const auto& entry : entries) {
        auto fields = entry_to_fields(entry);
        auto result = connection->xadd(delivery_config_.stream_name, fields);
        if (!result) {
            return false;
        }
    }
    
    return true;
}

bool RedisLogHandler::send_to_list(const std::vector<LogEntry>& entries) {
    auto connection = get_connection();
    if (!connection) return false;
    
    for (const auto& entry : entries) {
        std::string formatted = format_log_entry(entry);
        if (delivery_config_.enable_compression) {
            formatted = compress_data(formatted);
        }
        
        std::string key = delivery_config_.key_prefix + "list";
        if (!connection->lpush(key, formatted)) {
            return false;
        }
    }
    
    return true;
}

bool RedisLogHandler::send_to_pubsub(const std::vector<LogEntry>& entries) {
    auto connection = get_connection();
    if (!connection) return false;
    
    for (const auto& entry : entries) {
        std::string formatted = format_log_entry(entry);
        std::string channel = delivery_config_.key_prefix + "channel";
        
        int subscribers = connection->publish(channel, formatted);
        if (subscribers < 0) {
            return false;
        }
    }
    
    return true;
}

std::string RedisLogHandler::format_log_entry(const LogEntry& entry) const {
    if (formatter_) {
        return formatter_(entry);
    }
    
    std::ostringstream oss;
    oss << "[" << entry.logger_name << "] " << entry.message;
    return oss.str();
}

std::string RedisLogHandler::compress_data(const std::string& data) const {
    // 実際の実装では圧縮ライブラリを使用
    return data; // スタブ実装
}

std::unordered_map<std::string, std::string> RedisLogHandler::entry_to_fields(const LogEntry& entry) const {
    std::unordered_map<std::string, std::string> fields;
    
    fields["level"] = std::to_string(static_cast<int>(entry.level));
    fields["logger"] = entry.logger_name;
    fields["message"] = entry.message;
    fields["timestamp"] = std::to_string(
        std::chrono::duration_cast<std::chrono::milliseconds>(
            entry.timestamp.time_since_epoch()
        ).count()
    );
    fields["thread_id"] = entry.thread_id;
    fields["file"] = entry.file;
    fields["line"] = std::to_string(entry.line);
    fields["function"] = entry.function;
    
    // メタデータを追加
    for (const auto& [key, value] : entry.metadata) {
        fields["meta_" + key] = value;
    }
    
    return fields;
}

void RedisLogHandler::update_statistics(bool success, size_t message_count, size_t bytes_sent) {
    if (success) {
        stats_.messages_sent += message_count;
        stats_.total_bytes_sent += bytes_sent;
    } else {
        stats_.messages_failed += message_count;
    }
}

void RedisLogHandler::record_performance_metric(const std::string& metric, double value) {
    if (performance_monitoring_enabled_ && performance_callback_) {
        std::unordered_map<std::string, double> metrics{{metric, value}};
        performance_callback_(metrics);
    }
}

std::shared_ptr<RedisConnection> RedisLogHandler::get_connection() {
    if (connection_pool_) {
        return connection_pool_->acquire_connection();
    } else if (single_connection_) {
        return std::shared_ptr<RedisConnection>(single_connection_.get(), [](RedisConnection*){});
    }
    return nullptr;
}

void RedisLogHandler::check_and_flush_batch() {
    bool should_flush = false;
    
    if (batch_buffer_.size() >= delivery_config_.batch_size) {
        should_flush = true;
    } else {
        auto now = std::chrono::steady_clock::now();
        auto elapsed = std::chrono::duration_cast<std::chrono::milliseconds>(now - last_batch_time_);
        if (elapsed >= delivery_config_.batch_timeout) {
            should_flush = true;
        }
    }
    
    if (should_flush) {
        send_batch();
    }
}

bool RedisLogHandler::should_drop_message(const LogEntry& entry) const {
    // キューサイズ制限チェック
    if (async_enabled_) {
        std::lock_guard<std::mutex> lock(queue_mutex_);
        return log_queue_.size() >= delivery_config_.max_queue_size;
    }
    
    return false;
}

// DistributedLogManager実装
DistributedLogManager::DistributedLogManager(const std::vector<RedisConfig>& cluster_config) {
    for (size_t i = 0; i < cluster_config.size(); ++i) {
        auto handler = std::make_shared<RedisLogHandler>(cluster_config[i]);
        add_handler("handler_" + std::to_string(i), handler);
    }
}

DistributedLogManager::~DistributedLogManager() {
    std::lock_guard<std::mutex> lock(handlers_mutex_);
    handlers_.clear();
}

void DistributedLogManager::add_handler(const std::string& name, std::shared_ptr<RedisLogHandler> handler) {
    std::lock_guard<std::mutex> lock(handlers_mutex_);
    handlers_[name] = std::move(handler);
}

void DistributedLogManager::remove_handler(const std::string& name) {
    std::lock_guard<std::mutex> lock(handlers_mutex_);
    handlers_.erase(name);
}

void DistributedLogManager::distribute_log(const LogEntry& entry) {
    auto handler = select_handler(entry);
    if (handler) {
        handler->write(entry);
    }
}

std::unordered_map<std::string, RedisLogStats> DistributedLogManager::get_cluster_statistics() const {
    std::lock_guard<std::mutex> lock(handlers_mutex_);
    
    std::unordered_map<std::string, RedisLogStats> stats;
    for (const auto& [name, handler] : handlers_) {
        stats[name] = handler->get_statistics();
    }
    
    return stats;
}

void DistributedLogManager::enable_failover(bool enabled) {
    failover_enabled_ = enabled;
}

void DistributedLogManager::set_load_balancing_strategy(const std::string& strategy) {
    load_balancing_strategy_ = strategy;
}

std::shared_ptr<RedisLogHandler> DistributedLogManager::select_handler(const LogEntry& entry) {
    std::lock_guard<std::mutex> lock(handlers_mutex_);
    
    if (handlers_.empty()) {
        return nullptr;
    }
    
    if (load_balancing_strategy_ == "round_robin") {
        auto it = handlers_.begin();
        std::advance(it, round_robin_index_ % handlers_.size());
        round_robin_index_++;
        return it->second;
    } else if (load_balancing_strategy_ == "hash") {
        size_t hash = hash_entry(entry);
        auto it = handlers_.begin();
        std::advance(it, hash % handlers_.size());
        return it->second;
    } else if (load_balancing_strategy_ == "random") {
        static std::random_device rd;
        static std::mt19937 gen(rd());
        std::uniform_int_distribution<> dis(0, handlers_.size() - 1);
        
        auto it = handlers_.begin();
        std::advance(it, dis(gen));
        return it->second;
    }
    
    return handlers_.begin()->second;
}

size_t DistributedLogManager::hash_entry(const LogEntry& entry) const {
    std::hash<std::string> hasher;
    return hasher(entry.logger_name + entry.message);
}

// RedisLogHandlerFactory実装
std::shared_ptr<RedisLogHandler> RedisLogHandlerFactory::create_basic(const std::string& redis_host, uint16_t redis_port) {
    RedisConfig config;
    config.host = redis_host;
    config.port = redis_port;
    
    return std::make_shared<RedisLogHandler>(config);
}

std::shared_ptr<RedisLogHandler> RedisLogHandlerFactory::create_high_performance(const RedisConfig& redis_config, size_t worker_threads) {
    LogDeliveryConfig delivery_config;
    delivery_config.batch_size = 1000;
    delivery_config.batch_timeout = std::chrono::milliseconds{100};
    delivery_config.enable_compression = true;
    
    RedisPoolConfig pool_config;
    pool_config.min_connections = 5;
    pool_config.max_connections = 20;
    
    auto handler = std::make_shared<RedisLogHandler>(redis_config, delivery_config, pool_config);
    handler->set_async_enabled(true, worker_threads);
    
    return handler;
}

std::shared_ptr<RedisLogHandler> RedisLogHandlerFactory::create_secure(const RedisConfig& redis_config) {
    RedisConfig secure_config = redis_config;
    secure_config.enable_ssl = true;
    
    return std::make_shared<RedisLogHandler>(secure_config);
}

std::shared_ptr<RedisLogHandler> RedisLogHandlerFactory::create_from_config(const std::string& config_file) {
    // 設定ファイル読み込み実装（簡略化）
    RedisConfig config;
    config.host = "localhost";
    config.port = 6379;
    
    return std::make_shared<RedisLogHandler>(config);
}

} // namespace wiplib::utils