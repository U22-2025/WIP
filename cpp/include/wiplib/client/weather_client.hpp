#pragma once

#include <string>
#include <cstdint>
#include <optional>
#include <vector>

#include "wiplib/expected.hpp"
#include "wiplib/error.hpp"
#include "wiplib/packet/packet.hpp"
#include "wiplib/client/auth_config.hpp"

namespace wiplib::client {

struct QueryOptions {
  bool weather = true;
  bool temperature = true;
  bool precipitation_prob = true;
  bool alerts = false;
  bool disaster = false;
  uint8_t day = 0;
};

struct WeatherResult {
  uint32_t area_code = 0;
  std::optional<uint16_t> weather_code{};
  std::optional<int8_t> temperature{};
  std::optional<uint8_t> precipitation_prob{};
  std::optional<std::vector<std::string>> alerts{};
  std::optional<std::vector<std::string>> disasters{};
};

class WeatherClient {
public:
  WeatherClient(std::string host = default_host(),
                uint16_t port = default_port())
      : host_(std::move(host)), port_(port) {}
  ~WeatherClient() = default;

  static WeatherClient from_env();
  static std::string default_host();
  static uint16_t default_port();

  // Python版に合わせた命名
  wiplib::Result<WeatherResult> get_weather_by_coordinates(double lat, double lon, const QueryOptions& opt) noexcept;
  wiplib::Result<WeatherResult> get_weather_by_area_code(std::string_view area_code, const QueryOptions& opt) noexcept;

  void set_auth_config(const AuthConfig& cfg) { auth_cfg_ = cfg; }

private:
  std::string host_;
  uint16_t port_ = 4110;
  AuthConfig auth_cfg_{};
  wiplib::Result<WeatherResult> request_and_parse(const wiplib::proto::Packet& req) noexcept;
};

} // namespace wiplib::client
