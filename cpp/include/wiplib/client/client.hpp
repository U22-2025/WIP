#pragma once

#include <memory>
#include <optional>
#include <string>
#include <string_view>

#include "wiplib/client/wip_client.hpp"
#include "wiplib/client/weather_client.hpp"
#include "wiplib/client/location_client.hpp"
#include "wiplib/client/query_client.hpp"

namespace wiplib::client {

// 既存型のエイリアスでPython名に合わせる
using ServerConfig = ::wiplib::client::ServerConfig;
using ClientState = ::wiplib::client::ClientState;
using WeatherOptions = ::wiplib::client::WeatherOptions;
using WeatherData = ::wiplib::client::WeatherData;

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

  // RAII サポート（Python with相当）
  Client& operator()() { return *this; } // __enter__ equivalent
  void release() { close(); } // __exit__ equivalent

private:
  ServerConfig config_;
  ClientState state_;
  bool debug_;
    
  // 内部クライアント（WipClientを使用）
  std::unique_ptr<WipClient> wip_client_;
    
  // ヘルパーメソッド
  WeatherOptions build_options(bool weather, bool temperature, bool precipitation_prob, 
                              bool alert, bool disaster, uint8_t day) const;
  void validate_port() const;
  void initialize_wip_client();
};

} // namespace wiplib::client

