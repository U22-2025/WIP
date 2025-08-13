#include <iostream>
#include <string>
#include <vector>
#include <optional>
#include <cstring>

#include "wiplib/client/weather_client.hpp"

struct Args {
  std::string host = "127.0.0.1";
  uint16_t port = 4110;
  std::optional<std::pair<double,double>> coords;
  std::optional<std::string> area;
  wiplib::client::QueryOptions opt{};
};

static void print_usage() {
  std::cout << "Usage:\n"
               "  wip_client_cli --host <HOST> --port <PORT> --coords <LAT> <LON> [flags]\n"
               "  wip_client_cli --host <HOST> --port <PORT> --area <AREA_CODE> [flags]\n\n"
               "Flags:\n"
               "  --weather (default on), --no-weather\n"
               "  --temperature (default on), --no-temperature\n"
               "  --precipitation, --alerts, --disaster\n"
               "  --day <0-7>\n";
}

static bool parse_args(int argc, char** argv, Args& args) {
  for (int i = 1; i < argc; ++i) {
    std::string a = argv[i];
    auto next = [&](const char* err) -> const char* {
      if (i + 1 >= argc) { std::cerr << err << "\n"; return (const char*)nullptr; }
      return argv[++i];
    };
    if (a == "--host") {
      const char* v = next("--host needs value"); if (!v) return false; args.host = v;
    } else if (a == "--port") {
      const char* v = next("--port needs value"); if (!v) return false; args.port = static_cast<uint16_t>(std::stoi(v));
    } else if (a == "--coords") {
      const char* v1 = next("--coords needs lat"); if (!v1) return false; const char* v2 = next("--coords needs lon"); if (!v2) return false;
      args.coords = std::make_pair(std::stod(v1), std::stod(v2));
    } else if (a == "--area") {
      const char* v = next("--area needs value"); if (!v) return false; args.area = std::string(v);
    } else if (a == "--weather") {
      args.opt.weather = true;
    } else if (a == "--no-weather") {
      args.opt.weather = false;
    } else if (a == "--temperature") {
      args.opt.temperature = true;
    } else if (a == "--no-temperature") {
      args.opt.temperature = false;
    } else if (a == "--precipitation") {
      args.opt.precipitation_prob = true;
    } else if (a == "--alerts") {
      args.opt.alerts = true;
    } else if (a == "--disaster") {
      args.opt.disaster = true;
    } else if (a == "--day") {
      const char* v = next("--day needs value"); if (!v) return false; args.opt.day = static_cast<uint8_t>(std::stoi(v));
    } else if (a == "-h" || a == "--help") {
      print_usage(); return false;
    } else {
      std::cerr << "Unknown arg: " << a << "\n";
      return false;
    }
  }
  if (!(args.coords.has_value() ^ args.area.has_value())) {
    std::cerr << "Specify either --coords or --area\n";
    return false;
  }
  return true;
}

int main(int argc, char** argv) {
  Args args;
  if (!parse_args(argc, argv, args)) {
    print_usage();
    return 2;
  }

  wiplib::client::WeatherClient cli(args.host, args.port);
  wiplib::Result<wiplib::client::WeatherResult> res = [&]() {
    if (args.coords) {
      return cli.get_weather_by_coordinates(args.coords->first, args.coords->second, args.opt);
    } else {
      return cli.get_weather_by_area_code(args.area.value(), args.opt);
    }
  }();

  if (!res) {
    std::cerr << "error: " << res.error().message() << "\n";
    return 1;
  }

  const auto& r = res.value();
  std::cout << "Area Code: " << r.area_code << "\n";
  if (r.weather_code) std::cout << "Weather Code: " << *r.weather_code << "\n";
  if (r.temperature) std::cout << "Temperature(raw 2's): " << static_cast<int>(*r.temperature) << "\n";
  if (r.precipitation_prob) std::cout << "precipitation_prob: " << static_cast<int>(*r.precipitation_prob) << "%\n";
  return 0;
}
