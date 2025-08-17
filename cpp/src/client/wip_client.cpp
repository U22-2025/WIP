#include "wiplib/client/wip_client.hpp"

#include "wiplib/packet/codec.hpp"
#include "wiplib/client/location_client.hpp"
#include "wiplib/client/query_client.hpp"
#include <chrono>
#include <cstring>
#include <random>
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

using namespace wiplib::proto;

static uint64_t now_sec() {
  return static_cast<uint64_t>(std::chrono::duration_cast<std::chrono::seconds>(
      std::chrono::system_clock::now().time_since_epoch()).count());
}

WipClient::WipClient(ServerConfig cfg, bool debug)
    : cfg_(std::move(cfg)), debug_(debug), proxy_client_(cfg_.host, cfg_.port) {}

WipClient::~WipClient() { close(); }

void WipClient::set_coordinates(double latitude, double longitude) {
  state_.latitude = latitude;
  state_.longitude = longitude;
}

void WipClient::set_area_code(std::string area_code) { state_.area_code = std::move(area_code); }

void WipClient::update_server(std::string host, uint16_t port) {
  cfg_.host = std::move(host);
  cfg_.port = port;
  proxy_client_ = WeatherClient(cfg_.host, cfg_.port);
}

void WipClient::set_direct_endpoints(std::string location_host, uint16_t location_port,
                            std::string query_host, uint16_t query_port) {
  location_host_ = std::move(location_host);
  location_port_ = location_port;
  query_host_ = std::move(query_host);
  query_port_ = query_port;
}

void WipClient::close() {
  // nothing persistent to close in current implementation
}

Result<WeatherData> WipClient::get_weather(const WeatherOptions& opt, bool proxy) noexcept {
  if (proxy) {
    if (state_.area_code) {
      return get_weather_by_area_code(*state_.area_code, opt, true);
    }
    if (state_.latitude && state_.longitude) {
      return get_weather_by_coordinates(*state_.latitude, *state_.longitude, opt, true);
    }
    return make_error_code(WipErrc::invalid_packet); // missing inputs
  }
  // direct mode
  if (state_.area_code) {
    return query_weather_direct(*state_.area_code, opt);
  }
  if (state_.latitude && state_.longitude) {
    auto ac = resolve_area_code_direct(*state_.latitude, *state_.longitude, opt);
    if (!ac) return ac.error();
    return query_weather_direct(ac.value(), opt);
  }
  return make_error_code(WipErrc::invalid_packet);
}

Result<WeatherData> WipClient::get_weather_by_coordinates(double lat, double lon, const WeatherOptions& opt, bool proxy) noexcept {
  if (proxy) {
    QueryOptions qo{}; qo.weather = opt.weather; qo.temperature = opt.temperature; qo.precipitation_prob = opt.precipitation_prob; qo.alerts = opt.alert; qo.disaster = opt.disaster; qo.day = opt.day;
    auto res = proxy_client_.get_weather_by_coordinates(lat, lon, qo);
    if (!res) return res.error();
    WeatherData out{}; out.area_code = std::to_string(res.value().area_code);
    if (res.value().weather_code) out.weather_code = res.value().weather_code;
    if (res.value().temperature) out.temperature_c = static_cast<int>(*res.value().temperature) - 100; // Python仕様
    if (res.value().precipitation_prob) out.precipitation_prob = static_cast<int>(*res.value().precipitation_prob);
    return out;
  }
  auto ac = resolve_area_code_direct(lat, lon, opt);
  if (!ac) return ac.error();
  return query_weather_direct(ac.value(), opt);
}

Result<WeatherData> WipClient::get_weather_by_area_code(std::string_view area_code, const WeatherOptions& opt, bool proxy) noexcept {
  if (proxy) {
    QueryOptions qo{}; qo.weather = opt.weather; qo.temperature = opt.temperature; qo.precipitation_prob = opt.precipitation_prob; qo.alerts = opt.alert; qo.disaster = opt.disaster; qo.day = opt.day;
    auto res = proxy_client_.get_weather_by_area_code(area_code, qo);
    if (!res) return res.error();
    WeatherData out{}; out.area_code = std::string(area_code);
    if (res.value().weather_code) out.weather_code = res.value().weather_code;
    if (res.value().temperature) out.temperature_c = static_cast<int>(*res.value().temperature) - 100;
    if (res.value().precipitation_prob) out.precipitation_prob = static_cast<int>(*res.value().precipitation_prob);
    return out;
  }
  return query_weather_direct(area_code, opt);
}

Result<std::string> WipClient::resolve_area_code_direct(double lat, double lon, const WeatherOptions& opt) noexcept {
  LocationClient lc(location_host_, location_port_);
  return lc.get_area_code_simple(lat, lon);
}

