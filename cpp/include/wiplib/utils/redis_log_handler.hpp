#pragma once

#include <string>
#include <memory>
#include <vector>
#include <unordered_map>
#include <queue>
#include <mutex>
#include <atomic>
#include <chrono>
#include <thread>
#include <condition_variable>
#include <functional>
#include <future>
#include <optional>

#include "wiplib/utils/log_config.hpp"

namespace wiplib::utils {

/**
 * @brief Redis接続設定
 */
struct RedisConfig {
    std::string host = "localhost";
    uint16_t port = 6379;
    std::string password;
    uint8_t database = 0;
    std::chrono::milliseconds connect_timeout{5000};
    std::chrono::milliseconds socket_timeout{3000};
    uint32_t max_retries = 3;
    std::chrono::milliseconds retry_delay{1000};
    bool enable_ssl = false;
    std::string ssl_cert_file;
    std::string ssl_key_file;
    std::string ssl_ca_file;
};

/**
 * @brief Redis接続プール設定
 */
struct RedisPoolConfig {
    size_t min_connections = 2;
    size_t max_connections = 10;
    std::chrono::seconds idle_timeout{300};
    std::chrono::seconds connection_lifetime{3600};
    bool enable_health_check = true;
    std::chrono::seconds health_check_interval{30};
};

/**
 * @brief ログ配信設定
 */
struct LogDeliveryConfig {
    std::string key_prefix = "wiplib:logs:";
    std::string stream_name = "wiplib_log_stream";
    bool use_stream = true;           // Redis Streams使用
    bool use_list = false;            // Redis Lists使用
    bool use_pub_sub = false;         // Redis Pub/Sub使用
    size_t batch_size = 100;          // バッチサイズ
    std::chrono::milliseconds batch_timeout{1000}; // バッチタイムアウト
    size_t max_queue_size = 10000;    // 最大キューサイズ
    bool enable_compression = false;   // 圧縮有効化
    std::string compression_algorithm = "gzip";
};

/**
 * @brief Redisログハンドラー統計
 */
struct RedisLogStats {
    std::atomic<uint64_t> messages_sent{0};
    std::atomic<uint64_t> messages_failed{0};
    std::atomic<uint64_t> messages_queued{0};
    std::atomic<uint64_t> messages_dropped{0};
    std::atomic<uint64_t> reconnection_attempts{0};
    std::atomic<uint64_t> successful_reconnections{0};
    std::atomic<uint64_t> total_bytes_sent{0};
    std::atomic<uint64_t> compression_savings{0};
    std::chrono::steady_clock::time_point start_time{std::chrono::steady_clock::now()};
    
    /**
     * @brief 成功率を計算
     */
    double get_success_rate() const {
        uint64_t total = messages_sent.load() + messages_failed.load();
        return total > 0 ? static_cast<double>(messages_sent.load()) / total : 0.0;
    }
    
    /**
     * @brief スループットを計算（メッセージ/秒）
     */
    double get_throughput() const {
        auto now = std::chrono::steady_clock::now();
        auto elapsed = std::chrono::duration_cast<std::chrono::seconds>(now - start_time);
        return elapsed.count() > 0 ? static_cast<double>(messages_sent.load()) / elapsed.count() : 0.0;
    }
};

/**
 * @brief Redis接続クラス
 */
class RedisConnection {
public:
    /**
     * @brief コンストラクタ
     * @param config Redis設定
     */
    explicit RedisConnection(const RedisConfig& config);
    
    ~RedisConnection();
    
    /**
     * @brief 接続
     * @return 成功時true
     */
    bool connect();
    
    /**
     * @brief 切断
     */
    void disconnect();
    
    /**
     * @brief 接続状態確認
     * @return 接続中の場合true
     */
    bool is_connected() const;
    
    /**
     * @brief ヘルスチェック
     * @return 正常な場合true
     */
    bool health_check();
    
    /**
     * @brief コマンド実行
     * @param command コマンド文字列
     * @param args 引数リスト
     * @return 実行結果
     */
    std::optional<std::string> execute_command(const std::string& command, const std::vector<std::string>& args = {});
    
    /**
     * @brief Streamにエントリ追加
     * @param stream_name ストリーム名
     * @param fields フィールドマップ
     * @return エントリID
     */
    std::optional<std::string> xadd(const std::string& stream_name, const std::unordered_map<std::string, std::string>& fields);
    
    /**
     * @brief リストにプッシュ
     * @param list_name リスト名
     * @param value 値
     * @return 成功時true
     */
    bool lpush(const std::string& list_name, const std::string& value);
    
    /**
     * @brief Pub/Sub発行
     * @param channel チャンネル名
     * @param message メッセージ
     * @return 購読者数
     */
    int publish(const std::string& channel, const std::string& message);
    
