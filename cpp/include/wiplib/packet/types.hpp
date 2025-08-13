#pragma once

#include <cstdint>

namespace wiplib::proto {

enum class PacketType : uint8_t {
  CoordinateRequest = 0,
  CoordinateResponse = 1,
  WeatherRequest = 2,
  WeatherResponse = 3,
};

struct Flags {
  bool weather = false;
  bool temperature = false;
  bool precipitation_prob = false;
  bool alerts = false;
  bool disaster = false;
  bool extended = false;
  bool request_auth = false;  // RA
  bool response_auth = false; // RS

  uint8_t to_byte() const noexcept {
    return (static_cast<uint8_t>(weather) << 7)
         | (static_cast<uint8_t>(temperature) << 6)
         | (static_cast<uint8_t>(precipitation_prob) << 5)
         | (static_cast<uint8_t>(alerts) << 4)
         | (static_cast<uint8_t>(disaster) << 3)
         | (static_cast<uint8_t>(extended) << 2)
         | (static_cast<uint8_t>(request_auth) << 1)
         | (static_cast<uint8_t>(response_auth) << 0);
  }

  static Flags from_byte(uint8_t b) noexcept {
    Flags f{};
    f.weather = (b >> 7) & 1u;
    f.temperature = (b >> 6) & 1u;
    f.precipitation_prob = (b >> 5) & 1u;
    f.alerts = (b >> 4) & 1u;
    f.disaster = (b >> 3) & 1u;
    f.extended = (b >> 2) & 1u;
    f.request_auth = (b >> 1) & 1u;
    f.response_auth = (b >> 0) & 1u;
    return f;
  }
};

} // namespace wiplib::proto
