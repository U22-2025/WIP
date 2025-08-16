#pragma once

#include <future>
#include <chrono>
#include <memory>
#include <string>
#include <vector>
#include <atomic>
#include <mutex>
#include <queue>
#include <thread>
#include <condition_variable>
#include <functional>

#include <sys/socket.h>
#include <netinet/in.h>
#include <optional>

namespace wiplib::client::utils {

/**
 * @brief 送信エラータイプ
 */
enum class SendErrorType {
    Success = 0,
    NetworkError,
    Timeout,
    BufferFull,
    ConnectionClosed,
    InvalidAddress,
    PermissionDenied,
    MessageTooLarge,
    SystemError
};

/**
 * @brief 送信結果
 */
struct SendResult {
    SendErrorType error_type = SendErrorType::Success;
    ssize_t bytes_sent = 0;
    std::string error_message{};
    std::chrono::milliseconds send_time{};
    uint32_t retry_count = 0;
};

/**
 * @brief 送信統計情報
 */
struct SendStats {
    std::atomic<uint64_t> total_sends{0};
    std::atomic<uint64_t> successful_sends{0};
    std::atomic<uint64_t> failed_sends{0};
    std::atomic<uint64_t> retried_sends{0};
    std::atomic<uint64_t> bytes_sent{0};
    std::atomic<uint64_t> total_send_time_ms{0};
    std::chrono::steady_clock::time_point start_time{std::chrono::steady_clock::now()};
    SendStats() = default;
    SendStats(const SendStats& other) {
        total_sends.store(other.total_sends.load());
        successful_sends.store(other.successful_sends.load());
        failed_sends.store(other.failed_sends.load());
        retried_sends.store(other.retried_sends.load());
        bytes_sent.store(other.bytes_sent.load());
        total_send_time_ms.store(other.total_send_time_ms.load());
        start_time = other.start_time;
    }
    SendStats& operator=(const SendStats& other) {
        if (this != &other) {
            total_sends.store(other.total_sends.load());
            successful_sends.store(other.successful_sends.load());
            failed_sends.store(other.failed_sends.load());
            retried_sends.store(other.retried_sends.load());
            bytes_sent.store(other.bytes_sent.load());
            total_send_time_ms.store(other.total_send_time_ms.load());
            start_time = other.start_time;
        }
        return *this;
    }
};

/**
 * @brief 送信設定
 */
struct SendConfig {
    uint32_t max_retries = 3;
    std::chrono::milliseconds retry_delay{1000};
    std::chrono::milliseconds max_retry_delay{10000};
    std::chrono::milliseconds send_timeout{30000};
    size_t max_message_size = 65536;
    bool enable_keepalive = true;
    bool enable_nodelay = true;
    int send_buffer_size = 65536;
    double backoff_multiplier = 2.0;
};

/**
 * @brief 非同期送信アイテム
 */
struct AsyncSendItem {
    std::vector<uint8_t> data;
    struct sockaddr_in destination;
    std::promise<SendResult> promise;
    std::chrono::steady_clock::time_point enqueue_time;
    std::chrono::milliseconds timeout;
    uint32_t retry_count = 0;
    std::string operation_id;
};

/**
 * @brief 安全ソケット送信ユーティリティ
 */
class SafeSockSendTo {
public:
    /**
     * @brief コンストラクタ
     * @param socket_fd ソケットファイルディスクリプタ
     * @param config 送信設定
     */
    explicit SafeSockSendTo(int socket_fd, const SendConfig& config = SendConfig{});
    
    ~SafeSockSendTo();
    
    /**
     * @brief データを同期送信
     * @param data 送信データ
     * @param destination 送信先アドレス
     * @return 送信結果
     */
    SendResult send_sync(
        const std::vector<uint8_t>& data,
        const struct sockaddr_in& destination
    );
    