    /**
     * @brief 最後のエラーを取得
     * @return エラーメッセージ
     */
    std::string get_last_error() const;

private:
    RedisConfig config_;
    void* redis_context_; // redisContext*の前方宣言
    mutable std::mutex connection_mutex_;
    std::string last_error_;
    
    void set_error(const std::string& error);
};

/**
 * @brief Redis接続プール
 */
class RedisConnectionPool {
public:
    /**
     * @brief コンストラクタ
     * @param redis_config Redis設定
     * @param pool_config プール設定
     */
    explicit RedisConnectionPool(const RedisConfig& redis_config, const RedisPoolConfig& pool_config);
    
    ~RedisConnectionPool();
    
    /**
     * @brief 接続を取得
     * @param timeout タイムアウト時間
     * @return 接続（nullptrの場合は取得失敗）
     */
    std::shared_ptr<RedisConnection> acquire_connection(std::chrono::milliseconds timeout = std::chrono::milliseconds{5000});
    
    /**
     * @brief 接続を返却
     * @param connection 接続
     */
    void release_connection(std::shared_ptr<RedisConnection> connection);
    
    /**
     * @brief プール統計を取得
     * @return 統計情報
     */
    std::unordered_map<std::string, uint64_t> get_pool_statistics() const;
    
    /**
     * @brief ヘルスチェックを実行
     */
    void health_check();

private:
    RedisConfig redis_config_;
    RedisPoolConfig pool_config_;
    
    std::queue<std::shared_ptr<RedisConnection>> available_connections_;
    std::unordered_map<RedisConnection*, std::chrono::steady_clock::time_point> connection_timestamps_;
    
    mutable std::mutex pool_mutex_;
    std::condition_variable pool_cv_;
    
    std::unique_ptr<std::thread> health_check_thread_;
    std::atomic<bool> running_{true};
    
    mutable std::atomic<uint64_t> total_connections_created_{0};
    mutable std::atomic<uint64_t> active_connections_{0};
    mutable std::atomic<uint64_t> connection_requests_{0};
    mutable std::atomic<uint64_t> connection_timeouts_{0};
    
    std::shared_ptr<RedisConnection> create_connection();
    void health_check_loop();
    void cleanup_expired_connections();
};

/**
 * @brief RedisベースログハンドラークラシS
 */
class RedisLogHandler : public LogSink {
public:
    /**
     * @brief コンストラクタ
     * @param redis_config Redis設定
     * @param delivery_config 配信設定
     * @param pool_config プール設定（オプション）
     */
    explicit RedisLogHandler(
        const RedisConfig& redis_config,
        const LogDeliveryConfig& delivery_config = LogDeliveryConfig{},
        const std::optional<RedisPoolConfig>& pool_config = std::nullopt
    );
    
    ~RedisLogHandler() override;
    
    // LogSinkインターフェース実装
    void write(const LogEntry& entry) override;
    void flush() override;
    void close() override;
    
    /**
     * @brief 非同期ログ送信を有効化
     * @param enabled 有効フラグ
     * @param worker_threads ワーカースレッド数
     */
    void set_async_enabled(bool enabled, size_t worker_threads = 2);
    
    /**
     * @brief フィルターを設定
     * @param filter フィルター関数
     */
    void set_filter(std::function<bool(const LogEntry&)> filter);
    
    /**
     * @brief フォーマッターを設定
     * @param formatter フォーマッター関数
     */
    void set_formatter(std::function<std::string(const LogEntry&)> formatter);
    
    /**
     * @brief 配信設定を更新
     * @param config 新しい配信設定
     */
    void update_delivery_config(const LogDeliveryConfig& config);
    
    /**
     * @brief 統計情報を取得
     * @return 統計情報
     */
    RedisLogStats get_statistics() const;
    
    /**
     * @brief 統計をリセット
     */
    void reset_statistics();
    
    /**
     * @brief 接続状態を確認
     * @return 接続中の場合true
     */
    bool is_connected() const;
    
    /**
     * @brief 手動でバッファをフラッシュ
     * @return 送信されたメッセージ数
     */
    size_t flush_buffer();
    
    /**
     * @brief パフォーマンス監視を有効化
     * @param enabled 監視有効フラグ
     * @param callback パフォーマンス通知コールバック
     */
    void enable_performance_monitoring(bool enabled,
                                     std::function<void(const std::unordered_map<std::string, double>&)> callback = nullptr);

private:
    struct QueuedLogEntry {
        LogEntry entry;
        std::chrono::steady_clock::time_point queued_time;
    };
    
    RedisConfig redis_config_;
    LogDeliveryConfig delivery_config_;
    std::optional<RedisPoolConfig> pool_config_;
    
