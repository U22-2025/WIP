#pragma once

#include <cstdint>
#include <optional>
#include <string>
#include <string_view>
#include <vector>

#include "wiplib/expected.hpp"
#include "wiplib/error.hpp"
#include "wiplib/client/weather_client.hpp"
#include "wiplib/client/auth_config.hpp"
#include "wiplib/packet/packet.hpp"

namespace wiplib::client {

struct ServerConfig {
  std::string host = WeatherClient::default_host();
  uint16_t port = WeatherClient::default_port(); // Weather Server (proxy)
};

struct ClientState {
  std::optional<double> latitude{};
  std::optional<double> longitude{};
  std::optional<std::string> area_code{}; // keep as string like Python
};

struct WeatherOptions {
  bool weather = true;
  bool temperature = true;
  bool precipitation_prob = true;
  bool alert = false;
  bool disaster = false;
  uint8_t day = 0;
};

struct WeatherData {
  std::string area_code; // 6-digit string
  std::optional<uint16_t> weather_code{};
  std::optional<int> temperature_c{}; // Celsius
  std::optional<int> precipitation_prob{};
  std::optional<std::vector<std::string>> alerts{};
  std::optional<std::vector<std::string>> disasters{};
};

class WipClient {
public:
  explicit WipClient(ServerConfig cfg = {}, bool debug = false);
  static WipClient from_env(bool debug = false);
  ~WipClient();

  void set_coordinates(double latitude, double longitude);
  void set_area_code(std::string area_code);
  const ClientState& state() const noexcept { return state_; }

  void update_server(std::string host, uint16_t port);
  void set_direct_endpoints(std::string location_host, uint16_t location_port,
                            std::string query_host, uint16_t query_port);
  void close();
  void set_auth_config(const AuthConfig& cfg);

  // High-level API (proxy=false -> direct mode)
  wiplib::Result<WeatherData> get_weather(const WeatherOptions& opt, bool proxy = false) noexcept;
  wiplib::Result<WeatherData> get_weather_by_coordinates(double lat, double lon, const WeatherOptions& opt, bool proxy = false) noexcept;
  wiplib::Result<WeatherData> get_weather_by_area_code(std::string_view area_code, const WeatherOptions& opt, bool proxy = false) noexcept;

private:
  // helpers
  wiplib::Result<std::string> resolve_area_code_direct(double lat, double lon, const WeatherOptions& opt) noexcept;
  wiplib::Result<WeatherData> query_weather_direct(std::string_view area_code, const WeatherOptions& opt) noexcept;

  // UDP helper used by direct mode
  wiplib::Result<wiplib::proto::Packet> roundtrip_udp(const std::string& host, uint16_t port, const wiplib::proto::Packet& req) noexcept;

  // members
  ServerConfig cfg_{};
  ClientState state_{};
  bool debug_ = false;
  WeatherClient proxy_client_;
  AuthConfig auth_cfg_{};

  // direct mode endpoints (default localhost)
  std::string location_host_ = "127.0.0.1"; // LOCATION_RESOLVER_HOST
  uint16_t location_port_ = 4109;
  std::string query_host_ = "127.0.0.1";    // QUERY_GENERATOR_HOST
  uint16_t query_port_ = 4111;
};

} // namespace wiplib::client
