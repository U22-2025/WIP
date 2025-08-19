#include "wiplib/client/location_client.hpp"

#include "wiplib/packet/codec.hpp"
#include "wiplib/utils/auth.hpp"
#include "wiplib/packet/location_packet.hpp"
#include "wiplib/packet/extended_field.hpp"
#include "wiplib/packet/request.hpp"
#include "wiplib/packet/response.hpp"
#include <vector>
#include <string>
#include <cstdio>
#include <cmath>
#include <algorithm>
#include <future>
#include <thread>
#include <mutex>
#include <optional>
#include <sstream>
#include <iomanip>

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
#  include <cerrno>
#  include <cstring>
#endif

namespace wiplib::client {

using namespace wiplib::proto;

static std::vector<std::uint8_t> coord_to_le(double d) {
  std::vector<std::uint8_t> v(4);
  int32_t i = static_cast<int32_t>(d * 1000000.0);
  v[0] = static_cast<std::uint8_t>(i & 0xFF);
  v[1] = static_cast<std::uint8_t>((i >> 8) & 0xFF);
  v[2] = static_cast<std::uint8_t>((i >> 16) & 0xFF);
  v[3] = static_cast<std::uint8_t>((i >> 24) & 0xFF);
  return v;
}

wiplib::Result<std::string> LocationClient::get_area_code_simple(double latitude, double longitude) noexcept {
  Packet p{};
  p.header.version = 1;
  p.header.packet_id = 0x345; // 適当な固定でも良い
  p.header.type = PacketType::CoordinateRequest;
  p.header.flags.extended = true;
  p.header.area_code = 0;
  // timestamp is used in auth hash; set when auth enabled
  p.header.timestamp = 0; // default when auth disabled
  ExtendedField lat; lat.data_type = 33; lat.data = coord_to_le(latitude);
  ExtendedField lon; lon.data_type = 34; lon.data = coord_to_le(longitude);
  p.extensions.push_back(std::move(lat));
  p.extensions.push_back(std::move(lon));

  // Attach auth if configured
  if (auth_cfg_.enabled) {
    if (auth_cfg_.location && !auth_cfg_.location->empty()) {
      p.header.timestamp = static_cast<uint64_t>(std::chrono::duration_cast<std::chrono::seconds>(
          std::chrono::system_clock::now().time_since_epoch()).count());
      wiplib::utils::WIPAuth::attach_auth_hash(p, *auth_cfg_.location);
    }
  }

  auto enc = encode_packet(p);
  if (!enc) return enc.error();
  const auto& payload = enc.value();

  if (std::getenv("WIPLIB_DEBUG_LOG")) {
    fprintf(stderr, "[wiplib] LOC dest %s:%u, payload %zu bytes\n", host_.c_str(), static_cast<unsigned>(port_), payload.size());
    size_t dump = payload.size() < 32 ? payload.size() : 32;
    fprintf(stderr, "[wiplib] LOC tx: ");
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

  sockaddr_in addr{}; addr.sin_family = AF_INET; addr.sin_port = htons(port_);
  if (::inet_pton(AF_INET, host_.c_str(), &addr.sin_addr) != 1) {
    struct addrinfo hints{}; hints.ai_family = AF_INET; hints.ai_socktype = SOCK_DGRAM; struct addrinfo* res = nullptr;
    if (getaddrinfo(host_.c_str(), nullptr, &hints, &res) != 0 || !res) {
#if defined(_WIN32)
      closesocket(sock); WSACleanup();
#else
      close(sock);
#endif
      return make_error_code(WipErrc::io_error);
    }
    auto* a = reinterpret_cast<sockaddr_in*>(res->ai_addr); addr.sin_addr = a->sin_addr; freeaddrinfo(res);
  }

  int sret = ::sendto(sock, reinterpret_cast<const char*>(payload.data()), static_cast<int>(payload.size()), 0,
               reinterpret_cast<sockaddr*>(&addr), sizeof(addr));
  if (std::getenv("WIPLIB_DEBUG_LOG")) {
#if defined(_WIN32)
    if (sret < 0) { fprintf(stderr, "[wiplib] LOC sendto failed, WSA errno=%d\n", WSAGetLastError()); }
    else { fprintf(stderr, "[wiplib] LOC sendto ok (%d bytes)\n", sret); }
#else
    if (sret < 0) { fprintf(stderr, "[wiplib] LOC sendto failed, errno=%d (%s)\n", errno, strerror(errno)); }
    else { fprintf(stderr, "[wiplib] LOC sendto ok (%d bytes)\n", sret); }
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
  // set short timeout and loop up to ~10s
#if defined(_WIN32)
  DWORD tv = 500; setsockopt(sock, SOL_SOCKET, SO_RCVTIMEO, reinterpret_cast<const char*>(&tv), sizeof(tv));
#else
  struct timeval tv; tv.tv_sec = 0; tv.tv_usec = 500000; setsockopt(sock, SOL_SOCKET, SO_RCVTIMEO, &tv, sizeof(tv));
#endif
  if (std::getenv("WIPLIB_DEBUG_LOG")) {
    fprintf(stderr, "[wiplib] LOC waiting for CoordinateResponse up to 10s...\n");
  }
  const auto deadline = std::chrono::steady_clock::now() + std::chrono::seconds(10);
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
        fprintf(stderr, "[wiplib] LOC recv %dB from %s:%u\n", rlen, addrstr, ntohs(from.sin_port));
        size_t dump = static_cast<size_t>(rlen < 16 ? rlen : 16);
        fprintf(stderr, "[wiplib] LOC hdr: "); for (size_t i=0;i<dump;++i) fprintf(stderr, "%02X ", buf[i]); fprintf(stderr, "\n");
      }
      auto dec = decode_packet(std::span<const std::uint8_t>(buf, static_cast<size_t>(rlen)));
      if (!dec) {
        if (std::getenv("WIPLIB_DEBUG_LOG")) fprintf(stderr, "[wiplib] LOC decode error: %s\n", dec.error().message().c_str());
        continue;
      }
      const Packet& rp = dec.value();
      if (rp.header.type == PacketType::CoordinateResponse) {
        // Optional response verification (independent of response_auth flag)
        if (auth_cfg_.verify_response) {
          const std::string* pass = nullptr;
          if (auth_cfg_.location && !auth_cfg_.location->empty()) pass = &*auth_cfg_.location;
          if (pass) {
            std::vector<uint8_t> recv_hash;
            for (const auto& ef : rp.extensions) {
              if (ef.data_type == 4) {
                const auto& d = ef.data; if (d.size()==64) {
                  recv_hash.reserve(32);
                  auto hexval = [](uint8_t c)->int { if (c>='0'&&c<='9') return c-'0'; if (c>='a'&&c<='f') return c-'a'+10; if (c>='A'&&c<='F') return c-'A'+10; return -1; };
                  bool ok=true; for (size_t i=0;i<64;i+=2){ int hi=hexval(d[i]); int lo=hexval(d[i+1]); if (hi<0||lo<0){ok=false;break;} recv_hash.push_back(static_cast<uint8_t>((hi<<4)|lo)); }
                  if (!ok) recv_hash.clear();
                }
                break;
              }
            }
            if (!recv_hash.empty()) {
              if (!wiplib::utils::WIPAuth::verify_auth_hash(rp.header.packet_id, rp.header.timestamp, *pass, recv_hash)) {
#if defined(_WIN32)
                closesocket(sock); WSACleanup();
#else
                close(sock);
#endif
                return make_error_code(WipErrc::invalid_packet);
              }
            }
          }
        }
#if defined(_WIN32)
        closesocket(sock); WSACleanup();
#else
        close(sock);
#endif
        char out[16]; std::snprintf(out, sizeof(out), "%06u", rp.header.area_code);
        return std::string(out);
      }
      // ignore other packet types and keep waiting
    }
    if (std::chrono::steady_clock::now() >= deadline) {
      if (std::getenv("WIPLIB_DEBUG_LOG")) fprintf(stderr, "[wiplib] LOC timeout waiting for response\n");
      break;
    }
  }
#if defined(_WIN32)
  closesocket(sock); WSACleanup();
#else
  close(sock);
#endif
  return make_error_code(WipErrc::timeout);
}

