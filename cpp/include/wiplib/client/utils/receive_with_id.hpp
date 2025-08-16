#pragma once

#include <future>
#include <chrono>
#include <memory>
#include <string>
#include <vector>
#include <unordered_map>
#include <unordered_set>
#include <mutex>
#include <atomic>
#include <functional>

#include "wiplib/packet/packet.hpp"
#include "wiplib/packet/response.hpp"

namespace wiplib::client::utils {

/**
 * @brief 受信タイムアウト例外
 */
class ReceiveTimeoutException : public std::runtime_error {
public:
    explicit ReceiveTimeoutException(uint16_t packet_id)
        : std::runtime_error("Receive timeout for packet ID: " + std::to_string(packet_id)),
          packet_id_(packet_id) {}
    
    uint16_t get_packet_id() const noexcept { return packet_id_; }

private:
    uint16_t packet_id_;
};

/**
 * @brief マルチパケット受信結果
 */
struct MultiPacketResult {
    std::vector<packet::GenericResponse> responses;
    std::chrono::milliseconds total_time;
    size_t successful_count = 0;
    size_t failed_count = 0;
    std::vector<std::string> error_messages;
};

/**
 * @brief 受信統計情報
 */
struct ReceiveStats {
    std::atomic<uint64_t> total_requests{0};
    std::atomic<uint64_t> successful_receives{0};
    std::atomic<uint64_t> timeout_receives{0};
    std::atomic<uint64_t> corrupted_packets{0};
    std::atomic<uint64_t> duplicate_packets{0};
    std::atomic<uint64_t> out_of_order_packets{0};
    std::atomic<uint64_t> bytes_received{0};
    std::chrono::steady_clock::time_point start_time{std::chrono::steady_clock::now()};
    ReceiveStats() = default;
    ReceiveStats(const ReceiveStats& other) {
        total_requests.store(other.total_requests.load());
        successful_receives.store(other.successful_receives.load());
        timeout_receives.store(other.timeout_receives.load());
        corrupted_packets.store(other.corrupted_packets.load());
        duplicate_packets.store(other.duplicate_packets.load());
        out_of_order_packets.store(other.out_of_order_packets.load());
        bytes_received.store(other.bytes_received.load());
        start_time = other.start_time;
    }
    ReceiveStats& operator=(const ReceiveStats& other) {
        if (this != &other) {
            total_requests.store(other.total_requests.load());
            successful_receives.store(other.successful_receives.load());
            timeout_receives.store(other.timeout_receives.load());
            corrupted_packets.store(other.corrupted_packets.load());
            duplicate_packets.store(other.duplicate_packets.load());
            out_of_order_packets.store(other.out_of_order_packets.load());
            bytes_received.store(other.bytes_received.load());
            start_time = other.start_time;
        }
        return *this;
    }
};

/**
 * @brief 受信コールバック関数型
 */
using ReceiveCallback = std::function<void(const packet::GenericResponse&, bool success, const std::string& error)>;

/**
 * @brief パケットID付き受信ユーティリティ
 */
class ReceiveWithId {
public:
    /**
     * @brief コンストラクタ
     * @param socket_fd ソケットファイルディスクリプタ
     * @param enable_ordering パケット順序保証有効フラグ
     */
    explicit ReceiveWithId(int socket_fd, bool enable_ordering = false);
    
    ~ReceiveWithId();
    
    /**
     * @brief 指定パケットIDのレスポンスを同期受信
     * @param packet_id 待機するパケットID
     * @param timeout タイムアウト時間
     * @return 受信したレスポンス
     * @throws ReceiveTimeoutException タイムアウト時
     */
    packet::GenericResponse receive_sync(
        uint16_t packet_id,
        std::chrono::milliseconds timeout = std::chrono::milliseconds{30000}
    );
    
    /**
     * @brief 指定パケットIDのレスポンスを非同期受信
     * @param packet_id 待機するパケットID
     * @param timeout タイムアウト時間
     * @return レスポンスのFuture
     */
    std::future<packet::GenericResponse> receive_async(
        uint16_t packet_id,
        std::chrono::milliseconds timeout = std::chrono::milliseconds{30000}
    );
    
    /**
     * @brief コールバック付き非同期受信
     * @param packet_id 待機するパケットID
     * @param callback 受信時コールバック
     * @param timeout タイムアウト時間
     */
    void receive_with_callback(
        uint16_t packet_id,
        ReceiveCallback callback,
        std::chrono::milliseconds timeout = std::chrono::milliseconds{30000}
    );
    
