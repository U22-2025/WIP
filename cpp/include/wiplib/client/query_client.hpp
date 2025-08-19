#pragma once

#include <string>
#include <string_view>
#include <cstdint>
#include <optional>

#include "wiplib/expected.hpp"
#include "wiplib/error.hpp"
#include "wiplib/client/weather_client.hpp" // reuse QueryOptions and WeatherResult
#include "wiplib/client/auth_config.hpp"

namespace wiplib::client {

class QueryClient {
public:
  QueryClient(std::string host = default_host(), uint16_t port = default_port(),
              bool debug = false)
    : host_(std::move(host)), port_(port), debug_(debug) {}

  static QueryClient from_env(bool debug = false);
  static std::string default_host();
  static uint16_t default_port();

  wiplib::Result<WeatherResult> get_weather_data(std::string_view area_code,
                                                 const QueryOptions& opt) noexcept;

  void set_server(std::string host, uint16_t port) { host_ = std::move(host); port_ = port; }

  void set_auth_config(const AuthConfig& cfg) { auth_cfg_ = cfg; }

private:
  std::string host_;
  uint16_t port_;
  bool debug_ = false;
  AuthConfig auth_cfg_{};
};

} // namespace wiplib::client
