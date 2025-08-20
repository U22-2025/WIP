#pragma once

#include <memory>
#include <string>
#include <vector>
#include <unordered_map>
#include <mutex>
#include <condition_variable>
#include <atomic>
#include <thread>
#include <chrono>
#include <functional>
#include <queue>

#ifdef _WIN32
    #include <winsock2.h>
    #include <ws2tcpip.h>
#else
    #include <sys/socket.h>
    #include <netinet/in.h>
#endif

namespace wiplib::client::utils {

/**
 * @brief 接続状態
 */
enum class ConnectionState {
    Disconnected = 0,
    Connecting,
    Connected,
    Error,
    Timeout,
    Closed
};

/**
 * @brief 接続情報
 */
struct ConnectionInfo {
    int socket_fd = -1;
    std::string host;
    uint16_t port = 0;
    ConnectionState state = ConnectionState::Disconnected;
    std::chrono::steady_clock::time_point created_time{};
    std::chrono::steady_clock::time_point last_used_time{};
    std::chrono::steady_clock::time_point last_activity_time{};
    uint64_t use_count = 0;
    uint64_t error_count = 0;
    bool is_in_use = false;
    std::string connection_id;
    double quality_score = 1.0;  // 0.0-1.0
};

/**
 * @brief プール統計情報
 */
struct PoolStats {
    std::atomic<size_t> total_connections{0};
    std::atomic<size_t> active_connections{0};
    std::atomic<size_t> idle_connections{0};
    std::atomic<size_t> failed_connections{0};
    std::atomic<uint64_t> total_acquisitions{0};
    std::atomic<uint64_t> successful_acquisitions{0};
    std::atomic<uint64_t> failed_acquisitions{0};
    std::atomic<uint64_t> connections_created{0};
    std::atomic<uint64_t> connections_destroyed{0};
    std::chrono::steady_clock::time_point start_time{std::chrono::steady_clock::now()};
    PoolStats() = default;
    PoolStats(const PoolStats& other) {
        total_connections.store(other.total_connections.load());
        active_connections.store(other.active_connections.load());
        idle_connections.store(other.idle_connections.load());
        failed_connections.store(other.failed_connections.load());
        total_acquisitions.store(other.total_acquisitions.load());
        successful_acquisitions.store(other.successful_acquisitions.load());
        failed_acquisitions.store(other.failed_acquisitions.load());
        connections_created.store(other.connections_created.load());
        connections_destroyed.store(other.connections_destroyed.load());
        start_time = other.start_time;
    }
    PoolStats& operator=(const PoolStats& other) {
        if (this != &other) {
            total_connections.store(other.total_connections.load());
            active_connections.store(other.active_connections.load());
            idle_connections.store(other.idle_connections.load());
            failed_connections.store(other.failed_connections.load());
            total_acquisitions.store(other.total_acquisitions.load());
            successful_acquisitions.store(other.successful_acquisitions.load());
            failed_acquisitions.store(other.failed_acquisitions.load());
            connections_created.store(other.connections_created.load());
            connections_destroyed.store(other.connections_destroyed.load());
            start_time = other.start_time;
        }
        return *this;
    }
};

/**
 * @brief プール設定
 */
struct PoolConfig {
    size_t max_connections = 100;                    // 最大接続数
    size_t min_connections = 5;                      // 最小接続数
    std::chrono::seconds max_idle_time{300};         // 最大アイドル時間
    std::chrono::seconds connection_timeout{30};     // 接続タイムアウト
    std::chrono::seconds acquisition_timeout{10};    // 取得タイムアウト
    std::chrono::seconds health_check_interval{60};  // ヘルスチェック間隔
    uint32_t max_retries = 3;                        // 最大リトライ回数
    bool enable_keep_alive = true;                   // Keep-Alive有効
    bool enable_health_check = true;                 // ヘルスチェック有効
    size_t max_error_count = 5;                      // 最大エラー回数（接続除外閾値）
    double min_quality_threshold = 0.3;             // 最小品質閾値
};

/**
 * @brief 接続ファクトリー関数型
 */
using ConnectionFactory = std::function<int(const std::string&, uint16_t)>;

/**
 * @brief 接続ヘルスチェック関数型
 */
using HealthChecker = std::function<bool(int)>;

/**
 * @brief UDPソケット接続プール
 */
class UDPConnectionPool {
public:
    /**
     * @brief コンストラクタ
     * @param config プール設定
     * @param factory 接続ファクトリー（nullptrでデフォルト）
     * @param health_checker ヘルスチェッカー（nullptrでデフォルト）
     */
    explicit UDPConnectionPool(
        const PoolConfig& config = PoolConfig{},
        ConnectionFactory factory = nullptr,
        HealthChecker health_checker = nullptr
    );
    