    /**
     * @brief 複数パケットの受信
     * @param packet_ids 待機するパケットIDリスト
     * @param timeout 全体のタイムアウト時間
     * @param partial_results 部分的な結果を許可
     * @return マルチパケット受信結果
     */
    MultiPacketResult receive_multiple(
        const std::vector<uint16_t>& packet_ids,
        std::chrono::milliseconds timeout = std::chrono::milliseconds{60000},
        bool partial_results = true
    );
    
    /**
     * @brief ストリーミング受信開始
     * @param callback 受信時コールバック
     * @param filter_func パケットフィルタ関数（nullptrで全パケット受信）
     */
    void start_streaming(
        ReceiveCallback callback,
        std::function<bool(const packet::GenericResponse&)> filter_func = nullptr
    );
    
    /**
     * @brief ストリーミング受信停止
     */
    void stop_streaming();
    
    /**
     * @brief 受信待ちパケットをキャンセル
     * @param packet_id キャンセルするパケットID
     * @return キャンセルされた場合true
     */
    bool cancel_receive(uint16_t packet_id);
    
    /**
     * @brief すべての受信待ちをキャンセル
     */
    void cancel_all_receives();
    
    /**
     * @brief 重複パケット検出を有効化
     * @param enabled 有効フラグ
     * @param window_size 検出ウィンドウサイズ（パケット数）
     */
    void set_duplicate_detection(bool enabled, size_t window_size = 1000);
    
    /**
     * @brief 受信バッファサイズを設定
     * @param buffer_size バッファサイズ（バイト）
     */
    void set_receive_buffer_size(size_t buffer_size);
    
    /**
     * @brief 受信統計を取得
     * @return 統計情報
     */
    ReceiveStats get_statistics() const;
    
    /**
     * @brief 現在の受信待ちパケット数を取得
     * @return 受信待ちパケット数
     */
    size_t get_pending_receive_count() const;
    
    /**
     * @brief デバッグモードを設定
     * @param enabled デバッグ有効フラグ
     */
    void set_debug_enabled(bool enabled);

private:
    struct PendingReceive {
        uint16_t packet_id;
        std::promise<packet::GenericResponse> promise;
        ReceiveCallback callback;
        std::chrono::steady_clock::time_point start_time;
        std::chrono::milliseconds timeout;
        bool has_callback;
    };
    
    int socket_fd_;
    bool enable_ordering_;
    std::atomic<bool> running_{true};
    std::atomic<bool> streaming_{false};
    
    // 受信スレッド
    std::unique_ptr<std::thread> receive_thread_;
    
    // 受信待ちマップ
    std::unordered_map<uint16_t, std::unique_ptr<PendingReceive>> pending_receives_;
    std::mutex pending_mutex_;
    
    // ストリーミング
    ReceiveCallback streaming_callback_;
    std::function<bool(const packet::GenericResponse&)> streaming_filter_;
    
    // 順序保証
    std::unordered_map<uint16_t, packet::GenericResponse> out_of_order_buffer_;
    uint16_t expected_sequence_number_{0};
    std::mutex ordering_mutex_;
    
    // 重複検出
    std::atomic<bool> duplicate_detection_enabled_{false};
    size_t duplicate_window_size_{1000};
    std::unordered_set<uint16_t> recent_packet_ids_;
    std::mutex duplicate_mutex_;
    
    // バッファ設定
    size_t receive_buffer_size_{8192};
    
    // 統計・デバッグ
    ReceiveStats stats_;
    std::atomic<bool> debug_enabled_{false};
    
    // プライベートメソッド
    void receive_loop();
    packet::GenericResponse receive_single_packet();
    void process_received_packet(const packet::GenericResponse& response);
    void handle_ordered_packet(const packet::GenericResponse& response);
    void deliver_packet(const packet::GenericResponse& response);
    bool is_duplicate_packet(uint16_t packet_id);
    void record_packet_id(uint16_t packet_id);
    void cleanup_expired_receives();
    void log_debug(const std::string& message);
};

/**
 * @brief 受信ユーティリティファクトリー
 */
class ReceiveUtilsFactory {
public:
    /**
     * @brief 標準受信ユーティリティを作成
     * @param socket_fd ソケットファイルディスクリプタ
     */
    static std::unique_ptr<ReceiveWithId> create_standard(int socket_fd);
    
    /**
     * @brief 順序保証付き受信ユーティリティを作成
     * @param socket_fd ソケットファイルディスクリプタ
     */
    static std::unique_ptr<ReceiveWithId> create_ordered(int socket_fd);
    
    /**
     * @brief 高性能受信ユーティリティを作成
     * @param socket_fd ソケットファイルディスクリプタ
     */
    static std::unique_ptr<ReceiveWithId> create_high_performance(int socket_fd);
};

} // namespace wiplib::client::utils
