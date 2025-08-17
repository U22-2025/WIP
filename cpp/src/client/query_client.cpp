#include "wiplib/client/query_client.hpp"

#include "wiplib/packet/codec.hpp"
#include <random>

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

wiplib::Result<WeatherResult> QueryClient::get_weather_data(std::string_view area_code,
                                                            const QueryOptions& opt) noexcept {
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
  p.header.timestamp = 0;
  uint32_t ac = 0; for (char c : area_code) if (c>='0' && c<='9') ac = ac*10u + static_cast<uint32_t>(c-'0');
  p.header.area_code = ac & 0xFFFFFu;
  // client does not use source; no extended fields for direct query

  auto enc = encode_packet(p);
  if (!enc) return enc.error();

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
  const auto& payload = enc.value();
  if (::sendto(sock, reinterpret_cast<const char*>(payload.data()), static_cast<int>(payload.size()), 0,
               reinterpret_cast<sockaddr*>(&addr), sizeof(addr)) < 0) {
#if defined(_WIN32)
    closesocket(sock); WSACleanup();
#else
    close(sock);
#endif
    return make_error_code(WipErrc::io_error);
  }

  std::uint8_t buf[2048]; sockaddr_in from{}; socklen_t fromlen = sizeof(from);
  int rlen = static_cast<int>(::recvfrom(sock, reinterpret_cast<char*>(buf), sizeof(buf), 0,
                               reinterpret_cast<sockaddr*>(&from), &fromlen));
#if defined(_WIN32)
  closesocket(sock); WSACleanup();
#else
  close(sock);
#endif
  if (rlen <= 0) return make_error_code(WipErrc::timeout);

  auto dec = decode_packet(std::span<const std::uint8_t>(buf, static_cast<size_t>(rlen)));
  if (!dec) return dec.error();
  const Packet& rp = dec.value();
  if (rp.header.type != PacketType::WeatherResponse) return make_error_code(WipErrc::invalid_packet);

  WeatherResult out{}; out.area_code = rp.header.area_code;
  if (rp.response_fields) {
    out.weather_code = rp.response_fields->weather_code;
    out.temperature = rp.response_fields->temperature; // +100オフセットの生値
    out.precipitation_prob = rp.response_fields->precipitation_prob;
  }
  return out;
}

} // namespace wiplib::client
