#include <iostream>
#include <string>
#include <vector>
#include <optional>
#include <chrono>
#include <cstdint>

#include "wiplib/packet/codec.hpp"

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

using namespace wiplib::proto;

struct Args {
  std::string host = "127.0.0.1";
  uint16_t port = 4110; // Weather Server (proxy)
  bool use_coords = false;
  std::optional<std::pair<double,double>> coords;
  std::optional<std::string> area;
  bool weather = true;
  bool temperature = true;
  bool precipitation = true;
  bool alert = false;
  bool disaster = false;
  uint8_t day = 0;
};

static void usage() {
  std::cout << "Usage: wip_packet_roundtrip [--host H] [--port P] "
               "(--coords LAT LON | --area CODE) [--no-weather] [--no-temperature] [--no-precipitation] [--alert] [--disaster] [--day N]\n";
}

static bool parse_args(int argc, char** argv, Args& a) {
  for (int i = 1; i < argc; ++i) {
    std::string t = argv[i];
    auto next = [&](const char* err) -> const char* { if (i+1>=argc){ std::cerr<<err<<"\n"; return static_cast<const char*>(nullptr);} return argv[++i]; };
    if (t == "--host") { const char* v = next("--host needs value"); if(!v) return false; a.host = v; }
    else if (t == "--port") { const char* v = next("--port needs value"); if(!v) return false; a.port = static_cast<uint16_t>(std::stoi(v)); }
    else if (t == "--coords") { const char* v1 = next("--coords needs lat"); if(!v1) return false; const char* v2 = next("--coords needs lon"); if(!v2) return false; a.use_coords=true; a.coords = std::make_pair(std::stod(v1), std::stod(v2)); }
    else if (t == "--area") { const char* v = next("--area needs code"); if(!v) return false; a.area = std::string(v); }
    else if (t == "--no-weather") { a.weather = false; }
    else if (t == "--no-temperature") { a.temperature = false; }
    else if (t == "--no-precipitation") { a.precipitation = false; }
    else if (t == "--alert") { a.alert = true; }
    else if (t == "--disaster") { a.disaster = true; }
    else if (t == "--day") { const char* v = next("--day needs value"); if(!v) return false; a.day = static_cast<uint8_t>(std::stoi(v)); }
    else if (t == "-h" || t == "--help") { usage(); return false; }
    else { std::cerr << "Unknown arg: " << t << "\n"; return false; }
  }
  if (!(a.coords.has_value() ^ a.area.has_value())) {
    std::cerr << "Specify either --coords or --area\n"; return false;
  }
  return true;
}

static uint64_t now_sec() {
  return static_cast<uint64_t>(std::chrono::duration_cast<std::chrono::seconds>(
      std::chrono::system_clock::now().time_since_epoch()).count());
}

static int roundtrip(const std::string& host, uint16_t port, const Packet& req) {
  auto enc = encode_packet(req);
  if (!enc) { std::cerr << "encode error: " << enc.error().message() << "\n"; return 1; }
#if defined(_WIN32)
  WSADATA wsaData; if (WSAStartup(MAKEWORD(2,2), &wsaData) != 0) { std::cerr << "WSAStartup failed\n"; return 1; }
#endif
  int sock = -1;
#if defined(_WIN32)
  sock = static_cast<int>(::socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP));
  if (sock == INVALID_SOCKET) { WSACleanup(); std::cerr << "socket failed\n"; return 1; }
#else
  sock = ::socket(AF_INET, SOCK_DGRAM, 0);
  if (sock < 0) { std::cerr << "socket failed\n"; return 1; }
#endif
#if defined(_WIN32)
  DWORD tv = 2000; setsockopt(sock, SOL_SOCKET, SO_RCVTIMEO, reinterpret_cast<const char*>(&tv), sizeof(tv));
#else
  struct timeval tv; tv.tv_sec = 2; tv.tv_usec = 0; setsockopt(sock, SOL_SOCKET, SO_RCVTIMEO, &tv, sizeof(tv));
