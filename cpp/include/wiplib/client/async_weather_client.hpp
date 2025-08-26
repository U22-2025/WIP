#pragma once

#include <future>
#include <chrono>
#include <memory>
#include <string>
#include <vector>
#include <unordered_map>
#include <functional>
#include <atomic>
#include <mutex>
#include <thread>
#include <queue>
#include <condition_variable>

#include "wiplib/packet/packet.hpp"
#include "wiplib/packet/extended_field.hpp"
#include "wiplib/packet/request.hpp"
#include "wiplib/packet/response.hpp"

namespace wiplib::client {

/**
 * @brief 非同期リクエスト結果
 */
template<typename T>
struct AsyncResult {
    std::future<T> future;
    std::string request_id;
    std::chrono::steady_clock::time_point start_time;
    std::chrono::milliseconds timeout;
    
    /**
     * @brief リクエストがタイムアウトしたかチェック
     */
    bool is_timed_out() const {
        auto elapsed = std::chrono::steady_clock::now() - start_time;
        return elapsed > timeout;
    }
    
    /**
     * @brief 結果が利用可能かチェック
     */
    bool is_ready() const {
        return future.wait_for(std::chrono::seconds(0)) == std::future_status::ready;
    }
};

/**
 * @brief 天気データレスポンス
 */
struct WeatherData {
    uint32_t area_code = 0;
    uint16_t weather_code = 0;
    int8_t temperature = 0;
    uint8_t precipitation_prob = 0;
    std::vector<std::string> alerts{};
    std::vector<std::string> disasters{};
    uint64_t timestamp = 0;
    float data_quality = 1.0f;
};

/**
 * @brief 接続統計情報
 */
struct ConnectionStats {
    uint64_t total_requests = 0;
    uint64_t successful_requests = 0;
    uint64_t failed_requests = 0;
    uint64_t timeout_requests = 0;
    uint64_t retry_count = 0;
    uint64_t bytes_sent = 0;
    uint64_t bytes_received = 0;
    std::chrono::steady_clock::time_point connection_start_time{std::chrono::steady_clock::now()};
};

/**
 * @brief キャッシュエントリ
 */
struct CacheEntry {
    WeatherData data;
    std::chrono::steady_clock::time_point timestamp;
    std::chrono::seconds ttl;
    
    bool is_expired() const {
        auto elapsed = std::chrono::steady_clock::now() - timestamp;
        return elapsed > ttl;
    }
};

/**
 * @brief 接続プール管理
 */
class ConnectionPool {
public:
    explicit ConnectionPool(size_t max_connections = 10);
    ~ConnectionPool();
    
    /**
     * @brief 接続を取得
     */
    int acquire_connection(const std::string& host, uint16_t port);
    
    /**
     * @brief 接続を返却
     */
    void release_connection(int socket_fd);
    
    /**
     * @brief プールを閉じる
     */
    void close_all();
    
    /**
     * @brief 統計情報を取得
     */
    size_t get_active_connections() const;
    size_t get_available_connections() const;

private:
    struct Connection {
        int socket_fd;
        std::string host;
        uint16_t port;
        std::chrono::steady_clock::time_point last_used;
        bool in_use;
    };
    
    mutable std::mutex mutex_;
    std::vector<Connection> connections_;
    size_t max_connections_;
    
    void cleanup_idle_connections();
    bool is_connection_valid(int socket_fd) const;
};

/**
 * @brief 非同期天気クライアント
 */
class AsyncWeatherClient {
public:
    /**
     * @brief コンストラクタ
     * @param host サーバーホスト
     * @param port サーバーポート
     * @param max_concurrent_requests 最大同時リクエスト数
     */
    explicit AsyncWeatherClient(
        const std::string& host = "localhost", 
        uint16_t port = 4110,
        size_t max_concurrent_requests = 100
    );
    
    ~AsyncWeatherClient();
    
    /**
     * @brief エリアコードから天気データを非同期取得
     * @param area_code エリアコード
     * @param timeout タイムアウト時間
     * @return 非同期結果
     */
    AsyncResult<WeatherData> get_weather_async(
        uint32_t area_code, 
        std::chrono::milliseconds timeout = std::chrono::milliseconds{30000}
    );
    
    /**
     * @brief 座標から天気データを非同期取得
     * @param latitude 緯度
     * @param longitude 経度
     * @param timeout タイムアウト時間
     * @return 非同期結果
     */
    AsyncResult<WeatherData> get_weather_by_coordinates_async(
        float latitude, 
        float longitude,
        std::chrono::milliseconds timeout = std::chrono::milliseconds{30000}
    );
    
    /**
     * @brief 複数エリアの天気データを一括取得
     * @param area_codes エリアコードリスト
     * @param timeout タイムアウト時間
     * @return 非同期結果リスト
     */
    std::vector<AsyncResult<WeatherData>> get_multiple_weather_async(
        const std::vector<uint32_t>& area_codes,
        std::chrono::milliseconds timeout = std::chrono::milliseconds{30000}
    );
    
