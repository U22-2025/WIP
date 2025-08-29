#pragma once

#include <future>
#include <chrono>
#include <memory>
#include <string>
#include <vector>
#include <optional>
#include <unordered_map>
#include <mutex>
#include <atomic>

#include "wiplib/packet/location_packet.hpp"
#include "wiplib/packet/request.hpp"
#include "wiplib/packet/response.hpp"

namespace wiplib::client {

/**
 * @brief 位置解決結果
 */
struct LocationResolution {
    uint32_t area_code = 0;
    packet::Coordinate original_coordinate{};
    packet::Coordinate resolved_coordinate{};  // サーバーが解決した正確な座標
    uint8_t resolution_quality = 0;
    std::string area_name{};
    std::string prefecture{};
    std::string city{};
    double distance_from_original = 0.0;  // 元の座標からの距離（km）
    uint64_t server_timestamp = 0;
};

/**
 * @brief 境界チェック結果
 */
struct BoundaryCheckResult {
    bool is_valid = false;
    std::string error_message{};
    std::string suggested_action{};
    packet::Coordinate nearest_valid_point{};
};

/**
 * @brief GPSトラッキング情報
 */
struct GPSTrackingInfo {
    std::vector<packet::Coordinate> track_points{};
    std::chrono::steady_clock::time_point start_time{};
    std::chrono::steady_clock::time_point last_update{};
    double total_distance = 0.0;  // km
    double average_speed = 0.0;   // km/h
    uint32_t current_area_code = 0;
};

/**
 * @brief 拡張位置クライアント
 */
class EnhancedLocationClient {
public:
    /**
     * @brief コンストラクタ
     * @param host サーバーホスト
     * @param port サーバーポート
     */
    explicit EnhancedLocationClient(
        const std::string& host = "wip.ncc.onl", 
        uint16_t port = 4111
    );
    
    ~EnhancedLocationClient();
    
    /**
     * @brief 座標からエリアコードを解決（非同期）
     * @param coordinate 座標
     * @param timeout タイムアウト時間
     * @return 解決結果のFuture
     */
    std::future<LocationResolution> resolve_area_code_async(
        const packet::Coordinate& coordinate,
        std::chrono::milliseconds timeout = std::chrono::milliseconds{10000}
    );
    
    /**
     * @brief 座標からエリアコードを解決（同期）
     * @param coordinate 座標
     * @return 解決結果
     */
    LocationResolution resolve_area_code_sync(const packet::Coordinate& coordinate);
    
    /**
     * @brief 複数座標を一括解決
     * @param coordinates 座標リスト
     * @param timeout タイムアウト時間
     * @return 解決結果リスト
     */
    std::vector<std::future<LocationResolution>> resolve_multiple_async(
        const std::vector<packet::Coordinate>& coordinates,
        std::chrono::milliseconds timeout = std::chrono::milliseconds{10000}
    );
    
    /**
     * @brief GPS座標の精度管理を設定
     * @param min_precision 最小精度（小数点以下桁数）
     * @param max_precision 最大精度
     */
    void set_precision_policy(uint8_t min_precision = 3, uint8_t max_precision = 8);
    
    /**
     * @brief 地理的境界チェックを実行
     * @param coordinate チェック対象座標
     * @return チェック結果
     */
    BoundaryCheckResult check_geographic_bounds(const packet::Coordinate& coordinate) const;
    
    /**
     * @brief 座標の正規化（精度調整）
     * @param coordinate 元の座標
     * @param target_precision 目標精度
     * @return 正規化された座標
     */
    packet::Coordinate normalize_coordinate(
        const packet::Coordinate& coordinate, 
        uint8_t target_precision
    ) const;
    
    /**
     * @brief 2点間の距離を計算（Haversine公式）
     * @param coord1 座標1
     * @param coord2 座標2
     * @return 距離（km）
     */
    double calculate_distance(
        const packet::Coordinate& coord1, 
        const packet::Coordinate& coord2
    ) const;
    
    /**
     * @brief エリアコードキャッシュを有効化
     * @param enabled キャッシュ有効フラグ
     * @param ttl キャッシュTTL
     */
    void set_cache_enabled(bool enabled, std::chrono::seconds ttl = std::chrono::seconds{3600});
    
    /**
     * @brief GPSトラッキングを開始
     * @param tracking_id トラッキングID
     * @return 成功時true
     */
    bool start_gps_tracking(const std::string& tracking_id);
    
    /**
     * @brief GPSトラッキングポイントを追加
     * @param tracking_id トラッキングID
     * @param coordinate 座標
     * @return 成功時true
     */
    bool add_tracking_point(const std::string& tracking_id, const packet::Coordinate& coordinate);
    
