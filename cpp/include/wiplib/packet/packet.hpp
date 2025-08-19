#pragma once

#include <cstdint>
#include <array>
#include <string>
#include <vector>
#include <optional>

#include "wiplib/packet/types.hpp"

namespace wiplib::proto {

// 基本ヘッダー 128-bit（16バイト）
struct Header {
  uint8_t  version = 1;        // 4 bits
  uint16_t packet_id = 0;      // 12 bits
  PacketType type = PacketType::WeatherRequest; // 3 bits
  Flags flags{};               // 8 bits
  uint8_t day = 0;             // 3 bits
  uint64_t timestamp = 0;      // 64 bits (UNIX time)
  uint32_t area_code = 0;      // 20 bits
  uint16_t checksum = 0;       // 12 bits
  uint8_t reserved = 0;        // 2 bits (内部的に保持)
};

// レスポンス専用フィールド（必要に応じて利用）
struct ResponseFields {
  uint16_t weather_code = 0; // 16 bits
  int8_t temperature = 0;    // 8 bits (2の補数, +100オフセットは上位で扱う)
  uint8_t precipitation_prob = 0; // 8 bits
};

// 拡張フィールド（可変長）
struct ExtendedField {
  uint8_t data_type = 0; // 6bit想定（0-63）。実際は下位6bit。
  std::vector<std::uint8_t> data; // 値データ（little-endian表現のバイト列を想定）
};

struct Packet {
  Header header{};
  std::optional<ResponseFields> response_fields{}; // タイプがレスポンス時
  std::vector<ExtendedField> extensions{};
};

constexpr size_t kFixedHeaderSize = 16u;
using HeaderBytes = std::array<std::uint8_t, kFixedHeaderSize>;

} // namespace wiplib::proto
