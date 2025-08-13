#pragma once

#include <string>
#include <string_view>
#include <cstdint>

#include "wiplib/expected.hpp"
#include "wiplib/error.hpp"

namespace wiplib::client {

class LocationClient {
public:
  LocationClient(std::string host = "127.0.0.1", uint16_t port = 4109)
    : host_(std::move(host)), port_(port) {}

  // 座標→エリアコード（6桁文字列）
  wiplib::Result<std::string> get_area_code_simple(double latitude, double longitude) noexcept;

  // 設定変更
  void set_server(std::string host, uint16_t port) { host_ = std::move(host); port_ = port; }

private:
  std::string host_;
  uint16_t port_;
};

} // namespace wiplib::client

