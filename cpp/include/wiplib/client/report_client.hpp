#pragma once

#include <future>
#include <chrono>
#include <memory>
#include <string>
#include <vector>
#include <queue>
#include <mutex>
#include <condition_variable>
#include <atomic>
#include <thread>

#include "wiplib/packet/report_packet.hpp"
#include "wiplib/packet/request.hpp"
#include "wiplib/packet/response.hpp"

namespace wiplib::client {

/**
 * @brief レポート送信結果
 */
struct ReportResult {
    bool success = false;
    uint8_t status_code = 0;
    uint16_t processed_count = 0;
    std::string message{};
    uint64_t server_timestamp = 0;
    std::chrono::milliseconds response_time{};
};

/**
 * @brief バッチ処理設定
 */
struct BatchConfig {
    size_t max_batch_size = 100;          // 最大バッチサイズ
    std::chrono::milliseconds max_wait_time{5000};  // 最大待機時間
    size_t min_batch_size = 1;             // 最小バッチサイズ
    bool enable_compression = true;        // 圧縮有効
    uint8_t compression_level = 6;         // 圧縮レベル（0-9）
};

/**
 * @brief データ圧縮・暗号化設定
 */
struct SecurityConfig {
    bool enable_encryption = false;       // 暗号化有効
    std::string encryption_key{};         // 暗号化キー
    std::string encryption_algorithm = "AES-256-GCM";  // 暗号化アルゴリズム
    bool verify_ssl = true;               // SSL証明書検証
    std::chrono::seconds key_rotation_interval{3600}; // キーローテーション間隔
};

/**
 * @brief レポート送信統計
 */
struct ReportStats {
    std::atomic<uint64_t> total_reports_sent{0};
    std::atomic<uint64_t> successful_reports{0};
    std::atomic<uint64_t> failed_reports{0};
    std::atomic<uint64_t> batched_reports{0};
    std::atomic<uint64_t> compressed_bytes_saved{0};
    std::atomic<uint64_t> total_processing_time_ms{0};
    std::chrono::steady_clock::time_point start_time{std::chrono::steady_clock::now()};
};

/**
 * @brief レポートクライアント
 */
class ReportClient {
public:
    /**
     * @brief コンストラクタ
     * @param host サーバーホスト
     * @param port サーバーポート
     * @param enable_batching バッチ処理有効フラグ
     */
    explicit ReportClient(
        const std::string& host = "localhost", 
        uint16_t port = 4112,
        bool enable_batching = true
    );
    
    ~ReportClient();
    
    /**
     * @brief センサーデータを送信（非同期）
     * @param sensor_data センサーデータ
     * @param timeout タイムアウト時間
     * @return 送信結果のFuture
     */
    std::future<ReportResult> send_sensor_data_async(
        const packet::SensorData& sensor_data,
        std::chrono::milliseconds timeout = std::chrono::milliseconds{10000}
    );
    
    /**
     * @brief センサーデータを送信（同期）
     * @param sensor_data センサーデータ
     * @return 送信結果
     */
    ReportResult send_sensor_data_sync(const packet::SensorData& sensor_data);
    
    /**
     * @brief バイナリデータを送信
     * @param binary_data バイナリデータ
     * @param metadata メタデータ
     * @param timeout タイムアウト時間
     * @return 送信結果のFuture
     */
    std::future<ReportResult> send_binary_data_async(
        const std::vector<uint8_t>& binary_data,
        const std::unordered_map<std::string, std::string>& metadata = {},
        std::chrono::milliseconds timeout = std::chrono::milliseconds{30000}
    );
    
    /**
     * @brief 複数データを一括送信
     * @param sensor_data_list センサーデータリスト
     * @param timeout タイムアウト時間
     * @return 送信結果のFuture
     */
    std::future<ReportResult> send_batch_async(
        const std::vector<packet::SensorData>& sensor_data_list,
        std::chrono::milliseconds timeout = std::chrono::milliseconds{60000}
    );
    
    /**
     * @brief バッチ処理設定を変更
     * @param config バッチ設定
     */
    void set_batch_config(const BatchConfig& config);
    
    /**
     * @brief セキュリティ設定を変更
     * @param config セキュリティ設定
     */
    void set_security_config(const SecurityConfig& config);
    
    /**
     * @brief データ品質チェックを有効化
     * @param enabled 有効フラグ
     * @param min_quality 最小品質閾値（0-255）
     */
    void set_quality_check_enabled(bool enabled, uint8_t min_quality = 200);
    
    /**
     * @brief 重複データ検出を有効化
     * @param enabled 有効フラグ
     * @param time_window 検出時間窓（同一データの重複判定時間）
     */
    void set_duplicate_detection_enabled(bool enabled, 
                                        std::chrono::seconds time_window = std::chrono::seconds{60});
    
