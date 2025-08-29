#pragma once

#include <string>
#include <string_view>
#include <cstdint>
#include <vector>
#include <future>
#include <chrono>
#include <optional>
#include <unordered_map>
#include <mutex>
#include <filesystem>

#include "wiplib/expected.hpp"
#include "wiplib/error.hpp"
#include "wiplib/packet/location_packet.hpp"
#include "wiplib/client/auth_config.hpp"

namespace wiplib::client {

/**
 * @brief GPS座標精度レベル
 */
enum class PrecisionLevel {
    Low = 0,      // ±1000m
    Medium = 1,   // ±100m  
    High = 2,     // ±10m
    VeryHigh = 3  // ±1m
};


/**
 * @brief 座標変換結果
 */
struct CoordinateResult {
    std::string area_code;
    packet::Coordinate original_coordinate;
    packet::Coordinate normalized_coordinate;
    PrecisionLevel precision_level = PrecisionLevel::Medium;
    double accuracy_meters = 100.0;
    std::chrono::milliseconds response_time{0};
};

class LocationClient {
public:
  LocationClient(std::string host = "wip.ncc.onl", uint16_t port = 4109)
    : host_(std::move(host)), port_(port) {
        // Python互換のキャッシュファイルパス
        cache_file_path_ = std::filesystem::current_path() / "coordinate_cache.json";
        load_cache_from_disk();
    }

  static LocationClient from_env();
  static std::string default_host();
  static uint16_t default_port();

  // 既存メソッド
  wiplib::Result<std::string> get_area_code_simple(double latitude, double longitude) noexcept;

  /**
   * @brief 座標→エリアコード変換（詳細版）
   * @param coordinate 座標データ
   * @param precision_level 精度レベル
   * @param timeout タイムアウト時間
   * @return 変換結果
   */
  std::future<wiplib::Result<CoordinateResult>> get_area_code_detailed_async(
      const packet::Coordinate& coordinate,
      PrecisionLevel precision_level = PrecisionLevel::Medium,
      std::chrono::milliseconds timeout = std::chrono::milliseconds{5000}
  );

  /**
   * @brief 複数座標の一括変換
   * @param coordinates 座標リスト
   * @param precision_level 精度レベル
   * @param timeout タイムアウト時間
   * @return 変換結果リスト
   */
  std::future<std::vector<wiplib::Result<CoordinateResult>>> batch_convert_async(
      const std::vector<packet::Coordinate>& coordinates,
      PrecisionLevel precision_level = PrecisionLevel::Medium,
      std::chrono::milliseconds timeout = std::chrono::milliseconds{30000}
  );

  /**
   * @brief GPS座標の精度管理
   * @param coordinate 座標データ
   * @param target_precision 目標精度
   * @return 精度管理された座標
   */
  packet::Coordinate manage_gps_precision(
      const packet::Coordinate& coordinate,
      PrecisionLevel target_precision
  ) const;


  /**
   * @brief 座標の正規化
   * @param coordinate 座標データ
   * @param precision 正規化精度
   * @return 正規化された座標
   */
  packet::Coordinate normalize_coordinate(
      const packet::Coordinate& coordinate,
      uint8_t precision = 6
  ) const;

  /**
   * @brief 座標精度の推定
   * @param coordinate 座標データ
   * @return 推定精度レベル
   */
  PrecisionLevel estimate_precision_level(const packet::Coordinate& coordinate) const;

  /**
   * @brief 座標の妥当性検証
   * @param coordinate 座標データ
   * @return 検証結果とエラーメッセージ
   */
  std::pair<bool, std::string> validate_coordinate(const packet::Coordinate& coordinate) const;


  /**
   * @brief キャッシュを有効化/無効化
   * @param enabled キャッシュ有効フラグ
   * @param cache_ttl キャッシュTTL
   */
  void set_cache_enabled(bool enabled, std::chrono::seconds cache_ttl = std::chrono::seconds{300});

  /**
   * @brief 座標変換統計を取得
   * @return 統計情報
   */
  std::unordered_map<std::string, uint64_t> get_conversion_statistics() const;

  /**
   * @brief 統計をリセット
   */
  void reset_statistics();

  /**
   * @brief サーバー設定変更
   * @param host サーバーホスト
   * @param port サーバーポート
   */
  void set_server(std::string host, uint16_t port) { 
      host_ = std::move(host); 
      port_ = port; 
  }
  
  /**
   * @brief キャッシュファイルパスを設定（Python互換）
   * @param cache_file_path キャッシュファイルパス
   */
  void set_cache_file_path(const std::filesystem::path& cache_file_path) {
    cache_file_path_ = cache_file_path;
    load_cache_from_disk();
  }

  void set_auth_config(const AuthConfig& cfg) { auth_cfg_ = cfg; }

private:
  std::string host_;
  uint16_t port_;
  AuthConfig auth_cfg_{};
  
  // キャッシュ設定
  bool cache_enabled_ = false;
  std::chrono::seconds cache_ttl_{300};
  mutable std::unordered_map<std::string, std::pair<CoordinateResult, std::chrono::steady_clock::time_point>> cache_;
  mutable std::mutex cache_mutex_;
  std::filesystem::path cache_file_path_;
  
  // 統計
  mutable std::mutex stats_mutex_;
  mutable std::unordered_map<std::string, uint64_t> conversion_stats_;
  
  // プライベートメソッド
  CoordinateResult perform_coordinate_conversion(
      const packet::Coordinate& coordinate,
      PrecisionLevel precision_level,
      std::chrono::milliseconds timeout
  ) const;
  
  std::string generate_cache_key(const packet::Coordinate& coordinate, PrecisionLevel precision_level) const;
  
  std::optional<CoordinateResult> get_cached_result(const std::string& cache_key) const;
  
  void cache_result(const std::string& cache_key, const CoordinateResult& result) const;

  void load_cache_from_disk();
  void save_cache_to_disk() const;

  void update_statistics(const std::string& key, uint64_t increment = 1) const;
  
  double calculate_accuracy_from_precision(PrecisionLevel precision_level) const;

  friend class LocationClientCacheTestHelper;
};

/**
 * @brief LocationClientファクトリー
 */
class LocationClientFactory {
public:
    /**
     * @brief 基本LocationClientを作成
     */
    static std::unique_ptr<LocationClient> create_basic(
        const std::string& host = "wip.ncc.onl", 
        uint16_t port = 4109
    );
    
    /**
     * @brief 高精度LocationClientを作成
     */
    static std::unique_ptr<LocationClient> create_high_precision(
        const std::string& host = "wip.ncc.onl", 
        uint16_t port = 4109
    );
};

} // namespace wiplib::client