// ---------------------------------------
// 詳細エリアコード取得（非同期）
// ---------------------------------------

std::future<wiplib::Result<CoordinateResult>> LocationClient::get_area_code_detailed_async(
    const packet::Coordinate& coordinate,
    PrecisionLevel precision_level,
    std::chrono::milliseconds timeout) {
  return std::async(std::launch::async, [=, this]() -> wiplib::Result<CoordinateResult> {
    update_statistics("total_requests");

    const std::string cache_key = generate_cache_key(coordinate, precision_level);
    if (cache_enabled_) {
      if (auto cached = get_cached_result(cache_key)) {
        update_statistics("cache_hits");
        return *cached;
      }
    }
    update_statistics("cache_misses");

    auto start = std::chrono::steady_clock::now();
    auto ac = get_area_code_simple(coordinate.latitude, coordinate.longitude);
    auto end = std::chrono::steady_clock::now();

    if (!ac) {
      update_statistics("failed_requests");
      return ac.error();
    }

    CoordinateResult result = perform_coordinate_conversion(coordinate, precision_level, timeout);
    result.area_code = ac.value();
    result.response_time = std::chrono::duration_cast<std::chrono::milliseconds>(end - start);

    if (cache_enabled_) cache_result(cache_key, result);
    return result;
  });
}