    /**
     * @brief 自動リトライを設定
     * @param max_retries 最大リトライ回数
     * @param base_delay ベース遅延時間
     * @param max_delay 最大遅延時間
     */
    void set_retry_policy(uint8_t max_retries,
                         std::chrono::milliseconds base_delay = std::chrono::milliseconds{1000},
                         std::chrono::milliseconds max_delay = std::chrono::milliseconds{30000});
    
    /**
     * @brief バックプレッシャー制御を設定
     * @param max_pending_requests 最大保留リクエスト数
     * @param queue_timeout キュータイムアウト
     */
    void set_backpressure_control(size_t max_pending_requests = 1000,
                                 std::chrono::milliseconds queue_timeout = std::chrono::milliseconds{30000});
    
    /**
     * @brief ヘルスチェックを実行
     * @return サーバーが正常な場合true
     */
    bool health_check();
    
    /**
     * @brief 統計情報を取得
     * @return 統計情報
     */
    ReportStats get_statistics() const;
    
    /**
     * @brief パフォーマンスメトリクスを取得
     * @return メトリクスマップ
     */
    std::unordered_map<std::string, double> get_performance_metrics() const;
    
    /**
     * @brief 保留中のデータを強制送信
     * @return 送信されたアイテム数
     */
    size_t flush_pending_data();
    
    /**
     * @brief デバッグモードを設定
     * @param enabled デバッグ有効フラグ
     */
    void set_debug_enabled(bool enabled);
    
    /**
     * @brief すべての処理を停止してクライアントを閉じる
     */
    void close();

private:
    struct PendingReport {
        packet::SensorData sensor_data;
        std::vector<uint8_t> binary_data;
        std::unordered_map<std::string, std::string> metadata;
        std::chrono::steady_clock::time_point timestamp;
        std::promise<ReportResult> promise;
        uint8_t retry_count = 0;
    };
    
    std::string host_;
    uint16_t port_;
    
    // バッチ処理
    std::atomic<bool> batching_enabled_{true};
    BatchConfig batch_config_;
    std::queue<std::unique_ptr<PendingReport>> batch_queue_;
    std::mutex batch_mutex_;
    std::condition_variable batch_cv_;
    std::unique_ptr<std::thread> batch_worker_;
    
    // セキュリティ
    SecurityConfig security_config_;
    
    // 品質チェック
    std::atomic<bool> quality_check_enabled_{false};
    uint8_t min_quality_threshold_{200};
    
    // 重複検出
    std::atomic<bool> duplicate_detection_enabled_{false};
    std::chrono::seconds duplicate_time_window_{60};
    std::unordered_map<std::string, std::chrono::steady_clock::time_point> recent_data_hashes_;
    std::mutex duplicate_mutex_;
    
    // リトライ
    uint8_t max_retries_{3};
    std::chrono::milliseconds base_retry_delay_{1000};
    std::chrono::milliseconds max_retry_delay_{30000};
    
    // バックプレッシャー
    size_t max_pending_requests_{1000};
    std::chrono::milliseconds queue_timeout_{30000};
    std::atomic<size_t> pending_request_count_{0};
    
    // 統計・メトリクス
    ReportStats stats_;
    std::atomic<bool> debug_enabled_{false};
    
    // 制御フラグ
    std::atomic<bool> running_{true};
    
    // プライベートメソッド
    void batch_worker_loop();
    void process_batch();
    ReportResult send_report_internal(const packet::ReportRequest& request);
    std::vector<uint8_t> compress_data(const std::vector<uint8_t>& data);
    std::vector<uint8_t> decompress_data(const std::vector<uint8_t>& compressed_data);
    std::vector<uint8_t> encrypt_data(const std::vector<uint8_t>& data);
    std::vector<uint8_t> decrypt_data(const std::vector<uint8_t>& encrypted_data);
    bool validate_data_quality(const packet::SensorData& data);
    std::string calculate_data_hash(const packet::SensorData& data);
    bool is_duplicate_data(const std::string& data_hash);
    void record_data_hash(const std::string& data_hash);
    void cleanup_old_hashes();
    std::chrono::milliseconds calculate_retry_delay(uint8_t retry_count);
    void log_debug(const std::string& message);
    ReportResult parse_report_response(const packet::GenericResponse& response);
};

/**
 * @brief レポートクライアントファクトリー
 */
class ReportClientFactory {
public:
    /**
     * @brief 標準設定のクライアントを作成
     */
    static std::unique_ptr<ReportClient> create_standard();
    
    /**
     * @brief 高スループット設定のクライアントを作成
     */
    static std::unique_ptr<ReportClient> create_high_throughput();
    
    /**
     * @brief セキュア設定のクライアントを作成
     */
    static std::unique_ptr<ReportClient> create_secure();
    
    /**
     * @brief リアルタイム設定のクライアントを作成（バッチ無効）
     */
    static std::unique_ptr<ReportClient> create_realtime();
};

} // namespace wiplib::client