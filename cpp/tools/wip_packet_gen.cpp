#include <iostream>
#include <fstream>
#include <string>
#include <vector>
#include <optional>
#include <chrono>
#include <random>

#include "wiplib/packet/codec.hpp"

using namespace wiplib::proto;

struct GenArgs {
  std::string type; // "query" or "location"
  std::optional<std::string> area; // for query
  std::optional<std::pair<double,double>> coords; // for location
  uint16_t packet_id = 0x123;
  std::optional<uint64_t> timestamp;
  bool weather = true;
  bool temperature = true;
  bool precipitation = true;
  bool alert = false;
  bool disaster = false;
  uint8_t day = 0;
  std::string out;
};

static void usage() {
  std::cout << "Usage: wip_packet_gen --type <query|location> [--area <code> | --coords <lat> <lon>] "
               "[--packet-id N] [--timestamp N] [--day N] [--no-weather] [--no-temperature] [--no-precipitation] [--alert] [--disaster] --out <file>\n";
}

static bool parse_args(int argc, char** argv, GenArgs& args) {
  int i = 1;
  auto next = [&](const char* err) -> const char* {
    if (i + 1 >= argc) { std::cerr << err << "\n"; return static_cast<const char*>(nullptr); }
    return argv[++i];
  };
  for (; i < argc; ++i) {
    std::string a = argv[i];
    if (a == "--type") { const char* v = next("--type needs value"); if (!v) return false; args.type = v; }
    else if (a == "--area") { const char* v = next("--area needs value"); if (!v) return false; args.area = std::string(v); }
    else if (a == "--coords") { const char* v1 = next("--coords needs lat"); if (!v1) return false; const char* v2 = next("--coords needs lon"); if (!v2) return false; args.coords = std::make_pair(std::stod(v1), std::stod(v2)); }
    else if (a == "--packet-id") { const char* v = next("--packet-id needs value"); if (!v) return false; args.packet_id = static_cast<uint16_t>(std::stoul(v, nullptr, 0) & 0x0FFFu); }
    else if (a == "--timestamp") { const char* v = next("--timestamp needs value"); if (!v) return false; args.timestamp = static_cast<uint64_t>(std::stoull(v)); }
    else if (a == "--day") { const char* v = next("--day needs value"); if (!v) return false; args.day = static_cast<uint8_t>(std::stoul(v)); }
    else if (a == "--no-weather") { args.weather = false; }
    else if (a == "--no-temperature") { args.temperature = false; }
    else if (a == "--no-precipitation") { args.precipitation = false; }
    else if (a == "--alert") { args.alert = true; }
    else if (a == "--disaster") { args.disaster = true; }
    else if (a == "--out") { const char* v = next("--out needs value"); if (!v) return false; args.out = v; }
    else if (a == "-h" || a == "--help") { usage(); return false; }
    else { std::cerr << "Unknown arg: " << a << "\n"; return false; }
  }
  if (args.type != "query" && args.type != "location") { std::cerr << "--type must be query or location\n"; return false; }
  if (args.type == "query" && !args.area) { std::cerr << "--area required for query\n"; return false; }
  if (args.type == "location" && !args.coords) { std::cerr << "--coords required for location\n"; return false; }
  if (args.out.empty()) { std::cerr << "--out required\n"; return false; }
  return true;
}

static std::vector<std::uint8_t> encode_query(const GenArgs& g) {
  Packet p{};
  p.header.version = 1;
  p.header.packet_id = g.packet_id;
  p.header.type = PacketType::WeatherRequest;
  p.header.flags.weather = g.weather;
  p.header.flags.temperature = g.temperature;
  p.header.flags.precipitation = g.precipitation;
  p.header.flags.alert = g.alert;
  p.header.flags.disaster = g.disaster;
  p.header.day = g.day;
  p.header.timestamp = g.timestamp.value_or(static_cast<uint64_t>(std::chrono::duration_cast<std::chrono::seconds>(
    std::chrono::system_clock::now().time_since_epoch()).count()));
  // parse area code string to int
  uint32_t ac = 0; for (char c : *g.area) if (c>='0'&&c<='9') ac = ac*10u + static_cast<uint32_t>(c-'0');
  p.header.area_code = ac & 0xFFFFFu;
  auto enc = encode_packet(p);
  if (!enc) return {};
  return enc.value();
}

static std::vector<std::uint8_t> encode_location(const GenArgs& g) {
  Packet p{};
  p.header.version = 1;
  p.header.packet_id = g.packet_id;
  p.header.type = PacketType::CoordinateRequest;
  p.header.flags.weather = g.weather;
  p.header.flags.temperature = g.temperature;
  p.header.flags.precipitation = g.precipitation;
  p.header.flags.alert = g.alert;
  p.header.flags.disaster = g.disaster;
  p.header.flags.extended = true;
  p.header.day = g.day;
  p.header.timestamp = g.timestamp.value_or(static_cast<uint64_t>(std::chrono::duration_cast<std::chrono::seconds>(
    std::chrono::system_clock::now().time_since_epoch()).count()));
  p.header.area_code = 0;
  // push coords ext: ids 33, 34; int32 LE scaled 1e6
  auto push_coord = [](double d){
    std::vector<std::uint8_t> v(4);
    int32_t i = static_cast<int32_t>(d * 1000000.0);
    v[0] = static_cast<uint8_t>(i & 0xFF);
    v[1] = static_cast<uint8_t>((i >> 8) & 0xFF);
    v[2] = static_cast<uint8_t>((i >> 16) & 0xFF);
    v[3] = static_cast<uint8_t>((i >> 24) & 0xFF);
    return v;
  };
  ExtendedField lat; lat.data_type = 33; lat.data = push_coord(g.coords->first);
  ExtendedField lon; lon.data_type = 34; lon.data = push_coord(g.coords->second);
  p.extensions.push_back(std::move(lat));
  p.extensions.push_back(std::move(lon));
  auto enc = encode_packet(p);
  if (!enc) return {};
  return enc.value();
}

int main(int argc, char** argv) {
  GenArgs g;
  if (!parse_args(argc, argv, g)) return 2;
  std::vector<std::uint8_t> data;
  if (g.type == "query") data = encode_query(g);
  else data = encode_location(g);
  if (data.empty()) { std::cerr << "encode failed\n"; return 1; }
  std::ofstream ofs(g.out, std::ios::binary);
  ofs.write(reinterpret_cast<const char*>(data.data()), static_cast<std::streamsize>(data.size()));
  std::cout << "wrote " << data.size() << " bytes to " << g.out << "\n";
  return 0;
}