Result<WeatherData> WipClient::query_weather_direct(std::string_view area_code, const WeatherOptions& opt) noexcept {
  QueryClient qc(query_host_, query_port_);
  QueryOptions qo{}; qo.weather=opt.weather; qo.temperature=opt.temperature; qo.precipitation_prob=opt.precipitation_prob; qo.alerts=opt.alert; qo.disaster=opt.disaster; qo.day=opt.day;
  auto r = qc.get_weather_data(area_code, qo);
  if (!r) return r.error();
  WeatherData out{}; char buf[16]; std::snprintf(buf, sizeof(buf), "%06u", r.value().area_code); out.area_code = buf;
  if (r.value().weather_code) out.weather_code = r.value().weather_code;
  if (r.value().temperature) out.temperature_c = static_cast<int>(*r.value().temperature) - 100;
  if (r.value().precipitation_prob) out.precipitation_prob = static_cast<int>(*r.value().precipitation_prob);
  return out;
}

Result<Packet> WipClient::roundtrip_udp(const std::string& host, uint16_t port, const Packet& req) noexcept {
  auto enc = encode_packet(req);
  if (!enc) return enc.error();
  const auto& payload = enc.value();
  if (std::getenv("WIPLIB_DEBUG_LOG")) {
    fprintf(stderr, "[wiplib] dest %s:%u, payload %zu bytes\n", host.c_str(), static_cast<unsigned>(port), payload.size());
    size_t dump = payload.size() < 32 ? payload.size() : 32;
    fprintf(stderr, "[wiplib] tx: ");
    for (size_t i = 0; i < dump; ++i) fprintf(stderr, "%02X ", payload[i]);
    fprintf(stderr, "\n");
  }

#if defined(_WIN32)
  WSADATA wsaData; if (WSAStartup(MAKEWORD(2,2), &wsaData) != 0) return make_error_code(WipErrc::io_error);
#endif
  int sock = -1;
#if defined(_WIN32)
  sock = static_cast<int>(::socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP));
  if (sock == INVALID_SOCKET) { WSACleanup(); return make_error_code(WipErrc::io_error); }
#else
  sock = ::socket(AF_INET, SOCK_DGRAM, 0);
  if (sock < 0) return make_error_code(WipErrc::io_error);
#endif
  // 短い受信タイムアウト（500ms）でループし、全体で最大10秒待機
#if defined(_WIN32)
  DWORD tv = 500; setsockopt(sock, SOL_SOCKET, SO_RCVTIMEO, reinterpret_cast<const char*>(&tv), sizeof(tv));
#else
  struct timeval tv; tv.tv_sec = 0; tv.tv_usec = 500000; setsockopt(sock, SOL_SOCKET, SO_RCVTIMEO, &tv, sizeof(tv));
#endif

  sockaddr_in addr{}; addr.sin_family = AF_INET; addr.sin_port = htons(port);
  if (::inet_pton(AF_INET, host.c_str(), &addr.sin_addr) != 1) {
    struct addrinfo hints{}; hints.ai_family = AF_INET; hints.ai_socktype = SOCK_DGRAM; struct addrinfo* res = nullptr;
    if (getaddrinfo(host.c_str(), nullptr, &hints, &res) != 0 || res == nullptr) {
#if defined(_WIN32)
      closesocket(sock); WSACleanup();
#else
      ::close(sock);
#endif
      return make_error_code(WipErrc::io_error);
    }
    auto* a = reinterpret_cast<sockaddr_in*>(res->ai_addr); addr.sin_addr = a->sin_addr; freeaddrinfo(res);
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
    ::close(sock);
#endif
    return make_error_code(WipErrc::io_error);
  }

  const auto deadline = std::chrono::steady_clock::now() + std::chrono::seconds(10);
  if (std::getenv("WIPLIB_DEBUG_LOG")) {
    fprintf(stderr, "[wiplib] waiting for response up to 10s...\n");
  }
  for (;;) {
    std::uint8_t buf[2048]; sockaddr_in from{}; socklen_t fromlen = sizeof(from);
    int rlen = static_cast<int>(::recvfrom(sock, reinterpret_cast<char*>(buf), sizeof(buf), 0,
                                 reinterpret_cast<sockaddr*>(&from), &fromlen));
    if (rlen > 0) {
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
        auto get_bits_le = [&](size_t start, size_t length)->uint32_t {
          uint32_t val = 0; for (size_t i=0;i<length;++i){ size_t bitpos=start+i; size_t byte_index=bitpos/8; size_t bit_index=bitpos%8; uint8_t bit=(buf[byte_index]>>bit_index)&0x1u; val |= (bit<<i);} return val;
        };
        uint16_t pid = static_cast<uint16_t>(get_bits_le(4, 12));
        if (pid == req.header.packet_id) {
          auto dec = decode_packet(std::span<const std::uint8_t>(buf, static_cast<size_t>(rlen)));
#if defined(_WIN32)
          closesocket(sock); WSACleanup();
#else
          ::close(sock);
#endif
          return dec;
        }
      }
      // 不一致 → 継続
    }
    if (std::chrono::steady_clock::now() >= deadline) {
      if (std::getenv("WIPLIB_DEBUG_LOG")) {
        fprintf(stderr, "[wiplib] timeout: no matching response within 10s\n");
      }
      break;
    }
  }
#if defined(_WIN32)
  closesocket(sock); WSACleanup();
#else
  ::close(sock);
#endif
  return make_error_code(WipErrc::timeout);
}

} // namespace wiplib::client
