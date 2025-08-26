#pragma once

#include <span>
#include <vector>
#include <cstdint>

#include "wiplib/error.hpp"
#include "wiplib/expected.hpp"
#include "wiplib/packet/packet.hpp"

namespace wiplib::proto {

// 16バイト固定ヘッダのエンコード/デコード
wiplib::Result<HeaderBytes> encode_header(const Header& h) noexcept;
wiplib::Result<Header> decode_header(std::span<const std::uint8_t> bytes) noexcept;

// パケット全体（レスポンス/拡張フィールド対応）
wiplib::Result<std::vector<std::uint8_t>> encode_packet(const Packet& p) noexcept;
wiplib::Result<Packet> decode_packet(std::span<const std::uint8_t> bytes) noexcept;

} // namespace wiplib::proto
