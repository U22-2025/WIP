#include "wiplib/client/weather_client.hpp"

#include "wiplib/packet/codec.hpp"
#include "wiplib/utils/auth.hpp"
#include "wiplib/packet/extended_field.hpp"
#include "wiplib/utils/dotenv.hpp"
#include "wiplib/utils/platform_compat.hpp"
#include <variant>
#include <chrono>
#include <random>
#include <cstring>
#include <cstdio>
#include <cstdlib>

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

WeatherClient WeatherClient::from_env() {
  return WeatherClient(default_host(), default_port());
}

std::string WeatherClient::default_host() {
  (void)wiplib::utils::load_dotenv(".env", false, 3);
  if (const char* h = std::getenv("WEATHER_SERVER_HOST")) return h;
  return "127.0.0.1";
}

uint16_t WeatherClient::default_port() {
  (void)wiplib::utils::load_dotenv(".env", false, 3);
  if (const char* p = std::getenv("WEATHER_SERVER_PORT")) return static_cast<uint16_t>(std::stoi(p));
  return 4110;
}

wiplib::Result<WeatherResult> WeatherClient::get_weather_by_coordinates(double lat, double lon, const QueryOptions& opt) noexcept {
  using namespace wiplib::proto;
  Packet p{};
  p.header.version = 1;
  // packet_id: ランダム12bit
  std::mt19937 rng{std::random_device{}()};
  p.header.packet_id = static_cast<uint16_t>(rng() & 0x0FFFu);
  // 座標指定は LocationRequest(Type=0) を送信し、
  // LocationResponse(Type=1) の後に WeatherResponse(Type=3) を待つ（Python実装準拠）
  p.header.type = PacketType::CoordinateRequest;
  p.header.flags.weather = opt.weather;
  p.header.flags.temperature = opt.temperature;
  p.header.flags.precipitation = opt.precipitation_prob;
  p.header.flags.alert = opt.alerts;
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
  p.header.flags.precipitation = opt.precipitation_prob;
  p.header.flags.alert = opt.alerts;
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
  // Prepare packet and attach auth if configured
  Packet send_pkt = req;
  if (auth_cfg_.enabled) {
    // Attach auth for proxy WeatherServer request when passphrase provided
    if (auth_cfg_.weather && !auth_cfg_.weather->empty()) {
      wiplib::utils::WIPAuth::attach_auth_hash(send_pkt, *auth_cfg_.weather);
    }
  }

  // Set response_auth flag if client wants server to authenticate responses
  if (auth_cfg_.weather_server_response_auth_enabled) {
    send_pkt.header.flags.response_auth = true;
  }
  auto enc = encode_packet(send_pkt);
  if (!enc) return enc.error();
  const auto& payload = enc.value();

  // Optional debug: show destination and payload details before sending
  if (std::getenv("WIPLIB_DEBUG_LOG")) {
    fprintf(stderr, "[wiplib] dest %s:%u, payload %zu bytes\n", host_.c_str(), static_cast<unsigned>(port_), payload.size());
    size_t dump = payload.size() < 32 ? payload.size() : 32;
    fprintf(stderr, "[wiplib] tx: ");
    for (size_t i = 0; i < dump; ++i) fprintf(stderr, "%02X ", payload[i]);
    fprintf(stderr, "\n");
    if (payload.size() >= kFixedHeaderSize) {
      auto get_bits_le_dbg = [&](size_t start, size_t length)->uint32_t {
        uint32_t val = 0; for (size_t i=0;i<length;++i){ size_t bitpos=start+i; size_t byte_index=bitpos/8; size_t bit_index=bitpos%8; uint8_t bit=(payload[byte_index]>>bit_index)&0x1u; val |= (bit<<i);} return val;
      };
      uint32_t pid_le = get_bits_le_dbg(4, 12);
      fprintf(stderr, "[wiplib] tx pid=%u (req=%u)\n", pid_le, static_cast<unsigned>(req.header.packet_id));
    }
  }

  if (!wiplib::utils::initialize_platform()) {
    return make_error_code(WipErrc::io_error);
  }

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
    wiplib::utils::platform_setsockopt(sock, SOL_SOCKET, SO_RCVTIMEO, &tv, sizeof(tv));
#else
    struct timeval tv; tv.tv_sec = 0; tv.tv_usec = 500000;
    wiplib::utils::platform_setsockopt(sock, SOL_SOCKET, SO_RCVTIMEO, &tv, sizeof(tv));
#endif

    sockaddr_in addr{}; addr.sin_family = AF_INET; addr.sin_port = htons(port_);
    if (::inet_pton(AF_INET, host_.c_str(), &addr.sin_addr) != 1) {
      // 名前解決（IPv4）
      struct addrinfo hints{}; hints.ai_family = AF_INET; hints.ai_socktype = SOCK_DGRAM;
      struct addrinfo* res = nullptr;
      if (getaddrinfo(host_.c_str(), nullptr, &hints, &res) != 0 || res == nullptr) {
#if defined(_WIN32)
        closesocket(sock);
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
      closesocket(sock);
#else
      close(sock);
#endif
      return make_error_code(WipErrc::io_error);
    }

    const auto deadline = std::chrono::steady_clock::now() + std::chrono::seconds(10);
    if (std::getenv("WIPLIB_DEBUG_LOG")) {
      fprintf(stderr, "[wiplib] waiting for response up to 10s...\n");
    }
    bool saw_location_response = false;
    WeatherResult result{};
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

            // 座標リクエストの場合: LocationResponse(1) を受けたら、クライアントが QueryRequest(2) を送信し、WeatherResponse(3) を待つ
            if (req.header.type == PacketType::CoordinateRequest) {
              if (static_cast<uint8_t>(rp.header.type) == static_cast<uint8_t>(PacketType::CoordinateResponse)) {
                // Check if response has response_auth flag set
                bool response_has_auth_flag = rp.header.flags.response_auth;
                
                // Optional response verification for weather server (proxy)
                if (auth_cfg_.weather_server_response_auth_enabled) {
                  // Only verify if response has response_auth flag set
                  if (!response_has_auth_flag) {
                    if (std::getenv("WIPLIB_DEBUG_LOG"))
                      fprintf(stderr, "[wiplib] Response authentication skipped - response_auth flag not set\n");
                    // Continue without verification when flag is not set
                  } else {
                    const std::string* pass = nullptr;
                    if (auth_cfg_.weather && !auth_cfg_.weather->empty()) pass = &*auth_cfg_.weather;
                  if (pass) {
                    std::vector<uint8_t> recv_hash;
                    for (const auto& ef : rp.extensions) {
                      if (ef.data_type == static_cast<uint8_t>(wiplib::packet::ExtendedFieldKey::AuthHash)) {
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
                        closesocket(sock);
#else
                        close(sock);
#endif
                        return make_error_code(WipErrc::invalid_packet);
                      }
                    }
                    }
                  }
                }
                saw_location_response = true;
                result.area_code = rp.header.area_code; // 受領エリアコード
                // 直ちに QueryRequest を送信（常にクライアントが2回目を送る）
                // 送信先は以下の優先順位で決定:
                //  - LocationServer からの応答と判断した場合（応答元ポート=4109 もしくは初期送信ポート=4109）
                //      → QueryServer (env QUERY_GENERATOR_HOST/PORT または host_:4111)
                //  - それ以外（WeatherServer 経由想定）
                //      → 初期送信先 host_:port_（WeatherServer が転送）
                uint16_t from_port = ntohs(from.sin_port);
                bool from_location = (from_port == 4109) || (port_ == 4109);
                std::string qhost;
                uint16_t qport = 0;
                if (from_location) {
                  const char* env_qh = std::getenv("QUERY_GENERATOR_HOST");
                  const char* env_qp = std::getenv("QUERY_GENERATOR_PORT");
                  qhost = env_qh ? std::string(env_qh) : host_;
                  qport = env_qp ? static_cast<uint16_t>(std::stoi(env_qp)) : static_cast<uint16_t>(4111);
                } else {
                  qhost = host_;
                  qport = port_;
                }

                sockaddr_in qaddr{}; qaddr.sin_family = AF_INET; qaddr.sin_port = htons(qport);
                if (::inet_pton(AF_INET, qhost.c_str(), &qaddr.sin_addr) != 1) {
                  struct addrinfo hints{}; hints.ai_family = AF_INET; hints.ai_socktype = SOCK_DGRAM; struct addrinfo* res2 = nullptr;
                  if (getaddrinfo(qhost.c_str(), nullptr, &hints, &res2) == 0 && res2) {
                    auto* a2 = reinterpret_cast<sockaddr_in*>(res2->ai_addr); qaddr.sin_addr = a2->sin_addr; freeaddrinfo(res2);
                  } else if (std::getenv("WIPLIB_DEBUG_LOG")) {
                    fprintf(stderr, "[wiplib] failed to resolve query host %s\n", qhost.c_str());
                  }
                }

                Packet qreq{};
                qreq.header.version = req.header.version;
                qreq.header.packet_id = req.header.packet_id; // 同一ID
                qreq.header.type = PacketType::WeatherRequest;
                qreq.header.flags = req.header.flags; // weather/temperature等を引き継ぐ
                qreq.header.flags.extended = false; // client does not include source
                qreq.header.day = req.header.day;
                qreq.header.timestamp = static_cast<uint64_t>(std::chrono::duration_cast<std::chrono::seconds>(
                    std::chrono::system_clock::now().time_since_epoch()).count());
                qreq.header.area_code = rp.header.area_code;

                // Attach auth for QueryRequest to weather server (proxy) if configured
                if (auth_cfg_.enabled) {
                  if (auth_cfg_.weather && !auth_cfg_.weather->empty()) {
                    wiplib::utils::WIPAuth::attach_auth_hash(qreq, *auth_cfg_.weather);
                  }
                }

                // Set response_auth flag for query request to weather server (proxy)
                if (auth_cfg_.weather_server_response_auth_enabled) {
                  qreq.header.flags.response_auth = true;
                }

                auto enc2 = encode_packet(qreq);
                if (!enc2) {
                  if (std::getenv("WIPLIB_DEBUG_LOG")) fprintf(stderr, "[wiplib] encode query request failed: %s\n", enc2.error().message().c_str());
                } else {
                  const auto& payload2 = enc2.value();
                  int s2 = ::sendto(sock, reinterpret_cast<const char*>(payload2.data()), static_cast<int>(payload2.size()), 0,
                                     reinterpret_cast<sockaddr*>(&qaddr), sizeof(qaddr));
                  if (std::getenv("WIPLIB_DEBUG_LOG")) {
#if defined(_WIN32)
                    if (s2 < 0) { fprintf(stderr, "[wiplib] sent QueryRequest to %s:%u failed, WSA errno=%d\n", qhost.c_str(), static_cast<unsigned>(qport), WSAGetLastError()); }
                    else { fprintf(stderr, "[wiplib] sent QueryRequest to %s:%u ok (%d bytes)\n", qhost.c_str(), static_cast<unsigned>(qport), s2); }
#else
                    if (s2 < 0) { fprintf(stderr, "[wiplib] sent QueryRequest to %s:%u failed, errno=%d (%s)\n", qhost.c_str(), static_cast<unsigned>(qport), errno, strerror(errno)); }
                    else { fprintf(stderr, "[wiplib] sent QueryRequest to %s:%u ok (%d bytes)\n", qhost.c_str(), static_cast<unsigned>(qport), s2); }
#endif
                  }
                }
                if (std::getenv("WIPLIB_DEBUG_LOG")) {
                  fprintf(stderr, "[wiplib] waiting for WeatherResponse...\n");
                }
                // 続けて待機
                continue;
              }
              if (static_cast<uint8_t>(rp.header.type) == static_cast<uint8_t>(PacketType::WeatherResponse)) {
                // Optional response verification for weather server (proxy)
                if (auth_cfg_.weather_server_response_auth_enabled) {
                  const std::string* pass = nullptr;
                  if (auth_cfg_.weather && !auth_cfg_.weather->empty()) pass = &*auth_cfg_.weather;
                  if (pass) {
                    // find ext id=4 hex64
                    std::vector<uint8_t> recv_hash;
                    for (const auto& ef : rp.extensions) {
                      if (ef.data_type == static_cast<uint8_t>(wiplib::packet::ExtendedFieldKey::AuthHash)) {
                        const auto& d = ef.data;
                        if (d.size() == 64) {
                          // hex to bytes
                          recv_hash.reserve(32);
                          auto hexval = [](uint8_t c)->int { if (c>='0'&&c<='9') return c-'0'; if (c>='a'&&c<='f') return c-'a'+10; if (c>='A'&&c<='F') return c-'A'+10; return -1; };
                          bool ok=true;
                          for (size_t i=0;i<64;i+=2) { int hi=hexval(d[i]); int lo=hexval(d[i+1]); if (hi<0||lo<0){ ok=false; break;} recv_hash.push_back(static_cast<uint8_t>((hi<<4)|lo)); }
                          if (!ok) recv_hash.clear();
                        }
                        break;
                      }
                    }
                    if (!recv_hash.empty()) {
                      if (!wiplib::utils::WIPAuth::verify_auth_hash(rp.header.packet_id, rp.header.timestamp, *pass, recv_hash)) {
#if defined(_WIN32)
                        closesocket(sock);
#else
                        close(sock);
#endif
                        return make_error_code(WipErrc::invalid_packet);
                      }
                    }
                  }
                }
                // 最終レスポンス
                if (rp.response_fields.has_value()) {
                  result.weather_code = rp.response_fields->weather_code;
                  result.temperature = rp.response_fields->temperature;
                  result.precipitation_prob = rp.response_fields->precipitation_prob;
                }
                if (auto f = packet::ExtendedFieldManager::get_field(rp, packet::ExtendedFieldKey::Alert)) {
                  if (auto v = std::get_if<std::vector<std::string>>(&*f)) {
                    result.alerts = *v;
                  }
                }
                if (auto f = packet::ExtendedFieldManager::get_field(rp, packet::ExtendedFieldKey::Disaster)) {
                  if (auto v = std::get_if<std::vector<std::string>>(&*f)) {
                    result.disasters = *v;
                  }
                }
                if (result.area_code == 0) result.area_code = rp.header.area_code;
                // クローズして返す
#if defined(_WIN32)
                closesocket(sock);
#else
                close(sock);
#endif
                return result;
              }
              // その他のタイプは無視して待機を継続
            } else {
              // エリアコード指定（WeatherRequest→WeatherResponse 1段階）
              if (static_cast<uint8_t>(rp.header.type) == static_cast<uint8_t>(PacketType::WeatherResponse)) {
                // Optional response verification for weather server (proxy - direct request)
                if (auth_cfg_.weather_server_response_auth_enabled) {
                  const std::string* pass = nullptr;
                  if (auth_cfg_.weather && !auth_cfg_.weather->empty()) pass = &*auth_cfg_.weather;
                  if (pass) {
                    std::vector<uint8_t> recv_hash;
                    for (const auto& ef : rp.extensions) {
                      if (ef.data_type == static_cast<uint8_t>(wiplib::packet::ExtendedFieldKey::AuthHash)) {
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
                        closesocket(sock);
#else
                        close(sock);
#endif
                        return make_error_code(WipErrc::invalid_packet);
                      }
                    }
                  }
                }
                result.area_code = rp.header.area_code;
                if (rp.response_fields.has_value()) {
                  result.weather_code = rp.response_fields->weather_code;
                  result.temperature = rp.response_fields->temperature;
                  result.precipitation_prob = rp.response_fields->precipitation_prob;
                }
                if (auto f = packet::ExtendedFieldManager::get_field(rp, packet::ExtendedFieldKey::Alert)) {
                  if (auto v = std::get_if<std::vector<std::string>>(&*f)) {
                    result.alerts = *v;
                  }
                }
                if (auto f = packet::ExtendedFieldManager::get_field(rp, packet::ExtendedFieldKey::Disaster)) {
                  if (auto v = std::get_if<std::vector<std::string>>(&*f)) {
                    result.disasters = *v;
                  }
                }
#if defined(_WIN32)
                closesocket(sock);
#else
                close(sock);
#endif
                return result;
              }
            }
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
    closesocket(sock);
#else
    close(sock);
#endif
    return make_error_code(WipErrc::timeout);
  } while(false);

  return make_error_code(WipErrc::io_error);
}

} // namespace wiplib::client