    /**
     * @brief キャッシュを有効化/無効化
     * @param enabled キャッシュ有効フラグ
     * @param default_ttl デフォルトTTL
     */
    void set_cache_enabled(bool enabled, std::chrono::seconds default_ttl = std::chrono::seconds{300});
    
    /**
     * @brief リトライ設定
     * @param max_retries 最大リトライ回数
     * @param base_delay ベース遅延時間
     * @param max_delay 最大遅延時間
     */
    void set_retry_policy(uint8_t max_retries, 
                         std::chrono::milliseconds base_delay = std::chrono::milliseconds{1000},
                         std::chrono::milliseconds max_delay = std::chrono::milliseconds{30000});
    
    /**
     * @brief デバッグロギングを有効化/無効化
     * @param enabled デバッグ有効フラグ
     */
    void set_debug_enabled(bool enabled);
    
    /**
     * @brief 統計情報を取得
     * @return 接続統計
     */
    ConnectionStats get_stats() const;
    
    /**
     * @brief キャッシュをクリア
     */
    void clear_cache();
    
    /**
     * @brief すべての進行中リクエストをキャンセル
     */
    void cancel_all_requests();
    
    /**
     * @brief クライアントを閉じる
     */
    void close();

private:
    struct RequestContext {
        std::string request_id;
        packet::GenericRequest request;
        std::promise<WeatherData> promise;
        std::chrono::steady_clock::time_point start_time;
        std::chrono::milliseconds timeout;
        uint8_t retry_count;
    };
    
    std::string host_;
    uint16_t port_;
    size_t max_concurrent_requests_;
    
    // 非同期処理
    std::unique_ptr<std::thread> worker_thread_;
    std::atomic<bool> running_{true};
    std::queue<std::unique_ptr<RequestContext>> request_queue_;
    std::mutex queue_mutex_;
    std::condition_variable queue_cv_;
    
    // 接続管理
    std::unique_ptr<ConnectionPool> connection_pool_;
    
    // キャッシュ
    std::atomic<bool> cache_enabled_{false};
    std::chrono::seconds default_cache_ttl_{300};
    std::unordered_map<uint32_t, CacheEntry> cache_;
    mutable std::mutex cache_mutex_;
    
    // リトライ設定
    uint8_t max_retries_{3};
    std::chrono::milliseconds base_retry_delay_{1000};
    std::chrono::milliseconds max_retry_delay_{30000};
    
    // 統計・ログ（内部はatomicを使用）
    struct {
        std::atomic<uint64_t> total_requests{0};
        std::atomic<uint64_t> successful_requests{0};
        std::atomic<uint64_t> failed_requests{0};
        std::atomic<uint64_t> timeout_requests{0};
        std::atomic<uint64_t> retry_count{0};
        std::atomic<uint64_t> bytes_sent{0};
        std::atomic<uint64_t> bytes_received{0};
        std::chrono::steady_clock::time_point connection_start_time{std::chrono::steady_clock::now()};
    } stats_;
    std::atomic<bool> debug_enabled_{false};
    
    // 進行中のリクエスト
    std::unordered_map<std::string, std::unique_ptr<RequestContext>> active_requests_;
    std::mutex active_requests_mutex_;
    
    // プライベートメソッド
    void worker_loop();
    void process_request(std::unique_ptr<RequestContext> context);
    WeatherData send_request_sync(const packet::GenericRequest& request);
    std::optional<WeatherData> get_cached_data(uint32_t area_code) const;
    void cache_data(uint32_t area_code, const WeatherData& data);
    void log_debug(const std::string& message) const;
    std::string generate_request_id() const;
    std::chrono::milliseconds calculate_retry_delay(uint8_t retry_count) const;
    bool should_retry(const std::exception& e) const;
    WeatherData parse_response(const packet::GenericResponse& response) const;
};

/**
 * @brief 非同期天気クライアントファクトリー
 */
class AsyncWeatherClientFactory {
public:
    /**
     * @brief デフォルト設定でクライアントを作成
     */
    static std::unique_ptr<AsyncWeatherClient> create_default();
    
    /**
     * @brief 高性能設定でクライアントを作成
     */
    static std::unique_ptr<AsyncWeatherClient> create_high_performance();
    
    /**
     * @brief 低リソース設定でクライアントを作成
     */
    static std::unique_ptr<AsyncWeatherClient> create_low_resource();
    
    /**
     * @brief カスタム設定でクライアントを作成
     */
    static std::unique_ptr<AsyncWeatherClient> create_custom(
        const std::string& host,
        uint16_t port,
        size_t max_concurrent_requests,
        bool enable_cache,
        std::chrono::seconds cache_ttl
    );
};

} // namespace wiplib::client