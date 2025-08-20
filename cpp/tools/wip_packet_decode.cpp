#include <iostream>
#include <fstream>
#include <vector>
#include <string>
#include <cstdint>
#include <filesystem>
#include <iomanip>

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

static const char* type_name(PacketType t) {
  switch (t) {
    case PacketType::CoordinateRequest: return "CoordinateRequest";
    case PacketType::CoordinateResponse: return "CoordinateResponse";
    case PacketType::WeatherRequest: return "WeatherRequest";
    case PacketType::WeatherResponse: return "WeatherResponse";
    default: return "Unknown";
  }
}

int main(int argc, char** argv) {
  if (argc < 2) { std::cerr << "Usage: wip_packet_decode <file>\n"; return 2; }
  std::vector<std::uint8_t> bytes;
  if (!read_all(argv[1], bytes)) { std::cerr << "failed to read file\n"; return 1; }
  auto res = decode_packet(bytes);
  if (!res) { std::cerr << "decode error: " << res.error().message() << "\n"; return 1; }
  const Packet& p = res.value();
  // JSON output
  std::cout << "{\n";
  std::cout << "  \"version\": " << int(p.header.version) << ",\n";
  std::cout << "  \"packet_id\": " << p.header.packet_id << ",\n";
  std::cout << "  \"type\": \"" << type_name(p.header.type) << "\",\n";
  std::cout << "  \"area_code\": \"" << std::setw(6) << std::setfill('0') << p.header.area_code << "\",\n";
  std::cout << "  \"flags\": {\n"
            << "    \"weather\": " << (p.header.flags.weather?"true":"false") << ",\n"
            << "    \"temperature\": " << (p.header.flags.temperature?"true":"false") << ",\n"
            << "    \"precipitation\": " << (p.header.flags.precipitation?"true":"false") << ",\n"
            << "    \"alert\": " << (p.header.flags.alert?"true":"false") << ",\n"
            << "    \"disaster\": " << (p.header.flags.disaster?"true":"false") << "\n"
            << "  },\n";
  std::cout << "  \"day\": " << int(p.header.day) << ",\n";
  std::cout << "  \"timestamp\": " << p.header.timestamp << ",\n";
  if (p.response_fields.has_value()) {
    const auto& rf = p.response_fields.value();
    std::cout << "  \"response\": {\n"
              << "    \"weather_code\": " << rf.weather_code << ",\n"
              << "    \"temperature_raw\": " << int(rf.temperature) << ",\n"
              << "    \"precipitation_prob\": " << int(rf.precipitation_prob) << "\n"
              << "  },\n";
  }
  std::cout << "  \"extensions\": [";
  for (size_t i = 0; i < p.extensions.size(); ++i) {
    const auto& e = p.extensions[i];
    std::cout << (i==0?"\n":"\n,") << "    { \"type_id\": " << int(e.data_type);
    if (e.data_type == 33 || e.data_type == 34) {
      if (e.data.size() == 4) {
        int32_t ival = static_cast<int32_t>(
          (e.data[0]) | (e.data[1]<<8) | (e.data[2]<<16) | (e.data[3]<<24));
        double coord = static_cast<double>(ival) / 1000000.0;
        std::cout << ", \"value\": " << coord;
      }
    } else {
      std::cout << ", \"size\": " << e.data.size();
    }
    std::cout << " }";
  }
  if (!p.extensions.empty()) std::cout << "\n";
  std::cout << "  ]\n";
  std::cout << "}\n";
  return 0;
}
