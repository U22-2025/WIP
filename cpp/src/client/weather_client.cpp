#include "wiplib/client/weather_client.hpp"

#include "wiplib/packet/codec.hpp"
#include <chrono>
#include <random>
#include <cstring>
#include <cstdio>

#if defined(_WIN32)
#  include <winsock2.h>
#  include <ws2tcpip.h>
#  pragma comment(lib, "Ws2_32.lib")
using socklen_t = int;
#else
#  include <sys/types.h>
#  include <sys/socket.h>
#  include <arpa/inet.h>
#  include <netdb.h>
#  include <unistd.h>
#endif

namespace wiplib::client {

wiplib::Result<WeatherResult> WeatherClient::get_weather_by_coordinates(double lat, double lon, const QueryOptions& opt) noexcept {
  using namespace wiplib::proto;
  Packet p{};
  p.header.version = 1;
  // packet_id: ランダム12bit
  std::mt19937 rng{std::random_device{}()};
  p.header.packet_id = static_cast<uint16_t>(rng() & 0x0FFFu);
  p.header.type = PacketType::WeatherRequest;
  p.header.flags.weather = opt.weather;
  p.header.flags.temperature = opt.temperature;
  p.header.flags.precipitation_prob = opt.precipitation_prob;
  p.header.flags.alerts = opt.alerts;
  p.header.flags.disaster = opt.disaster;
  p.header.day = opt.day;
  p.header.timestamp = static_cast<uint64_t>(std::chrono::duration_cast<std::chrono::seconds>(
      std::chrono::system_clock::now().time_since_epoch()).count());
  p.header.area_code = 0; // 座標ベース要求では 0 を設定

  // 拡張: 緯度/経度（各 4 バイトの int32 LE, 倍率 1e6）
  auto push_coord_le = [](double d) {
    std::vector<std::uint8_t> v(4);
    const long long scaled = static_cast<long long>(d * 1000000.0);
    const int32_t i = static_cast<int32_t>(scaled);
    v[0] = static_cast<uint8_t>(i & 0xFF);
    v[1] = static_cast<uint8_t>((i >> 8) & 0xFF);
    v[2] = static_cast<uint8_t>((i >> 16) & 0xFF);
    v[3] = static_cast<uint8_t>((i >> 24) & 0xFF);
    return v;
  };
  ExtendedField latf; latf.data_type = 33; latf.data = push_coord_le(lat);
  ExtendedField lonf; lonf.data_type = 34; lonf.data = push_coord_le(lon);
  p.extensions.push_back(std::move(latf));
  p.extensions.push_back(std::move(lonf));
  p.header.flags.extended = true;

  return request_and_parse(p);
}

wiplib::Result<WeatherResult> WeatherClient::get_weather_by_area_code(std::string_view area_code, const QueryOptions& opt) noexcept {
  using namespace wiplib::proto;
  Packet p{};
  p.header.version = 1;
  std::mt19937 rng{std::random_device{}()};
  p.header.packet_id = static_cast<uint16_t>(rng() & 0x0FFFu);
  p.header.type = PacketType::WeatherRequest;
  p.header.flags.weather = opt.weather;
  p.header.flags.temperature = opt.temperature;
  p.header.flags.precipitation_prob = opt.precipitation_prob;
  p.header.flags.alerts = opt.alerts;
  p.header.flags.disaster = opt.disaster;
  p.header.day = opt.day;
  p.header.timestamp = static_cast<uint64_t>(std::chrono::duration_cast<std::chrono::seconds>(
      std::chrono::system_clock::now().time_since_epoch()).count());
  // area_code is 6 digits string; we accept decimal and clamp to 20-bit
  uint32_t ac = 0;
  for (char c : area_code) {
    if (c < '0' || c > '9') continue;
    ac = ac * 10u + static_cast<uint32_t>(c - '0');
  }
  p.header.area_code = ac & 0xFFFFFu;

  return request_and_parse(p);
}

wiplib::Result<WeatherResult> WeatherClient::request_and_parse(const wiplib::proto::Packet& req) noexcept {
  using namespace wiplib::proto;
  auto enc = encode_packet(req);
  if (!enc) return enc.error();
  const auto& payload = enc.value();

  // Optional debug: show destination and payload details before sending
  if (std::getenv("WIPLIB_DEBUG_LOG")) {
    fprintf(stderr, "[wiplib] dest %s:%u, payload %zu bytes\n", host_.c_str(), static_cast<unsigned>(port_), payload.size());
    size_t dump = payload.size() < 32 ? payload.size() : 32;
    fprintf(stderr, "[wiplib] tx: ");
    for (size_t i = 0; i < dump; ++i) fprintf(stderr, "%02X ", payload[i]);
    fprintf(stderr, "\n");
    // Show interpreted packet_id from first 16 header bytes in both bit-orders
    if (payload.size() >= kFixedHeaderSize) {
      auto get_bits_le_dbg = [&](size_t start, size_t length)->uint32_t {
        uint32_t val = 0; for (size_t i=0;i<length;++i){ size_t bitpos=start+i; size_t byte_index=bitpos/8; size_t bit_index=bitpos%8; uint8_t bit=(payload[byte_index]>>bit_index)&0x1u; val |= (bit<<i);} return val;
      };
      auto get_bits_msb_dbg = [&](size_t start, size_t length)->uint32_t {
        uint32_t val = 0; for (size_t i=0;i<length;++i){ size_t bitpos=start+i; size_t byte_index=bitpos/8; size_t bit_index=bitpos%8; uint8_t bit=(payload[byte_index]>>(7-bit_index))&0x1u; val |= (bit<<i);} return val;
      };
      uint32_t pid_le = get_bits_le_dbg(4, 12);
      uint32_t pid_msb = get_bits_msb_dbg(4, 12);
      fprintf(stderr, "[wiplib] tx pid_le=%u pid_msb=%u (req=%u)\n", pid_le, pid_msb, static_cast<unsigned>(req.header.packet_id));
    }
  }

#if defined(_WIN32)
  WSADATA wsaData;
  if (WSAStartup(MAKEWORD(2, 2), &wsaData) != 0) {
    return make_error_code(WipErrc::io_error);
  }
#endif

  WeatherResult result{};
  int sock = -1;
  do {
#if defined(_WIN32)
    sock = static_cast<int>(::socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP));
    if (sock == INVALID_SOCKET) { result = {}; break; }
#else
    sock = ::socket(AF_INET, SOCK_DGRAM, 0);
    if (sock < 0) { return make_error_code(WipErrc::io_error); }
#endif

    // 短い受信タイムアウトを設定（500ms）し、全体で最大10秒待つ
#if defined(_WIN32)
    DWORD tv = 500;
    setsockopt(sock, SOL_SOCKET, SO_RCVTIMEO, reinterpret_cast<const char*>(&tv), sizeof(tv));
#else
    struct timeval tv; tv.tv_sec = 0; tv.tv_usec = 500000;
    setsockopt(sock, SOL_SOCKET, SO_RCVTIMEO, &tv, sizeof(tv));
#endif

    sockaddr_in addr{}; addr.sin_family = AF_INET; addr.sin_port = htons(port_);
    if (::inet_pton(AF_INET, host_.c_str(), &addr.sin_addr) != 1) {
      // 名前解決（IPv4）
      struct addrinfo hints{}; hints.ai_family = AF_INET; hints.ai_socktype = SOCK_DGRAM;
      struct addrinfo* res = nullptr;
      if (getaddrinfo(host_.c_str(), nullptr, &hints, &res) != 0 || res == nullptr) {
#if defined(_WIN32)
        closesocket(sock);
        WSACleanup();
#else
        close(sock);
#endif
        return make_error_code(WipErrc::io_error);
      }
      auto* a = reinterpret_cast<sockaddr_in*>(res->ai_addr);
      addr.sin_addr = a->sin_addr;
      freeaddrinfo(res);
    }

    int sret = ::sendto(sock, reinterpret_cast<const char*>(payload.data()), static_cast<int>(payload.size()), 0,
                 reinterpret_cast<sockaddr*>(&addr), sizeof(addr));
    if (std::getenv("WIPLIB_DEBUG_LOG")) {
#if defined(_WIN32)
      if (sret < 0) { fprintf(stderr, "[wiplib] sendto failed, WSA errno=%d\n", WSAGetLastError()); }
      else { fprintf(stderr, "[wiplib] sendto ok (%d bytes)\n", sret); }
#else
      if (sret < 0) { fprintf(stderr, "[wiplib] sendto failed, errno=%d (%s)\n", errno, strerror(errno)); }
      else { fprintf(stderr, "[wiplib] sendto ok (%d bytes)\n", sret); }
#endif
    }
    if (sret < 0) {
#if defined(_WIN32)
      closesocket(sock); WSACleanup();
#else
      close(sock);
#endif
      return make_error_code(WipErrc::io_error);
    }

    const auto deadline = std::chrono::steady_clock::now() + std::chrono::seconds(10);
    if (std::getenv("WIPLIB_DEBUG_LOG")) {
      fprintf(stderr, "[wiplib] waiting for response up to 10s...\n");
    }
  for (;;) {
      std::uint8_t buf[2048];
      sockaddr_in from{}; socklen_t fromlen = sizeof(from);
      int rlen = static_cast<int>(::recvfrom(sock, reinterpret_cast<char*>(buf), sizeof(buf), 0,
                                   reinterpret_cast<sockaddr*>(&from), &fromlen));
      if (rlen > 0) {
        // Optional debug: dump first 16 bytes and dual PID interpretations
        if (std::getenv("WIPLIB_DEBUG_LOG")) {
          char addrstr[64] = {0};
#if defined(_WIN32)
          ::InetNtopA(AF_INET, &from.sin_addr, addrstr, sizeof(addrstr));
#else
          ::inet_ntop(AF_INET, &from.sin_addr, addrstr, sizeof(addrstr));
#endif
          fprintf(stderr, "[wiplib] recv %dB from %s:%u\n", rlen, addrstr, ntohs(from.sin_port));
          size_t dump = static_cast<size_t>(rlen < 16 ? rlen : 16);
          fprintf(stderr, "[wiplib] hdr: ");
          for (size_t i = 0; i < dump; ++i) fprintf(stderr, "%02X ", buf[i]);
          fprintf(stderr, "\n");
          auto get_bits_le_dbg = [&](size_t start, size_t length)->uint32_t {
            uint32_t val = 0; for (size_t i=0;i<length;++i){ size_t bitpos=start+i; size_t byte_index=bitpos/8; size_t bit_index=bitpos%8; uint8_t bit=(buf[byte_index]>>bit_index)&0x1u; val |= (bit<<i);} return val;
          };
          auto get_bits_msb_dbg = [&](size_t start, size_t length)->uint32_t {
            uint32_t val = 0; for (size_t i=0;i<length;++i){ size_t bitpos=start+i; size_t byte_index=bitpos/8; size_t bit_index=bitpos%8; uint8_t bit=(buf[byte_index]>>(7-bit_index))&0x1u; val |= (bit<<i);} return val;
          };
          uint32_t pid_le = get_bits_le_dbg(4, 12);
          uint32_t pid_msb = get_bits_msb_dbg(4, 12);
          fprintf(stderr, "[wiplib] pid_le=%u pid_msb=%u (req=%u)\n", pid_le, pid_msb, static_cast<unsigned>(req.header.packet_id));
        }
        if (rlen >= static_cast<int>(kFixedHeaderSize)) {
          // ヘッダ先頭から packet_id を軽量解析（LE, version4bitの後の12bit）
          auto get_bits_le = [&](size_t start, size_t length)->uint32_t {
            uint32_t val = 0; for (size_t i=0;i<length;++i){ size_t bitpos=start+i; size_t byte_index=bitpos/8; size_t bit_index=bitpos%8; uint8_t bit=(buf[byte_index]>>bit_index)&0x1u; val |= (bit<<i);} return val;
          };
          uint16_t pid = static_cast<uint16_t>(get_bits_le(4, 12));
          if (pid == req.header.packet_id) {
            auto dec = decode_packet(std::span<const std::uint8_t>(buf, static_cast<size_t>(rlen)));
            if (!dec) {
              // マッチしたが破損
              break;
            }
            const Packet& rp = dec.value();
            result.area_code = rp.header.area_code;
            if (rp.response_fields.has_value()) {
              result.weather_code = rp.response_fields->weather_code;
              result.temperature = rp.response_fields->temperature;
              result.precipitation_prob = rp.response_fields->precipitation_prob;
            }
            // クローズして返す
#if defined(_WIN32)
            closesocket(sock); WSACleanup();
#else
            close(sock);
#endif
            return result;
          }
        }
        // packet_id不一致 → 続行
      }
      if (std::chrono::steady_clock::now() >= deadline) {
        if (std::getenv("WIPLIB_DEBUG_LOG")) {
          fprintf(stderr, "[wiplib] timeout: no matching response within 10s\n");
        }
        break;
      }
      // ループ継続（SO_RCVTIMEOにより適度に戻る）
    }

#if defined(_WIN32)
    closesocket(sock); WSACleanup();
#else
    close(sock);
#endif
    return make_error_code(WipErrc::timeout);
  } while(false);

  return make_error_code(WipErrc::io_error);
}

} // namespace wiplib::client