#endif
  sockaddr_in addr{}; addr.sin_family = AF_INET; addr.sin_port = htons(port);
  if (::inet_pton(AF_INET, host.c_str(), &addr.sin_addr) != 1) {
    struct addrinfo hints{}; hints.ai_family = AF_INET; hints.ai_socktype = SOCK_DGRAM; struct addrinfo* res = nullptr;
    if (getaddrinfo(host.c_str(), nullptr, &hints, &res) != 0 || !res) {
#if defined(_WIN32)
      closesocket(sock); WSACleanup();
#else
      close(sock);
#endif
      std::cerr << "resolve failed\n"; return 1;
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
    std::cerr << "sendto failed\n"; return 1;
  }

  for(;;){
    std::uint8_t buf[2048]; sockaddr_in from{}; socklen_t fromlen = sizeof(from);
    int rlen = static_cast<int>(::recvfrom(sock, reinterpret_cast<char*>(buf), sizeof(buf), 0,
                                 reinterpret_cast<sockaddr*>(&from), &fromlen));
    if (rlen <= 0) { std::cerr << "timeout/no data\n"; break; }
    // Debug: dump header and dual PID
    {
      char addrstr[64] = {0};
#if defined(_WIN32)
      ::InetNtopA(AF_INET, &from.sin_addr, addrstr, sizeof(addrstr));
#else
      ::inet_ntop(AF_INET, &from.sin_addr, addrstr, sizeof(addrstr));
#endif
      std::cerr << "recv " << rlen << "B from " << addrstr << ":" << ntohs(from.sin_port) << "\n";
      size_t dump = static_cast<size_t>(rlen < 16 ? rlen : 16);
      std::cerr << "hdr: "; for (size_t i=0;i<dump;++i) { char b[4]; std::snprintf(b,sizeof(b),"%02X ", buf[i]); std::cerr << b; } std::cerr << "\n";
      auto get_bits_le = [&](size_t start, size_t length)->uint32_t { uint32_t val=0; for(size_t i=0;i<length;++i){ size_t bitpos=start+i; size_t byte_index=bitpos/8; size_t bit_index=bitpos%8; uint8_t bit=(buf[byte_index]>>bit_index)&0x1u; val |= (bit<<i);} return val; };
      auto get_bits_msb = [&](size_t start, size_t length)->uint32_t { uint32_t val=0; for(size_t i=0;i<length;++i){ size_t bitpos=start+i; size_t byte_index=bitpos/8; size_t bit_index=bitpos%8; uint8_t bit=(buf[byte_index]>>(7-bit_index))&0x1u; val |= (bit<<i);} return val; };
      uint32_t pid_le = get_bits_le(4,12); uint32_t pid_msb = get_bits_msb(4,12);
      std::cerr << "pid_le=" << pid_le << " pid_msb=" << pid_msb << " req=" << static_cast<unsigned>(req.header.packet_id) << "\n";
    }
    if (rlen >= static_cast<int>(kFixedHeaderSize)) {
      auto dec = decode_packet(std::span<const std::uint8_t>(buf, static_cast<size_t>(rlen)));
      if (!dec) { std::cerr << "decode error: " << dec.error().message() << "\n"; break; }
      const auto& rp = dec.value();
      std::cout << "Response: type=" << static_cast<int>(rp.header.type)
                << " area=" << rp.header.area_code
                << " day=" << static_cast<int>(rp.header.day) << "\n";
      if (rp.response_fields.has_value()) {
        std::cout << "  weather_code=" << rp.response_fields->weather_code
                  << " temperature(raw)=" << static_cast<int>(rp.response_fields->temperature)
                  << " pop=" << static_cast<int>(rp.response_fields->precipitation_prob) << "\n";
      }
#if defined(_WIN32)
      closesocket(sock); WSACleanup();
#else
      close(sock);
#endif
      return 0;
    }
  }
#if defined(_WIN32)
  closesocket(sock); WSACleanup();
#else
  close(sock);
#endif
  return 1;
}

int main(int argc, char** argv) {
  Args a; if (!parse_args(argc, argv, a)) { usage(); return 2; }

  Packet p{};
  p.header.version = 1;
  p.header.packet_id = static_cast<uint16_t>(0x123u); // サンプル: 固定でもOK
  p.header.flags.weather = a.weather;
  p.header.flags.temperature = a.temperature;
  p.header.flags.precipitation = a.precipitation;
  p.header.flags.alert = a.alert;
  p.header.flags.disaster = a.disaster;
  p.header.day = a.day;
  p.header.timestamp = now_sec();

  if (a.coords) {
    p.header.type = PacketType::CoordinateRequest;
    p.header.area_code = 0;
    // 拡張: 緯度/経度（各 4B の int32 LE, 倍率 1e6）
    auto push_coord = [](double d){ std::vector<std::uint8_t> v(4); int32_t i = static_cast<int32_t>(d * 1000000.0); v[0]=i&0xFF; v[1]=(i>>8)&0xFF; v[2]=(i>>16)&0xFF; v[3]=(i>>24)&0xFF; return v; };
    ExtendedField lat; lat.data_type = 33; lat.data = push_coord(a.coords->first);
    ExtendedField lon; lon.data_type = 34; lon.data = push_coord(a.coords->second);
    p.extensions.push_back(std::move(lat));
    p.extensions.push_back(std::move(lon));
    p.header.flags.extended = true;
  } else {
    p.header.type = PacketType::WeatherRequest;
    // area code: 6桁の数字文字列を20bitへ
    uint32_t ac = 0; for (char c : a.area.value()) if (c>='0'&&c<='9') ac = ac*10u + static_cast<uint32_t>(c-'0');
    p.header.area_code = ac & 0xFFFFFu;
  }

  return roundtrip(a.host, a.port, p);
}
