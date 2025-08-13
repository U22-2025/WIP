#pragma once

#include <string>
#include <string_view>
#include <cstdint>
#include <optional>

#include "wiplib/expected.hpp"
#include "wiplib/error.hpp"
#include "wiplib/client/weather_client.hpp" // reuse QueryOptions and WeatherResult

namespace wiplib::client {

class QueryClient {
public:
  QueryClient(std::string host = "127.0.0.1", uint16_t port = 4111)
    : host_(std::move(host)), port_(port) {}

  wiplib::Result<WeatherResult> get_weather_data(std::string_view area_code,
                                                 const QueryOptions& opt) noexcept;

  void set_server(std::string host, uint16_t port) { host_ = std::move(host); port_ = port; }

private:
  std::string host_;
  uint16_t port_;
};

} // namespace wiplib::client

