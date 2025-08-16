#include <iostream>
#include <string>
#include <optional>
#include "wiplib/client/async_weather_client.hpp"

using namespace wiplib::client;

static void usage() {
  std::cout << "Usage:\n"
               "  async_weather_cli --host <HOST> --port <PORT> --area <AREA>\n"
               "  async_weather_cli --host <HOST> --port <PORT> --coords <LAT> <LON>\n";
}

int main(int argc, char** argv) {
  std::string host = "127.0.0.1"; uint16_t port = 4110; std::optional<std::string> area; std::optional<std::pair<double,double>> coords;
  for (int i=1;i<argc;++i) {
    std::string a = argv[i];
    auto next = [&](const char* err)->const char*{ if (i+1>=argc){ std::cerr<<err<<"\n"; return (const char*)nullptr;} return (const char*)argv[++i]; };
    if (a=="--host") { const char* v=next("--host needs value"); if(!v) return 2; host=v; }
    else if (a=="--port") { const char* v=next("--port needs value"); if(!v) return 2; port=static_cast<uint16_t>(std::stoi(v)); }
    else if (a=="--area") { const char* v=next("--area needs value"); if(!v) return 2; area=std::string(v); }
    else if (a=="--coords") { const char* v1=next("--coords lat"); if(!v1) return 2; const char* v2=next("--coords lon"); if(!v2) return 2; coords=std::make_pair(std::stod(v1), std::stod(v2)); }
    else if (a=="-h"||a=="--help") { usage(); return 0; }
    else { std::cerr << "Unknown arg: "<<a<<"\n"; return 2; }
  }
  if (!(area.has_value() ^ coords.has_value())) { usage(); return 2; }
  AsyncWeatherClient cli(host, port, 32);
  cli.set_debug_enabled(true);
  if (area) {
    uint32_t ac=0; for (char c:*area) if (c>='0'&&c<='9') ac = ac*10u + static_cast<uint32_t>(c-'0');
    auto r = cli.get_weather_async(ac, std::chrono::milliseconds{5000});
    auto wd = r.future.get();
    std::cout << "Area:"<<wd.area_code<<" weather:"<<wd.weather_code<<" temp(raw):"<<int(wd.temperature)
              <<" pop:"<<int(wd.precipitation_prob)<<" alerts:"<<wd.alerts.size()<<" disasters:"<<wd.disasters.size()<<"\n";
  } else {
    auto r = cli.get_weather_by_coordinates_async(static_cast<float>(coords->first), static_cast<float>(coords->second), std::chrono::milliseconds{5000});
    auto wd = r.future.get();
    std::cout << "Area:"<<wd.area_code<<" weather:"<<wd.weather_code<<" temp(raw):"<<int(wd.temperature)
              <<" pop:"<<int(wd.precipitation_prob)<<" alerts:"<<wd.alerts.size()<<" disasters:"<<wd.disasters.size()<<"\n";
  }
  return 0;
}
