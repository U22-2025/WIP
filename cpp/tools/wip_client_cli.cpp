#include <iostream>
#include <string>
#include <vector>
#include <optional>
#include <cstring>

#include "wiplib/client/weather_client.hpp"
#include "wiplib/client/wip_client.hpp"

struct Args {
  std::string host = "127.0.0.1";
  uint16_t port = 4110;
  std::optional<std::pair<double,double>> coords;
  std::optional<std::string> area;
  wiplib::client::QueryOptions opt{};
  bool direct = false; // when true, bypass WeatherServer and send two requests
  // direct endpoints (optional overrides)
  std::optional<std::string> location_host;
  std::optional<uint16_t> location_port;
  std::optional<std::string> query_host;
  std::optional<uint16_t> query_port;
};

static void print_usage() {
  std::cout << "Usage:\n"
               "  wip_client_cli --host <HOST> --port <PORT> --coords <LAT> <LON> [flags]\n"
               "  wip_client_cli --host <HOST> --port <PORT> --area <AREA_CODE> [flags]\n"
               "  wip_client_cli --direct [--location-host H --location-port P --query-host H --query-port P] (--coords LAT LON | --area CODE) [flags]\n\n"
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
    } else if (a == "--direct") {
      args.direct = true;
    } else if (a == "--location-host") {
      const char* v = next("--location-host needs value"); if (!v) return false; args.location_host = std::string(v);
    } else if (a == "--location-port") {
      const char* v = next("--location-port needs value"); if (!v) return false; args.location_port = static_cast<uint16_t>(std::stoi(v));
    } else if (a == "--query-host") {
      const char* v = next("--query-host needs value"); if (!v) return false; args.query_host = std::string(v);
    } else if (a == "--query-port") {
      const char* v = next("--query-port needs value"); if (!v) return false; args.query_port = static_cast<uint16_t>(std::stoi(v));
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

  if (!args.direct) {
    // Proxy mode via WeatherServer
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

  // Direct mode: client sends 2 requests (Location -> Query)
  wiplib::client::ServerConfig cfg; // proxy config not used in direct mode
  wiplib::client::WipClient wcli(cfg, /*debug=*/false);
  if (args.location_host || args.location_port || args.query_host || args.query_port) {
    std::string lhost = args.location_host.value_or("127.0.0.1");
    uint16_t lport = args.location_port.value_or(4109);
    std::string qhost = args.query_host.value_or("127.0.0.1");
    uint16_t qport = args.query_port.value_or(4111);
    wcli.set_direct_endpoints(lhost, lport, qhost, qport);
  }

  auto to_weather_opts = [&](const wiplib::client::QueryOptions& qo){
    wiplib::client::WeatherOptions wo{};
    wo.weather = qo.weather; wo.temperature = qo.temperature; wo.precipitation_prob = qo.precipitation_prob; wo.alert = qo.alerts; wo.disaster = qo.disaster; wo.day = qo.day; return wo;
  };

  auto wopt = to_weather_opts(args.opt);
  wiplib::Result<wiplib::client::WeatherData> dres = [&]() {
    if (args.coords) return wcli.get_weather_by_coordinates(args.coords->first, args.coords->second, wopt, /*proxy=*/false);
    return wcli.get_weather_by_area_code(args.area.value(), wopt, /*proxy=*/false);
  }();

  if (!dres) {
    std::cerr << "error: " << dres.error().message() << "\n";
    return 1;
  }

  const auto& r2 = dres.value();
  std::cout << "Area Code: " << r2.area_code << "\n";
  if (r2.weather_code) std::cout << "Weather Code: " << *r2.weather_code << "\n";
  if (r2.temperature_c) std::cout << "Temperature(C): " << *r2.temperature_c << "\n";
  if (r2.precipitation_prob) std::cout << "precipitation_prob: " << *r2.precipitation_prob << "%\n";
  return 0;
}