    /**
     * @brief データを非同期送信
     * @param data 送信データ
     * @param destination 送信先アドレス
     * @param timeout タイムアウト時間
     * @return 送信結果のFuture
     */
    std::future<SendResult> send_async(
        const std::vector<uint8_t>& data,
        const struct sockaddr_in& destination,
        std::chrono::milliseconds timeout = std::chrono::milliseconds{30000}
    );
    
    /**
     * @brief 複数データを一括送信
     * @param send_items 送信アイテムリスト
     * @param max_concurrent 最大同時送信数
     * @return 送信結果リスト
     */
    std::vector<std::future<SendResult>> send_multiple(
        const std::vector<std::pair<std::vector<uint8_t>, struct sockaddr_in>>& send_items,
        size_t max_concurrent = 10
    );
    
    /**
     * @brief ブロードキャスト送信
     * @param data 送信データ
     * @param port 送信先ポート
     * @param interface_addr インターフェースアドレス（空文字で全インターフェース）
     * @return 送信結果
     */
    SendResult broadcast_send(
        const std::vector<uint8_t>& data,
        uint16_t port,
        const std::string& interface_addr = ""
    );
    
    /**
     * @brief マルチキャスト送信
     * @param data 送信データ
     * @param multicast_addr マルチキャストアドレス
     * @param port 送信先ポート
     * @param ttl TTL値
     * @return 送信結果
     */
    SendResult multicast_send(
        const std::vector<uint8_t>& data,
        const std::string& multicast_addr,
        uint16_t port,
        uint8_t ttl = 1
    );
    
    /**
     * @brief 送信キューの状態を取得
     * @return キューサイズ
     */
    size_t get_queue_size() const;
    
    /**
     * @brief 送信キューの最大サイズを設定
     * @param max_size 最大サイズ
     */
    void set_max_queue_size(size_t max_size);
    
    /**
     * @brief 送信を一時停止/再開
     * @param paused 一時停止フラグ
     */
    void set_paused(bool paused);
    
    /**
     * @brief 保留中の送信をすべてキャンセル
     * @return キャンセルされた送信数
     */
    size_t cancel_all_pending();
    
    /**
     * @brief 特定の操作をキャンセル
     * @param operation_id 操作ID
     * @return キャンセルされた場合true
     */
    bool cancel_operation(const std::string& operation_id);
    
    /**
     * @brief 送信統計を取得
     * @return 統計情報
     */
    SendStats get_statistics() const;
    
    /**
     * @brief 送信パフォーマンスメトリクスを取得
     * @return メトリクスマップ
     */
    std::unordered_map<std::string, double> get_performance_metrics() const;
    
    /**
     * @brief ソケットオプションを最適化
     * @return 成功時true
     */
    bool optimize_socket_options();
    
    /**
     * @brief 送信バッファサイズを取得
     * @return バッファサイズ
     */
    int get_send_buffer_size() const;
    
    /**
     * @brief 送信バッファサイズを設定
     * @param size バッファサイズ
     * @return 成功時true
     */
    bool set_send_buffer_size(int size);
    
    /**
     * @brief ネットワーク品質を測定
     * @param destination 測定対象アドレス
     * @param test_data_size テストデータサイズ
     * @return 品質スコア（0.0-1.0）
     */
    double measure_network_quality(
        const struct sockaddr_in& destination,
        size_t test_data_size = 1024
    );
    
    /**
     * @brief デバッグモードを設定
     * @param enabled デバッグ有効フラグ
     */
    void set_debug_enabled(bool enabled);
    
    /**
     * @brief 送信処理を停止
     */
    void close();

private:
    int socket_fd_;
    SendConfig config_;
    
    // 非同期送信
    std::atomic<bool> running_{true};
    std::atomic<bool> paused_{false};
    std::queue<std::unique_ptr<AsyncSendItem>> send_queue_;
    std::mutex queue_mutex_;
    std::condition_variable queue_cv_;
    std::vector<std::unique_ptr<std::thread>> worker_threads_;
    size_t max_queue_size_{10000};
    
    // 統計・メトリクス
    SendStats stats_;
    std::atomic<bool> debug_enabled_{false};
    
