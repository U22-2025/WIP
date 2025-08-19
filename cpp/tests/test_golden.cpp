#include <cassert>
#include <cstdint>
#include <fstream>
#include <vector>
#include <string>
#include <filesystem>

#include "wiplib/packet/codec.hpp"

using namespace wiplib::proto;

static bool read_all(const std::filesystem::path& p, std::vector<std::uint8_t>& out) {
  std::ifstream ifs(p, std::ios::binary);
  if (!ifs) return false;
  ifs.seekg(0, std::ios::end);
  auto n = ifs.tellg();
  ifs.seekg(0, std::ios::beg);
  out.resize(static_cast<size_t>(n));
  if (n > 0) ifs.read(reinterpret_cast<char*>(out.data()), n);
  return true;
}

int main() {
  namespace fs = std::filesystem;
  fs::path dir = fs::path("dist")/"golden";
  if (!fs::exists(dir)) {
    // nothing to do
    return 0;
  }

  for (auto& entry : fs::directory_iterator(dir)) {
    if (!entry.is_regular_file()) continue;
    std::vector<std::uint8_t> bytes;
    if (!read_all(entry.path(), bytes)) continue;
    auto pkt = decode_packet(bytes);
    assert(pkt);
    // Basic sanity: checksum verified in decode_header
    const Packet& p = pkt.value();
    assert(p.header.version == 1);
    assert(p.header.type == PacketType::CoordinateRequest
           || p.header.type == PacketType::WeatherRequest
           || p.header.type == PacketType::CoordinateResponse
           || p.header.type == PacketType::WeatherResponse);
  }
  return 0;
}
