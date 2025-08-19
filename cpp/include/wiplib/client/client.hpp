#pragma once

#include <memory>
#include <optional>
#include <string>
#include <string_view>
#include <vector>
#include <future>
#include <any>
#include <unordered_map>

#include "wiplib/client/wip_client.hpp"
#include "wiplib/client/weather_client.hpp"
#include "wiplib/client/location_client.hpp"
#include "wiplib/client/query_client.hpp"
#include "wiplib/client/report_client.hpp"
#include "wiplib/client/auth_config.hpp"

namespace wiplib::client {

// 既存型のエイリアスでPython名に合わせる
using ServerConfig = ::wiplib::client::ServerConfig;
using ClientState = ::wiplib::client::ClientState;
using WeatherOptions = ::wiplib::client::WeatherOptions;
using WeatherData = ::wiplib::client::WeatherData;
using ReportResult = ::wiplib::client::ReportResult;

struct ClientSnapshot {
  std::optional<double> latitude{};
  std::optional<double> longitude{};
  std::optional<std::string> area_code{};
  std::string host{};
  uint16_t port{};
};

/**
 * @brief WIPクライアント（Python Clientに対応）
 */
class Client {
public:
  /**
   * @brief コンストラクタ
   * @param host サーバーホスト（nulloptの場合デフォルト）
   * @param port サーバーポート（nulloptの場合デフォルト）
   * @param server_config サーバー設定（nulloptの場合デフォルト）
   * @param debug デバッグ有効
   * @param latitude 初期緯度
   * @param longitude 初期経度  
   * @param area_code 初期エリアコード
   */
  explicit Client(
      std::optional<std::string> host = std::nullopt,
      std::optional<uint16_t> port = std::nullopt,
      std::optional<ServerConfig> server_config = std::nullopt,
      bool debug = false,
      std::optional<double> latitude = std::nullopt,
      std::optional<double> longitude = std::nullopt,
      std::optional<std::string> area_code = std::nullopt
  );

  // プロパティアクセス（Python互換）
  std::optional<double> latitude() const noexcept;
  std::optional<double> longitude() const noexcept;
  std::optional<std::string> area_code() const noexcept;

  // 座標設定
  void set_coordinates(double lat, double lon);


  // サーバ設定（Pythonと同名）
  void set_server(const std::string& host);
  void set_server(const std::string& host, uint16_t port);

  // 認証設定
  void set_auth_config(const AuthConfig& auth_config);

  // 互換API
  void close();

  // スナップショット
  ClientSnapshot get_state() const noexcept;

  // 天気データ取得API（Python互換）
  Result<WeatherData> get_weather(
      bool weather = true,
      bool temperature = true,
      bool precipitation_prob = true,
      bool alert = false,
      bool disaster = false,
      uint8_t day = 0,
      bool proxy = false
  );

  Result<WeatherData> get_weather_by_coordinates(
      double lat, double lon,
      bool weather = true,
      bool temperature = true,
      bool precipitation_prob = true,
      bool alert = false,
      bool disaster = false,
      uint8_t day = 0,
      bool proxy = false
  );

  Result<WeatherData> get_weather_by_area_code(
      std::string_view area_code,
      bool weather = true,
      bool temperature = true,
      bool precipitation_prob = true,
      bool alert = false,
      bool disaster = false,
      uint8_t day = 0,
      bool proxy = false
  );

  // レポート送信API（Python互換）
  void set_sensor_data(const std::string& area_code, 
                      std::optional<int> weather_code = {},
                      std::optional<float> temperature = {},
                      std::optional<int> precipitation_prob = {},
                      std::optional<std::vector<std::string>> alert = {},
                      std::optional<std::vector<std::string>> disaster = {});
  
  void set_area_code(const std::string& area_code);
  void set_weather_code(int weather_code);
  void set_temperature(float temperature);
  void set_precipitation_prob(int precipitation_prob);
  void set_alert(const std::vector<std::string>& alert);
  void set_disaster(const std::vector<std::string>& disaster);
  
  Result<ReportResult> send_report_data(bool proxy = false,
                                        std::optional<ServerConfig> report_server = std::nullopt);
  std::future<Result<ReportResult>> send_report_data_async(bool proxy = false,
                                                           std::optional<ServerConfig> report_server = std::nullopt);
  Result<ReportResult> send_data_simple(bool proxy = false,
                                        std::optional<ServerConfig> report_server = std::nullopt);
  
  std::unordered_map<std::string, std::any> get_current_data() const;
  void clear_data();
  
  // 後方互換性メソッド
  Result<ReportResult> send_report(bool proxy = false,
                                   std::optional<ServerConfig> report_server = std::nullopt);
  Result<ReportResult> send_current_data(bool proxy = false,
                                         std::optional<ServerConfig> report_server = std::nullopt);

  // RAII サポート（Python with相当）
  Client& operator()() { return *this; } // __enter__ equivalent
  void release() { close(); } // __exit__ equivalent

private:
  ServerConfig config_;
  ClientState state_;
  bool debug_;
    
  // 内部クライアント
  std::unique_ptr<WipClient> wip_client_;
  std::unique_ptr<ReportClient> report_client_;
    
  // ヘルパーメソッド
  WeatherOptions build_options(bool weather, bool temperature, bool precipitation_prob, 
                              bool alert, bool disaster, uint8_t day) const;
  void validate_port() const;
  void initialize_wip_client();
  void initialize_report_client(bool proxy = false,
                                std::optional<ServerConfig> report_server = std::nullopt);
};

} // namespace wiplib::client