    // 接続管理
    std::unique_ptr<RedisConnectionPool> connection_pool_;
    std::unique_ptr<RedisConnection> single_connection_;
    
    // 非同期処理
    std::atomic<bool> async_enabled_{false};
    std::vector<std::unique_ptr<std::thread>> worker_threads_;
    std::queue<QueuedLogEntry> log_queue_;
    std::mutex queue_mutex_;
    std::condition_variable queue_cv_;
    std::atomic<bool> running_{true};
    
    // バッチ処理
    std::vector<LogEntry> batch_buffer_;
    std::mutex batch_mutex_;
    std::chrono::steady_clock::time_point last_batch_time_;
    
    // フィルタリング・フォーマット
    std::function<bool(const LogEntry&)> filter_;
    std::function<std::string(const LogEntry&)> formatter_;
    
    // 統計
    mutable RedisLogStats stats_;
    
    // パフォーマンス監視
    std::atomic<bool> performance_monitoring_enabled_{false};
    std::function<void(const std::unordered_map<std::string, double>&)> performance_callback_;
    
    // プライベートメソッド
    void worker_loop();
    void process_log_entry(const LogEntry& entry);
    void send_batch();
    bool send_to_stream(const std::vector<LogEntry>& entries);
    bool send_to_list(const std::vector<LogEntry>& entries);
    bool send_to_pubsub(const std::vector<LogEntry>& entries);
    
    std::string format_log_entry(const LogEntry& entry) const;
    std::string compress_data(const std::string& data) const;
    std::unordered_map<std::string, std::string> entry_to_fields(const LogEntry& entry) const;
    
    void update_statistics(bool success, size_t message_count, size_t bytes_sent);
    void record_performance_metric(const std::string& metric, double value);
    
    std::shared_ptr<RedisConnection> get_connection();
    void check_and_flush_batch();
    bool should_drop_message(const LogEntry& entry) const;
};

/**
 * @brief 分散ログ管理クラス
 */
class DistributedLogManager {
public:
    /**
     * @brief コンストラクタ
     * @param cluster_config クラスター設定
     */
    explicit DistributedLogManager(const std::vector<RedisConfig>& cluster_config);
    
    ~DistributedLogManager();
    
    /**
     * @brief ログハンドラーを追加
     * @param name ハンドラー名
     * @param handler ログハンドラー
     */
    void add_handler(const std::string& name, std::shared_ptr<RedisLogHandler> handler);
    
    /**
     * @brief ログハンドラーを削除
     * @param name ハンドラー名
     */
    void remove_handler(const std::string& name);
    
    /**
     * @brief ログを分散送信
     * @param entry ログエントリ
     */
    void distribute_log(const LogEntry& entry);
    
    /**
     * @brief 全体統計を取得
     * @return 統計情報マップ
     */
    std::unordered_map<std::string, RedisLogStats> get_cluster_statistics() const;
    
    /**
     * @brief フェイルオーバー機能を有効化
     * @param enabled フェイルオーバー有効フラグ
     */
    void enable_failover(bool enabled);
    
    /**
     * @brief ロードバランシング戦略を設定
     * @param strategy 戦略（"round_robin", "hash", "random"）
     */
    void set_load_balancing_strategy(const std::string& strategy);

private:
    std::unordered_map<std::string, std::shared_ptr<RedisLogHandler>> handlers_;
    std::atomic<size_t> round_robin_index_{0};
    std::atomic<bool> failover_enabled_{true};
    std::string load_balancing_strategy_{"round_robin"};
    mutable std::mutex handlers_mutex_;
    
    std::shared_ptr<RedisLogHandler> select_handler(const LogEntry& entry);
    size_t hash_entry(const LogEntry& entry) const;
};

/**
 * @brief RedisLogHandlerファクトリー
 */
class RedisLogHandlerFactory {
public:
    /**
     * @brief 基本Redis ログハンドラーを作成
     */
    static std::shared_ptr<RedisLogHandler> create_basic(
        const std::string& redis_host = "localhost",
        uint16_t redis_port = 6379
    );
    
    /**
     * @brief 高性能Redis ログハンドラーを作成
     */
    static std::shared_ptr<RedisLogHandler> create_high_performance(
        const RedisConfig& redis_config,
        size_t worker_threads = 4
    );
    
    /**
     * @brief セキュアRedis ログハンドラーを作成
     */
    static std::shared_ptr<RedisLogHandler> create_secure(
        const RedisConfig& redis_config
    );
    
    /**
     * @brief 設定ファイルからRedis ログハンドラーを作成
     */
    static std::shared_ptr<RedisLogHandler> create_from_config(
        const std::string& config_file
    );
};

} // namespace wiplib::utils