    // プライベートメソッド
    void worker_loop();
    SendResult send_internal(const std::vector<uint8_t>& data, const struct sockaddr_in& destination);
    SendResult retry_send(const std::vector<uint8_t>& data, const struct sockaddr_in& destination, uint32_t retry_count);
    std::chrono::milliseconds calculate_retry_delay(uint32_t retry_count);
    bool is_temporary_error(int error_code);
    bool is_recoverable_error(int error_code);
    SendErrorType classify_error(int error_code);
    std::string error_to_string(SendErrorType error_type);
    std::string generate_operation_id();
    void log_debug(const std::string& message);
    bool validate_destination(const struct sockaddr_in& destination);
    size_t get_optimal_chunk_size(const struct sockaddr_in& destination);
    void cleanup_expired_operations();
};

/**
 * @brief アドレス変換ユーティリティ
 */
namespace address_utils {
    /**
     * @brief ホスト名とポートからsockaddr_inを作成
     * @param hostname ホスト名またはIPアドレス
     * @param port ポート番号
     * @return sockaddr_in構造体
     */
    std::optional<struct sockaddr_in> create_address(const std::string& hostname, uint16_t port);
    
    /**
     * @brief IPアドレス文字列からsockaddr_inを作成
     * @param ip_address IPアドレス文字列
     * @param port ポート番号
     * @return sockaddr_in構造体
     */
    std::optional<struct sockaddr_in> create_address_from_ip(const std::string& ip_address, uint16_t port);
    
    /**
     * @brief sockaddr_inから文字列表現を取得
     * @param addr sockaddr_in構造体
     * @return "IP:PORT" 形式の文字列
     */
    std::string address_to_string(const struct sockaddr_in& addr);
    
    /**
     * @brief ブロードキャストアドレスを作成
     * @param port ポート番号
     * @return ブロードキャストアドレス
     */
    struct sockaddr_in create_broadcast_address(uint16_t port);
    
    /**
     * @brief マルチキャストアドレスを作成
     * @param multicast_ip マルチキャストIPアドレス
     * @param port ポート番号
     * @return マルチキャストアドレス
     */
    std::optional<struct sockaddr_in> create_multicast_address(const std::string& multicast_ip, uint16_t port);
    
    /**
     * @brief アドレスが有効かチェック
     * @param addr sockaddr_in構造体
     * @return 有効な場合true
     */
    bool is_valid_address(const struct sockaddr_in& addr);
    
    /**
     * @brief プライベートIPアドレスかチェック
     * @param addr sockaddr_in構造体
     * @return プライベートIPの場合true
     */
    bool is_private_address(const struct sockaddr_in& addr);
    
    /**
     * @brief ローカルアドレスかチェック
     * @param addr sockaddr_in構造体
     * @return ローカルアドレスの場合true
     */
    bool is_local_address(const struct sockaddr_in& addr);
}

/**
 * @brief 送信ユーティリティファクトリー
 */
class SafeSendFactory {
public:
    /**
     * @brief 標準設定の送信ユーティリティを作成
     * @param socket_fd ソケットファイルディスクリプタ
     */
    static std::unique_ptr<SafeSockSendTo> create_standard(int socket_fd);
    
    /**
     * @brief 高信頼性設定の送信ユーティリティを作成
     * @param socket_fd ソケットファイルディスクリプタ
     */
    static std::unique_ptr<SafeSockSendTo> create_reliable(int socket_fd);
    
    /**
     * @brief 高性能設定の送信ユーティリティを作成
     * @param socket_fd ソケットファイルディスクリプタ
     */
    static std::unique_ptr<SafeSockSendTo> create_high_performance(int socket_fd);
    
    /**
     * @brief 低遅延設定の送信ユーティリティを作成
     * @param socket_fd ソケットファイルディスクリプタ
     */
    static std::unique_ptr<SafeSockSendTo> create_low_latency(int socket_fd);
};

} // namespace wiplib::client::utils