// ---------------------------------------
// バッチ変換（非同期）
// ---------------------------------------

std::future<std::vector<wiplib::Result<CoordinateResult>>> LocationClient::batch_convert_async(
    const std::vector<packet::Coordinate>& coordinates,
    PrecisionLevel precision_level,
    std::chrono::milliseconds timeout) {
  return std::async(std::launch::async, [=, this]() {
    std::vector<wiplib::Result<CoordinateResult>> results;
    results.reserve(coordinates.size());
    for (const auto& c : coordinates) {
      auto r = get_area_code_detailed_async(c, precision_level, timeout).get();
      results.push_back(std::move(r));
    }
    return results;
  });
}

// ---------------------------------------
// GPS精度管理
// ---------------------------------------

packet::Coordinate LocationClient::manage_gps_precision(
    const packet::Coordinate& coordinate,
    PrecisionLevel target_precision) const {
  packet::Coordinate result = coordinate;
  int digits = 3;
  switch (target_precision) {
    case PrecisionLevel::Low: digits = 2; break;
    case PrecisionLevel::Medium: digits = 3; break;
    case PrecisionLevel::High: digits = 4; break;
    case PrecisionLevel::VeryHigh: digits = 5; break;
  }
  double factor = std::pow(10.0, digits);
  result.latitude = std::round(result.latitude * factor) / factor;
  result.longitude = std::round(result.longitude * factor) / factor;
  return result;
}

// ---------------------------------------
// 境界チェック
// ---------------------------------------

bool LocationClient::check_geographic_bounds(
    const packet::Coordinate& coordinate,
    const std::optional<GeographicBounds>& bounds) const {
  const GeographicBounds& b = bounds ? *bounds : geographic_bounds_;
  return is_coordinate_in_bounds(coordinate, b);
}

// ---------------------------------------
// 座標正規化
// ---------------------------------------

packet::Coordinate LocationClient::normalize_coordinate(
    const packet::Coordinate& coordinate,
    uint8_t precision) const {
  packet::Coordinate result = coordinate;
  double factor = std::pow(10.0, precision);
  result.latitude = std::round(result.latitude * factor) / factor;
  result.longitude = std::round(result.longitude * factor) / factor;
  return result;
}

// ---------------------------------------
// 精度推定
// ---------------------------------------

PrecisionLevel LocationClient::estimate_precision_level(const packet::Coordinate& coordinate) const {
  auto digits = [](double v) {
    v = std::abs(v);
    for (int d = 0; d <= 6; ++d) {
      double f = std::pow(10.0, d);
      if (std::abs(v * f - std::round(v * f)) < 1e-6) return d;
    }
    return 6;
  };
  int d = std::max(digits(coordinate.latitude), digits(coordinate.longitude));
  if (d >= 5) return PrecisionLevel::VeryHigh;
  if (d >= 4) return PrecisionLevel::High;
  if (d >= 3) return PrecisionLevel::Medium;
  return PrecisionLevel::Low;
}

// ---------------------------------------
// 座標妥当性検証
// ---------------------------------------

std::pair<bool, std::string> LocationClient::validate_coordinate(const packet::Coordinate& coordinate) const {
  if (coordinate.latitude < -90.0 || coordinate.latitude > 90.0)
    return {false, "latitude out of range"};
  if (coordinate.longitude < -180.0 || coordinate.longitude > 180.0)
    return {false, "longitude out of range"};
  return {true, ""};
}

// ---------------------------------------
// 境界設定/取得
// ---------------------------------------