    ~UDPConnectionPool();
    
    /**
     * @brief 接続を取得
     * @param host ホスト名
     * @param port ポート番号
     * @param timeout 取得タイムアウト
     * @return 接続情報（失敗時nullptr）
     */
    std::shared_ptr<ConnectionInfo> acquire_connection(
        const std::string& host,
        uint16_t port,
        std::chrono::milliseconds timeout = std::chrono::milliseconds{10000}
    );
    
    /**
     * @brief 接続を返却
     * @param connection 返却する接続
     */
    void release_connection(std::shared_ptr<ConnectionInfo> connection);
    
    /**
     * @brief 指定ホスト・ポートの接続をすべて取得
     * @param host ホスト名
     * @param port ポート番号
     * @param max_connections 最大取得数
     * @return 接続リスト
     */
    std::vector<std::shared_ptr<ConnectionInfo>> acquire_multiple_connections(
        const std::string& host,
        uint16_t port,
        size_t max_connections = 10
    );
    
    /**
     * @brief 接続の事前作成（ウォームアップ）
     * @param host ホスト名
     * @param port ポート番号
     * @param count 作成数
     * @return 作成された接続数
     */
    size_t warmup_connections(const std::string& host, uint16_t port, size_t count);
    
    /**
     * @brief 不正な接続を除外
     * @param connection 除外する接続
     * @param reason 除外理由
     */
    void invalidate_connection(std::shared_ptr<ConnectionInfo> connection, const std::string& reason = "");
    
    /**
     * @brief 指定ホスト・ポートの接続をすべて除外
     * @param host ホスト名
     * @param port ポート番号
     * @return 除外された接続数
     */
    size_t invalidate_host_connections(const std::string& host, uint16_t port);
    
    /**
     * @brief アイドル接続をクリーンアップ
     * @return クリーンアップされた接続数
     */
    size_t cleanup_idle_connections();
    
    /**
     * @brief エラーの多い接続をクリーンアップ
     * @return クリーンアップされた接続数
     */
    size_t cleanup_error_connections();
    
    /**
     * @brief 接続品質を更新
     * @param connection_id 接続ID
     * @param quality_score 品質スコア（0.0-1.0）
     */
    void update_connection_quality(const std::string& connection_id, double quality_score);
    
    /**
     * @brief 接続エラーを記録
     * @param connection_id 接続ID
     * @param error_message エラーメッセージ
     */
    void record_connection_error(const std::string& connection_id, const std::string& error_message = "");
    
    /**
     * @brief 手動ヘルスチェックを実行
     * @return チェックされた接続数
     */
    size_t perform_health_check();
    
    /**
     * @brief プール統計を取得
     * @return 統計情報
     */
    PoolStats get_statistics() const;
    
    /**
     * @brief アクティブな接続数を取得
     * @return アクティブ接続数
     */
    size_t get_active_connection_count() const;
    
    /**
     * @brief 利用可能な接続数を取得
     * @return 利用可能接続数
     */
    size_t get_available_connection_count() const;
    
    /**
     * @brief 接続先ホスト一覧を取得
     * @return ホスト:ポートのペアリスト
     */
    std::vector<std::pair<std::string, uint16_t>> get_active_hosts() const;
    
    /**
     * @brief プール設定を更新
     * @param new_config 新しい設定
     */
    void update_config(const PoolConfig& new_config);
    
    /**
     * @brief プールをリセット（全接続クローズ）
     */
    void reset_pool();
    
