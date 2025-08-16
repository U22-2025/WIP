#include "wiplib/packet/codec.hpp"

#include <array>
#include <cstring>
#include <limits>

namespace wiplib::proto {

static uint16_t compute_checksum12_le(std::array<std::uint8_t, 16> bytes_le) noexcept {
  // チェックサムビット(116-127)を0にした状態で12ビット1の補数和（キャリーフォールド）
  auto clear_bit = [&](size_t bitpos){ bytes_le[bitpos/8] &= static_cast<uint8_t>(~(1u << (bitpos%8))); };
  for (size_t i = 116; i < 128; ++i) clear_bit(i);
  uint32_t total = 0;
  for (auto b : bytes_le) total += static_cast<uint32_t>(b);
  while (total >> 12) {
    total = (total & 0x0FFFu) + (total >> 12);
  }
  return static_cast<uint16_t>((~total) & 0x0FFFu);
}

static inline void set_bits_le(std::array<std::uint8_t, 16>& out, size_t start, size_t length, uint64_t value) noexcept {
  for (size_t i = 0; i < length; ++i) {
    size_t bitpos = start + i;
    size_t byte_index = bitpos / 8;
    size_t bit_index = bitpos % 8; // LSB-first within byte
    uint8_t bit = static_cast<uint8_t>((value >> i) & 0x1u);
    if (bit) out[byte_index] |= static_cast<uint8_t>(1u << bit_index);
    else out[byte_index] &= static_cast<uint8_t>(~(1u << bit_index));
  }
}

static inline uint64_t get_bits_le(std::span<const std::uint8_t> in, size_t start, size_t length) noexcept {
  uint64_t value = 0;
  for (size_t i = 0; i < length; ++i) {
    size_t bitpos = start + i;
    size_t byte_index = bitpos / 8;
    size_t bit_index = bitpos % 8;
    uint8_t bit = (in[byte_index] >> bit_index) & 0x1u;
    value |= (static_cast<uint64_t>(bit) << i);
  }
  return value;
}

static inline void set_bits_le_vec(std::vector<std::uint8_t>& out, size_t start, size_t length, uint64_t value) noexcept {
  for (size_t i = 0; i < length; ++i) {
    size_t bitpos = start + i;
    size_t byte_index = bitpos / 8;
    size_t bit_index = bitpos % 8; // LSB-first
    uint8_t bit = static_cast<uint8_t>((value >> i) & 0x1u);
    if (bit) out[byte_index] |= static_cast<uint8_t>(1u << bit_index);
    else out[byte_index] &= static_cast<uint8_t>(~(1u << bit_index));
  }
}

static uint16_t compute_checksum12_over_packet(std::span<const std::uint8_t> bytes) noexcept {
  if (bytes.size() < kFixedHeaderSize) return 0;
  std::vector<std::uint8_t> copy(bytes.begin(), bytes.end());
  // clear checksum bits 116..127 (12 bits) in-place (LSB-first within byte)
  for (size_t i = 116; i < 128; ++i) {
    size_t byte_index = i / 8;
    size_t bit_index = i % 8;
    copy[byte_index] &= static_cast<uint8_t>(~(1u << bit_index));
  }
  uint32_t total = 0;
  for (auto b : copy) total += static_cast<uint32_t>(b);
  while (total >> 12) {
    total = (total & 0x0FFFu) + (total >> 12);
  }
  return static_cast<uint16_t>((~total) & 0x0FFFu);
}

wiplib::Result<HeaderBytes> encode_header(const Header& h) noexcept {
  HeaderBytes out{};
  // 基本ヘッダ 128bit を little-endian ビット配置で構築
  // フィールド位置（bit）: FormatBase の順序に一致
  size_t pos = 0;
  set_bits_le(out, pos, 4, h.version & 0x0Fu); pos += 4;
  set_bits_le(out, pos, 12, h.packet_id & 0x0FFFu); pos += 12;
  set_bits_le(out, pos, 3, static_cast<uint8_t>(h.type) & 0x7u); pos += 3;
  set_bits_le(out, pos++, 1, h.flags.weather ? 1 : 0);
  set_bits_le(out, pos++, 1, h.flags.temperature ? 1 : 0);
  set_bits_le(out, pos++, 1, h.flags.precipitation_prob ? 1 : 0);
  set_bits_le(out, pos++, 1, h.flags.alerts ? 1 : 0);
  set_bits_le(out, pos++, 1, h.flags.disaster ? 1 : 0);
  set_bits_le(out, pos++, 1, h.flags.extended ? 1 : 0);
  set_bits_le(out, pos++, 1, h.flags.request_auth ? 1 : 0);
  set_bits_le(out, pos++, 1, h.flags.response_auth ? 1 : 0);
  set_bits_le(out, pos, 3, h.day & 0x7u); pos += 3;
  set_bits_le(out, pos, 2, h.reserved & 0x3u); pos += 2;
  set_bits_le(out, pos, 64, h.timestamp); pos += 64;
  set_bits_le(out, pos, 20, h.area_code & 0xFFFFFu); pos += 20;
  // checksum は一旦 0 のままにして計算後設定
  // 計算
  uint16_t cs = compute_checksum12_le(out);
  set_bits_le(out, pos, 12, cs); pos += 12;
  (void)pos; // silence unused in release
  return out;
}

wiplib::Result<Header> decode_header(std::span<const std::uint8_t> bytes) noexcept {
  if (bytes.size() < kFixedHeaderSize) {
    return make_error_code(WipErrc::invalid_packet);
  }
  Header h{};
  // チェックサム検証（パケット全体を対象）
  uint16_t stored = static_cast<uint16_t>(get_bits_le(bytes, 116, 12));
  uint16_t calc = compute_checksum12_over_packet(bytes);
  if (calc != stored) {
    return make_error_code(WipErrc::checksum_mismatch);
  }

  size_t pos = 0;
  h.version = static_cast<uint8_t>(get_bits_le(bytes, pos, 4)); pos += 4;
  h.packet_id = static_cast<uint16_t>(get_bits_le(bytes, pos, 12)); pos += 12;
  h.type = static_cast<PacketType>(get_bits_le(bytes, pos, 3)); pos += 3;
  h.flags.weather = get_bits_le(bytes, pos++, 1);
  h.flags.temperature = get_bits_le(bytes, pos++, 1);
  h.flags.precipitation_prob = get_bits_le(bytes, pos++, 1);
  h.flags.alerts = get_bits_le(bytes, pos++, 1);
  h.flags.disaster = get_bits_le(bytes, pos++, 1);
  h.flags.extended = get_bits_le(bytes, pos++, 1);
  h.flags.request_auth = get_bits_le(bytes, pos++, 1);
  h.flags.response_auth = get_bits_le(bytes, pos++, 1);
  h.day = static_cast<uint8_t>(get_bits_le(bytes, pos, 3)); pos += 3;
  h.reserved = static_cast<uint8_t>(get_bits_le(bytes, pos, 2)); pos += 2;
  h.timestamp = get_bits_le(bytes, pos, 64); pos += 64;
  h.area_code = static_cast<uint32_t>(get_bits_le(bytes, pos, 20)); pos += 20;
  h.checksum = static_cast<uint16_t>(get_bits_le(bytes, pos, 12)); pos += 12;
  (void)pos;
  return h;
}

wiplib::Result<std::vector<std::uint8_t>> encode_packet(const Packet& p) noexcept {
  auto hbytes_res = encode_header(p.header);
  if (!hbytes_res) return hbytes_res.error();
  std::vector<std::uint8_t> out;
  out.reserve(kFixedHeaderSize + 64);
  const auto& hb = hbytes_res.value();
  out.insert(out.end(), hb.begin(), hb.end());

  // レスポンスフィールド（クライアント送信では通常含めない）
  if (p.response_fields.has_value()) {
    const auto& rf = p.response_fields.value();
    // little-endian: 下位バイトから格納
    out.push_back(static_cast<uint8_t>(rf.weather_code & 0xFF));
    out.push_back(static_cast<uint8_t>((rf.weather_code >> 8) & 0xFF));
    out.push_back(static_cast<uint8_t>(static_cast<uint8_t>(rf.temperature)));
    out.push_back(static_cast<uint8_t>(rf.precipitation_prob));
  }

  // 拡張フィールド（ヘッダーは 2B LE, 値バイト列）
  for (const auto& ext : p.extensions) {
    if (ext.data.size() > 0x3FFu) { // 10-bit length 上限
      return make_error_code(WipErrc::invalid_packet);
    }
    uint16_t header = static_cast<uint16_t>(((static_cast<uint16_t>(ext.data_type) & 0x3Fu) << 10)
                      | (static_cast<uint16_t>(ext.data.size()) & 0x3FFu));
    // little-endian header
    out.push_back(static_cast<uint8_t>(header & 0xFF));
    out.push_back(static_cast<uint8_t>((header >> 8) & 0xFF));
    // 値は little-endian で格納されている前提
    out.insert(out.end(), ext.data.begin(), ext.data.end());
  }

  // パケット全体でチェックサムを再計算し、ヘッダーに反映
  uint16_t cs = compute_checksum12_over_packet(out);
  set_bits_le_vec(out, 116, 12, cs);
  return out;
}

wiplib::Result<Packet> decode_packet(std::span<const std::uint8_t> bytes) noexcept {
  auto h_res = decode_header(bytes);
  if (!h_res) return h_res.error();
  Packet p{};
  p.header = h_res.value();
  size_t offset = kFixedHeaderSize;
  const size_t n = bytes.size();

  // レスポンスフィールド（4バイト分存在すれば読む）
  if (n >= offset + 4 && (p.header.type == PacketType::WeatherResponse || p.header.type == PacketType::CoordinateResponse)) {
    ResponseFields rf{};
    // little-endian 16bit + int8 + uint8
    rf.weather_code = static_cast<uint16_t>(bytes[offset] | (bytes[offset + 1] << 8));
    rf.temperature = static_cast<int8_t>(bytes[offset + 2]);
    rf.precipitation_prob = static_cast<uint8_t>(bytes[offset + 3]);
    p.response_fields = rf;
    offset += 4;
  }

  // 拡張フィールド
  while (n >= offset + 2) {
    uint16_t hdr = static_cast<uint16_t>(bytes[offset] | (bytes[offset + 1] << 8));
    offset += 2;
    uint16_t len = static_cast<uint16_t>(hdr & 0x03FFu);
    uint8_t dtype = static_cast<uint8_t>((hdr >> 10) & 0x3Fu);
    if (n < offset + len) { // 破損
      return make_error_code(WipErrc::invalid_packet);
    }
    ExtendedField ext{};
    ext.data_type = dtype;
    ext.data.assign(bytes.begin() + static_cast<std::ptrdiff_t>(offset), bytes.begin() + static_cast<std::ptrdiff_t>(offset + len));
    p.extensions.push_back(std::move(ext));
    offset += len;
  }

  return p;
}

} // namespace wiplib::proto