void LocationClient::set_geographic_bounds(const GeographicBounds& bounds) {
  geographic_bounds_ = bounds;
}

GeographicBounds LocationClient::get_geographic_bounds() const {
  return geographic_bounds_;
}

// ---------------------------------------
// キャッシュ設定
// ---------------------------------------

void LocationClient::set_cache_enabled(bool enabled, std::chrono::seconds cache_ttl) {
  std::scoped_lock lock(cache_mutex_);
  cache_enabled_ = enabled;
  cache_ttl_ = cache_ttl;
  if (!enabled) cache_.clear();
}

// ---------------------------------------
// 統計取得/リセット
// ---------------------------------------

std::unordered_map<std::string, uint64_t> LocationClient::get_conversion_statistics() const {
  std::scoped_lock lock(stats_mutex_);
  return conversion_stats_;
}

void LocationClient::reset_statistics() {
  std::scoped_lock lock(stats_mutex_);
  conversion_stats_.clear();
}

// ---------------------------------------
// 変換処理（共通）
// ---------------------------------------

CoordinateResult LocationClient::perform_coordinate_conversion(
    const packet::Coordinate& coordinate,
    PrecisionLevel precision_level,
    std::chrono::milliseconds /*timeout*/) const {
  CoordinateResult result{};
  result.original_coordinate = coordinate;
  result.precision_level = precision_level;
  result.accuracy_meters = calculate_accuracy_from_precision(precision_level);
  auto managed = manage_gps_precision(coordinate, precision_level);
  result.normalized_coordinate = normalize_coordinate(managed, 6);
  result.is_within_bounds = check_geographic_bounds(managed);
  return result;
}

// ---------------------------------------
// キャッシュ関連
// ---------------------------------------

std::string LocationClient::generate_cache_key(const packet::Coordinate& coordinate,
                                               PrecisionLevel precision_level) const {
  std::ostringstream oss;
  auto c = manage_gps_precision(coordinate, precision_level);
  oss << std::fixed << std::setprecision(4) << c.latitude << ',' << c.longitude
      << ':' << static_cast<int>(precision_level);
  return oss.str();
}

std::optional<CoordinateResult> LocationClient::get_cached_result(const std::string& cache_key) const {
  std::scoped_lock lock(cache_mutex_);
  if (!cache_enabled_) return std::nullopt;
  auto it = cache_.find(cache_key);
  if (it == cache_.end()) return std::nullopt;
  if (std::chrono::steady_clock::now() - it->second.second > cache_ttl_) {
    cache_.erase(it);
    return std::nullopt;
  }
  return it->second.first;
}

void LocationClient::cache_result(const std::string& cache_key, const CoordinateResult& result) const {
  std::scoped_lock lock(cache_mutex_);
  if (!cache_enabled_) return;
  cache_[cache_key] = {result, std::chrono::steady_clock::now()};
}

void LocationClient::update_statistics(const std::string& key, uint64_t increment) const {
  std::scoped_lock lock(stats_mutex_);
  conversion_stats_[key] += increment;
}

double LocationClient::calculate_accuracy_from_precision(PrecisionLevel precision_level) const {
  switch (precision_level) {
    case PrecisionLevel::Low: return 1000.0;
    case PrecisionLevel::Medium: return 100.0;
    case PrecisionLevel::High: return 10.0;
    case PrecisionLevel::VeryHigh: return 1.0;
  }
  return 100.0;
}

bool LocationClient::is_coordinate_in_bounds(const packet::Coordinate& coordinate,
                                             const GeographicBounds& bounds) const {
  return coordinate.latitude >= bounds.min_latitude &&
         coordinate.latitude <= bounds.max_latitude &&
         coordinate.longitude >= bounds.min_longitude &&
         coordinate.longitude <= bounds.max_longitude;
}

// ---------------------------------------
// ファクトリー実装
// ---------------------------------------

std::unique_ptr<LocationClient> LocationClientFactory::create_basic(
    const std::string& host, uint16_t port) {
  return std::make_unique<LocationClient>(host, port);
}

std::unique_ptr<LocationClient> LocationClientFactory::create_high_precision(
    const std::string& host, uint16_t port, const GeographicBounds& bounds) {
  auto client = std::make_unique<LocationClient>(host, port);
  client->set_geographic_bounds(bounds);
  client->set_cache_enabled(true);
  return client;
}

} // namespace wiplib::client