    /**
     * @brief デバッグ情報を取得
     * @return デバッグ情報マップ
     */
    std::unordered_map<std::string, std::string> get_debug_info() const;
    
    /**
     * @brief デバッグモードを設定
     * @param enabled デバッグ有効フラグ
     */
    void set_debug_enabled(bool enabled);
    
    /**
     * @brief プールを閉じる
     */
    void close();

private:
    struct HostKey {
        std::string host;
        uint16_t port;
        
        bool operator==(const HostKey& other) const {
            return host == other.host && port == other.port;
        }
    };
    
    struct HostKeyHash {
        size_t operator()(const HostKey& key) const {
            return std::hash<std::string>{}(key.host) ^ 
                   (std::hash<uint16_t>{}(key.port) << 1);
        }
    };
    
    PoolConfig config_;
    ConnectionFactory connection_factory_;
    HealthChecker health_checker_;
    
    // 接続管理
    std::unordered_map<HostKey, std::vector<std::shared_ptr<ConnectionInfo>>, HostKeyHash> connections_;
    std::unordered_map<std::string, std::shared_ptr<ConnectionInfo>> connection_by_id_;
    std::mutex connections_mutex_;
    std::condition_variable connection_available_cv_;
    
    // バックグラウンドタスク
    std::atomic<bool> running_{true};
    std::unique_ptr<std::thread> maintenance_thread_;
    
    // 統計
    PoolStats stats_;
    std::atomic<bool> debug_enabled_{false};
    
    // プライベートメソッド
    void maintenance_loop();
    std::shared_ptr<ConnectionInfo> create_connection(const std::string& host, uint16_t port);
    bool validate_connection(std::shared_ptr<ConnectionInfo> connection);
    void close_connection(std::shared_ptr<ConnectionInfo> connection);
    std::string generate_connection_id();
    int default_connection_factory(const std::string& host, uint16_t port);
    bool default_health_checker(int socket_fd);
    void log_debug(const std::string& message);
    void update_connection_activity(std::shared_ptr<ConnectionInfo> connection);
    bool should_remove_connection(std::shared_ptr<ConnectionInfo> connection);
    size_t get_host_connection_count(const HostKey& key) const;
    double calculate_connection_quality(std::shared_ptr<ConnectionInfo> connection) const;
};

/**
 * @brief TCP接続プール
 */
class TCPConnectionPool {
public:
    explicit TCPConnectionPool(
        const PoolConfig& config = PoolConfig{},
        ConnectionFactory factory = nullptr,
        HealthChecker health_checker = nullptr
    );
    
    ~TCPConnectionPool();
    
    // UDPConnectionPoolと同様のインターフェース
    std::shared_ptr<ConnectionInfo> acquire_connection(
        const std::string& host,
        uint16_t port,
        std::chrono::milliseconds timeout = std::chrono::milliseconds{10000}
    );
    
    void release_connection(std::shared_ptr<ConnectionInfo> connection);
    PoolStats get_statistics() const;
    void close();

private:
    std::unique_ptr<UDPConnectionPool> impl_;  // 実装は共通化
};

/**
 * @brief 接続プールファクトリー
 */
class ConnectionPoolFactory {
public:
    /**
     * @brief UDP用の標準プールを作成
     */
    static std::unique_ptr<UDPConnectionPool> create_udp_pool();
    
    /**
     * @brief UDP用の高性能プールを作成
     */
    static std::unique_ptr<UDPConnectionPool> create_high_performance_udp_pool();
    
    /**
     * @brief UDP用の低リソースプールを作成
     */
    static std::unique_ptr<UDPConnectionPool> create_low_resource_udp_pool();
    
    /**
     * @brief TCP用の標準プールを作成
     */
    static std::unique_ptr<TCPConnectionPool> create_tcp_pool();
    
    /**
     * @brief カスタムプールを作成
     */
    static std::unique_ptr<UDPConnectionPool> create_custom_udp_pool(
        const PoolConfig& config,
        ConnectionFactory factory = nullptr,
        HealthChecker health_checker = nullptr
    );
};

} // namespace wiplib::client::utils
