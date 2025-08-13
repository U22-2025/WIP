#pragma once

#include <optional>
#include <string>
#include <string_view>

#include "wiplib/client/wip_client.hpp"

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

// Pythonの WIPClientPy.client.Client に対応する薄いラッパ
class Client {
public:
  explicit Client(ServerConfig cfg = {}, bool debug = false)
    : cfg_(cfg), core_(cfg, debug) {}

  // 状態操作
  void set_coordinates(double lat, double lon) { core_.set_coordinates(lat, lon); }
  void set_area_code(std::string area) { core_.set_area_code(std::move(area)); }
  const ClientState& state() const noexcept { return core_.state(); }

  // サーバ設定（Pythonと同名）
  void set_server(const std::string& host) { cfg_.host = host; core_.update_server(cfg_.host, cfg_.port); }
  void set_server(const std::string& host, uint16_t port) { cfg_.host = host; cfg_.port = port; core_.update_server(cfg_.host, cfg_.port); }

  // 互換API
  void close() { core_.close(); }

  // スナップショット
  ClientSnapshot get_state() const noexcept {
    ClientSnapshot s{};
    const auto& st = core_.state();
    s.latitude = st.latitude; s.longitude = st.longitude; s.area_code = st.area_code;
    s.host = cfg_.host; s.port = cfg_.port;
    return s;
  }

  // 高水準API（Python関数名と引数順に揃えたオーバーロード）
  Result<WeatherData> get_weather(const WeatherOptions& opt, bool proxy = false) noexcept {
    return core_.get_weather(opt, proxy);
  }
  Result<WeatherData> get_weather(
      bool weather = true,
      bool temperature = true,
      bool precipitation_prob = true,
      bool alert = false,
      bool disaster = false,
      uint8_t day = 0,
      bool proxy = false) noexcept {
    WeatherOptions o{}; o.weather=weather; o.temperature=temperature; o.precipitation_prob=precipitation_prob; o.alert=alert; o.disaster=disaster; o.day=day;
    return core_.get_weather(o, proxy);
  }

  Result<WeatherData> get_weather_by_coordinates(double lat, double lon, const WeatherOptions& opt, bool proxy = false) noexcept {
    return core_.get_weather_by_coordinates(lat, lon, opt, proxy);
  }
  Result<WeatherData> get_weather_by_coordinates(
      double lat, double lon,
      bool weather, bool temperature, bool precipitation_prob,
      bool alert, bool disaster, uint8_t day,
      bool proxy = false) noexcept {
    WeatherOptions o{}; o.weather=weather; o.temperature=temperature; o.precipitation_prob=precipitation_prob; o.alert=alert; o.disaster=disaster; o.day=day;
    return core_.get_weather_by_coordinates(lat, lon, o, proxy);
  }

  Result<WeatherData> get_weather_by_area_code(std::string_view area_code, const WeatherOptions& opt, bool proxy = false) noexcept {
    return core_.get_weather_by_area_code(area_code, opt, proxy);
  }
  Result<WeatherData> get_weather_by_area_code(
      std::string_view area_code,
      bool weather, bool temperature, bool precipitation_prob,
      bool alert, bool disaster, uint8_t day,
      bool proxy = false) noexcept {
    WeatherOptions o{}; o.weather=weather; o.temperature=temperature; o.precipitation_prob=precipitation_prob; o.alert=alert; o.disaster=disaster; o.day=day;
    return core_.get_weather_by_area_code(area_code, o, proxy);
  }

private:
  ServerConfig cfg_{}; // ラッパ側で保持
  ::wiplib::client::WipClient core_;
};

} // namespace wiplib::client

