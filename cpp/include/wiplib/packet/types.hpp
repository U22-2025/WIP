#pragma once

#include <cstdint>

namespace wiplib::proto {

enum class PacketType : uint8_t {
  CoordinateRequest = 0,
  CoordinateResponse = 1,
  WeatherRequest = 2,
  WeatherResponse = 3,
  ReportRequest = 4,        // IoT機器からのセンサーデータレポート
  ReportResponse = 5,       // レポートに対するACK応答
  QueryRequest = 6,         // 直接クエリ要求
  ErrorResponse = 7,        // エラー応答
};

struct Flags {
  bool weather = false;
  bool temperature = false;
  bool precipitation = false;     // Python版に合わせて precipitation_prob -> precipitation
  bool alert = false;             // Python版に合わせて alerts -> alert
  bool disaster = false;
  bool extended = false;
  bool auth_enabled = false;      // Python版に合わせて統一
  bool response_auth = false;

  uint8_t to_byte() const noexcept {
    return (static_cast<uint8_t>(weather) << 7)
         | (static_cast<uint8_t>(temperature) << 6)
         | (static_cast<uint8_t>(precipitation) << 5)
         | (static_cast<uint8_t>(alert) << 4)
         | (static_cast<uint8_t>(disaster) << 3)
         | (static_cast<uint8_t>(extended) << 2)
         | (static_cast<uint8_t>(auth_enabled) << 1)
         | (static_cast<uint8_t>(response_auth) << 0);
  }

  static Flags from_byte(uint8_t b) noexcept {
    Flags f{};
    f.weather = (b >> 7) & 1u;
    f.temperature = (b >> 6) & 1u;
    f.precipitation = (b >> 5) & 1u;
    f.alert = (b >> 4) & 1u;
    f.disaster = (b >> 3) & 1u;
    f.extended = (b >> 2) & 1u;
    f.auth_enabled = (b >> 1) & 1u;
    f.response_auth = (b >> 0) & 1u;
    return f;
  }
};

} // namespace wiplib::proto
