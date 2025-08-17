#include "wiplib/client/location_client.hpp"

#include "wiplib/packet/codec.hpp"
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
  p.header.timestamp = 0; // 任意
  ExtendedField lat; lat.data_type = 33; lat.data = coord_to_le(latitude);
  ExtendedField lon; lon.data_type = 34; lon.data = coord_to_le(longitude);
  p.extensions.push_back(std::move(lat));
  p.extensions.push_back(std::move(lon));

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

} // namespace wiplib::client