    /**
     * @brief GPSトラッキングを停止
     * @param tracking_id トラッキングID
     * @return トラッキング情報
     */
    std::optional<GPSTrackingInfo> stop_gps_tracking(const std::string& tracking_id);
    
    /**
     * @brief アクティブなトラッキング一覧を取得
     * @return トラッキングID一覧
     */
    std::vector<std::string> get_active_trackings() const;
    
    /**
     * @brief 統計情報を取得
     * @return 統計情報マップ
     */
    std::unordered_map<std::string, uint64_t> get_statistics() const;
    
    /**
     * @brief デバッグモードを設定
     * @param enabled デバッグ有効フラグ
     */
    void set_debug_enabled(bool enabled);
    
    /**
     * @brief クライアントを閉じる
     */
    void close();

private:
    struct CacheEntry {
        LocationResolution resolution;
        std::chrono::steady_clock::time_point timestamp;
        std::chrono::seconds ttl;
        
        bool is_expired() const {
            auto elapsed = std::chrono::steady_clock::now() - timestamp;
            return elapsed > ttl;
        }
    };
    
    std::string host_;
    uint16_t port_;
    
    // 精度設定
    uint8_t min_precision_{3};
    uint8_t max_precision_{8};
    
    // キャッシュ
    std::atomic<bool> cache_enabled_{false};
    std::chrono::seconds cache_ttl_{3600};
    std::unordered_map<std::string, CacheEntry> cache_;
    mutable std::mutex cache_mutex_;
    
    // GPSトラッキング
    std::unordered_map<std::string, GPSTrackingInfo> active_trackings_;
    mutable std::mutex tracking_mutex_;
    
    // 統計
    mutable std::mutex stats_mutex_;
    std::unordered_map<std::string, std::atomic<uint64_t>> statistics_;
    
    // デバッグ
    std::atomic<bool> debug_enabled_{false};
    
    // プライベートメソッド
    LocationResolution send_resolution_request(const packet::Coordinate& coordinate);
    std::string coordinate_to_cache_key(const packet::Coordinate& coordinate) const;
    std::optional<LocationResolution> get_cached_resolution(const packet::Coordinate& coordinate) const;
    void cache_resolution(const packet::Coordinate& coordinate, const LocationResolution& resolution);
    void log_debug(const std::string& message) const;
    void increment_stat(const std::string& key);
    bool is_coordinate_in_japan(const packet::Coordinate& coordinate) const;
    bool is_coordinate_valid_range(const packet::Coordinate& coordinate) const;
    packet::Coordinate find_nearest_valid_point(const packet::Coordinate& coordinate) const;
    LocationResolution parse_location_response(const packet::GenericResponse& response) const;
};

/**
 * @brief 位置関連ユーティリティ
 */
namespace location_utils {
    /**
     * @brief 日本の境界を定義
     */
    struct JapanBounds {
        static constexpr float MIN_LATITUDE = 20.0f;
        static constexpr float MAX_LATITUDE = 46.0f;
        static constexpr float MIN_LONGITUDE = 123.0f;
        static constexpr float MAX_LONGITUDE = 154.0f;
    };
    
    /**
     * @brief 緯度経度が日本国内かチェック
     * @param latitude 緯度
     * @param longitude 経度
     * @return 日本国内の場合true
     */
    bool is_in_japan(float latitude, float longitude);
    
    /**
     * @brief 座標の精度を計算（GPS精度から）
     * @param gps_accuracy GPS精度（メートル）
     * @return 推奨精度（小数点以下桁数）
     */
    uint8_t calculate_precision_from_accuracy(double gps_accuracy);
    
    /**
     * @brief 座標文字列をパース
     * @param coord_str 座標文字列（例："35.6895,139.6917"）
     * @return パースされた座標
     */
    std::optional<packet::Coordinate> parse_coordinate_string(const std::string& coord_str);
    
    /**
     * @brief 座標を文字列に変換
     * @param coordinate 座標
     * @param precision 精度
     * @return 座標文字列
     */
    std::string coordinate_to_string(const packet::Coordinate& coordinate, uint8_t precision = 6);
    
    /**
     * @brief DMS（度分秒）形式から十進度に変換
     * @param degrees 度
     * @param minutes 分
     * @param seconds 秒
     * @return 十進度
     */
    double dms_to_decimal(int degrees, int minutes, double seconds);
    
    /**
     * @brief 十進度からDMS形式に変換
     * @param decimal 十進度
     * @return DMS形式（degrees, minutes, seconds）
     */
    std::tuple<int, int, double> decimal_to_dms(double decimal);
}

} // namespace wiplib::client
