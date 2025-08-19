#include <iostream>
#include <string>
#include <vector>
#include <optional>
#include <cstring>
#include <iomanip>

#include "wiplib/client/client.hpp"
#include "wiplib/client/auth_config.hpp"

enum class ClientMode {
    Weather,
    Report
};

struct Args {
    // 共通設定
    std::string host = "127.0.0.1";
    uint16_t port = 4110;  // デフォルトは天気サーバー
    ClientMode mode = ClientMode::Weather;
    bool debug = false;
    
    // 天気データ取得用
    std::optional<std::pair<double,double>> coords;
    std::optional<std::string> area;
    bool proxy = false;
    bool weather = true;
    bool temperature = true;
    bool precipitation = true;
    bool alerts = false;
    bool disaster = false;
    uint8_t day = 0;
    
    // レポート送信用
    std::optional<int> weather_code;
    std::optional<float> temp_value;
    std::optional<int> precipitation_prob;
    std::vector<std::string> alert_list;
    std::vector<std::string> disaster_list;
    
    // 認証
    std::optional<bool> auth_enabled;
    std::optional<std::string> auth_weather;
    std::optional<std::string> auth_location;
    std::optional<std::string> auth_query;
    std::optional<std::string> auth_report;
};

static void print_usage() {
    std::cout << R"(Usage:
  unified_client_cli [mode] [common_options] [mode_specific_options]

MODES:
  weather    Weather data retrieval (default)
  report     Sensor data reporting

COMMON OPTIONS:
  --host <HOST>         Server host (default: 127.0.0.1)
  --port <PORT>         Server port (default: 4110 for weather, 4112 for report)
  --debug               Enable debug output
  --help, -h            Show this help

WEATHER MODE OPTIONS:
  --coords <LAT> <LON>  Use coordinates for weather query
  --area <AREA_CODE>    Use area code for weather query (6-digit string)
  --proxy               Use weather server proxy mode
  --weather             Include weather data (default: on)
  --no-weather          Exclude weather data
  --temperature         Include temperature (default: on)
  --no-temperature      Exclude temperature
  --precipitation       Include precipitation (default: on)
  --no-precipitation    Exclude precipitation
  --alerts              Include alerts (default: off)
  --disaster            Include disaster info (default: off)
  --day <0-7>           Day offset (default: 0)

REPORT MODE OPTIONS:
  --area <AREA_CODE>         Area code for report (required)
  --weather-code <CODE>      Weather code (1-4)
  --temp <CELSIUS>           Temperature in Celsius
  --precipitation-prob <0-100> Precipitation probability percentage
  --alert "<MESSAGE>"        Add alert message (can be used multiple times)
  --disaster "<MESSAGE>"     Add disaster message (can be used multiple times)

AUTHENTICATION OPTIONS:
  --auth-enabled            Enable authentication
  --no-auth-enabled         Disable authentication
  --auth-weather <PASS>     Weather service passphrase
  --auth-location <PASS>    Location service passphrase
  --auth-query <PASS>       Query service passphrase
  --auth-report <PASS>      Report service passphrase

EXAMPLES:
  # Weather data retrieval by coordinates
  unified_client_cli weather --coords 35.6762 139.6503 --temperature --precipitation

  # Weather data retrieval by area code via proxy
  unified_client_cli weather --proxy --host 127.0.0.1 --port 4110 --area 130010

  # Sensor data reporting
  unified_client_cli report --host 127.0.0.1 --port 4112 --area 130010 --weather-code 1 --temp 25.5 --precipitation-prob 30

  # Report with alerts and disaster info
  unified_client_cli report --area 130010 --weather-code 2 --alert "強風注意報" --disaster "地震情報"

  # With authentication
  unified_client_cli weather --auth-enabled --auth-query "secret123" --area 130010
  unified_client_cli report --auth-enabled --auth-report "reportsecret" --area 130010 --weather-code 1
)";
}

static bool parse_args(int argc, char** argv, Args& args) {
    int i = 1;
    
    // モード判定
    if (i < argc) {
        std::string mode_arg = argv[i];
        if (mode_arg == "weather") {
            args.mode = ClientMode::Weather;
            i++;
        } else if (mode_arg == "report") {
            args.mode = ClientMode::Report;
            args.port = 4112;  // レポートサーバーのデフォルトポート
            i++;
        } else if (mode_arg.starts_with("--") || mode_arg == "-h") {
            // オプションから開始の場合はデフォルト（weather）モード
            args.mode = ClientMode::Weather;
        } else {
            std::cerr << "Unknown mode: " << mode_arg << "\n";
            return false;
        }
    }
    
    auto next = [&](const char* err) -> const char* {
        if (i + 1 >= argc) { std::cerr << err << "\n"; return nullptr; }
        return argv[++i];
    };
    
    for (; i < argc; ++i) {
        std::string a = argv[i];
        
        if (a == "--host") {
            const char* v = next("--host needs value"); if (!v) return false; args.host = v;
        } else if (a == "--port") {
            const char* v = next("--port needs value"); if (!v) return false; args.port = static_cast<uint16_t>(std::stoi(v));
        } else if (a == "--debug") {
            args.debug = true;
        } else if (a == "--coords") {
            const char* v1 = next("--coords needs lat"); if (!v1) return false; 
            const char* v2 = next("--coords needs lon"); if (!v2) return false;
            args.coords = std::make_pair(std::stod(v1), std::stod(v2));
        } else if (a == "--area") {
            const char* v = next("--area needs value"); if (!v) return false; args.area = std::string(v);
        } else if (a == "--proxy") {
            args.proxy = true;
        } else if (a == "--weather") {
            args.weather = true;
        } else if (a == "--no-weather") {
            args.weather = false;
        } else if (a == "--temperature") {
            args.temperature = true;
        } else if (a == "--no-temperature") {
            args.temperature = false;
        } else if (a == "--precipitation") {
            args.precipitation = true;
        } else if (a == "--no-precipitation") {
            args.precipitation = false;
        } else if (a == "--alerts") {
            args.alerts = true;
        } else if (a == "--disaster") {
            args.disaster = true;
        } else if (a == "--day") {
            const char* v = next("--day needs value"); if (!v) return false; 
            args.day = static_cast<uint8_t>(std::stoi(v));
        } else if (a == "--weather-code") {
            const char* v = next("--weather-code needs value"); if (!v) return false;
            args.weather_code = std::stoi(v);
        } else if (a == "--temp") {
            const char* v = next("--temp needs value"); if (!v) return false;
            args.temp_value = std::stof(v);
        } else if (a == "--precipitation-prob") {
            const char* v = next("--precipitation-prob needs value"); if (!v) return false;
            args.precipitation_prob = std::stoi(v);
        } else if (a == "--alert") {
            const char* v = next("--alert needs value"); if (!v) return false;
            args.alert_list.push_back(std::string(v));
        } else if (a == "--disaster") {
            const char* v = next("--disaster needs value"); if (!v) return false;
            args.disaster_list.push_back(std::string(v));
        } else if (a == "--auth-enabled") {
            args.auth_enabled = true;
        } else if (a == "--no-auth-enabled") {
            args.auth_enabled = false;
        } else if (a == "--auth-weather") {
            const char* v = next("--auth-weather needs value"); if (!v) return false; 
            args.auth_weather = std::string(v);
        } else if (a == "--auth-location") {
            const char* v = next("--auth-location needs value"); if (!v) return false; 
            args.auth_location = std::string(v);
        } else if (a == "--auth-query") {
            const char* v = next("--auth-query needs value"); if (!v) return false; 
            args.auth_query = std::string(v);
        } else if (a == "--auth-report") {
            const char* v = next("--auth-report needs value"); if (!v) return false; 
            args.auth_report = std::string(v);
        } else if (a == "-h" || a == "--help") {
            print_usage(); return false;
        } else {
            std::cerr << "Unknown arg: " << a << "\n";
            return false;
        }
    }
    
    // バリデーション
    if (args.mode == ClientMode::Weather) {
        if (!(args.coords.has_value() ^ args.area.has_value())) {
            std::cerr << "Weather mode: Specify either --coords or --area\n";
            return false;
        }
    } else if (args.mode == ClientMode::Report) {
        if (!args.area.has_value()) {
            std::cerr << "Report mode: --area is required\n";
            return false;
        }
    }
    
    return true;
}

static wiplib::client::AuthConfig build_auth_config(const Args& args) {
    wiplib::client::AuthConfig auth_cfg = wiplib::client::AuthConfig::from_env();
    if (args.auth_enabled.has_value()) auth_cfg.enabled = args.auth_enabled.value();
    if (args.auth_weather.has_value()) auth_cfg.weather = args.auth_weather.value();
    if (args.auth_location.has_value()) auth_cfg.location = args.auth_location.value();
    if (args.auth_query.has_value()) auth_cfg.query = args.auth_query.value();
    if (args.auth_report.has_value()) auth_cfg.report = args.auth_report.value();
    return auth_cfg;
}

static int run_weather_mode(const Args& args) {
    std::cout << "=== Weather Data Retrieval Mode ===" << std::endl;
    
    try {
        auto client = std::make_unique<wiplib::client::Client>(
            args.host, args.port, std::nullopt, args.debug
        );
        
        // 認証設定
        auto auth_cfg = build_auth_config(args);
        client->set_auth_config(auth_cfg);
        if (args.debug) {
            std::cout << "Auth enabled: " << (auth_cfg.enabled ? "true" : "false") << std::endl;
        }
        
        // 座標またはエリアコード設定
        if (args.coords.has_value()) {
            client->set_coordinates(args.coords->first, args.coords->second);
            if (args.debug) {
                std::cout << "Using coordinates: " << args.coords->first << ", " << args.coords->second << std::endl;
            }
        } else {
            client->set_area_code(args.area.value());
            if (args.debug) {
                std::cout << "Using area code: " << args.area.value() << std::endl;
            }
        }
        
        // 天気データ取得
        auto result = client->get_weather(
            args.weather, args.temperature, args.precipitation,
            args.alerts, args.disaster, args.day, args.proxy
        );
        
        if (!result.has_value()) {
            std::cerr << "Weather query failed: " << result.error().message() << std::endl;
            return 1;
        }
        
        const auto& weather_data = result.value();
        std::cout << "\n=== Weather Data Results ===" << std::endl;
        std::cout << "Area Code: " << weather_data.area_code << std::endl;
        
        if (weather_data.weather_code.has_value()) {
            std::cout << "Weather Code: " << weather_data.weather_code.value() << std::endl;
        }
        if (weather_data.temperature_c.has_value()) {
            std::cout << "Temperature: " << std::fixed << std::setprecision(1) 
                      << weather_data.temperature_c.value() << "°C" << std::endl;
        }
        if (weather_data.precipitation_prob.has_value()) {
            std::cout << "Precipitation Probability: " << weather_data.precipitation_prob.value() << "%" << std::endl;
        }
        
        std::cout << "✓ Weather data retrieval completed successfully" << std::endl;
        return 0;
        
    } catch (const std::exception& e) {
        std::cerr << "Error: " << e.what() << std::endl;
        return 1;
    }
}

static int run_report_mode(const Args& args) {
    std::cout << "=== Sensor Data Report Mode ===" << std::endl;
    
    try {
        auto client = std::make_unique<wiplib::client::Client>(
            args.host, args.port, std::nullopt, args.debug
        );
        
        // 認証設定
        auto auth_cfg = build_auth_config(args);
        client->set_auth_config(auth_cfg);
        if (args.debug) {
            std::cout << "Auth enabled: " << (auth_cfg.enabled ? "true" : "false") << std::endl;
        }
        
        // センサーデータ設定
        std::optional<std::vector<std::string>> alerts_opt;
        std::optional<std::vector<std::string>> disasters_opt;
        
        if (!args.alert_list.empty()) {
            alerts_opt = args.alert_list;
        }
        if (!args.disaster_list.empty()) {
            disasters_opt = args.disaster_list;
        }
        
        client->set_sensor_data(
            args.area.value(),
            args.weather_code,
            args.temp_value,
            args.precipitation_prob,
            alerts_opt,
            disasters_opt
        );
        
        if (args.debug) {
            std::cout << "Set sensor data:" << std::endl;
            std::cout << "  Area: " << args.area.value() << std::endl;
            if (args.weather_code.has_value()) {
                std::cout << "  Weather Code: " << args.weather_code.value() << std::endl;
            }
            if (args.temp_value.has_value()) {
                std::cout << "  Temperature: " << args.temp_value.value() << "°C" << std::endl;
            }
            if (args.precipitation_prob.has_value()) {
                std::cout << "  Precipitation Probability: " << args.precipitation_prob.value() << "%" << std::endl;
            }
            if (!args.alert_list.empty()) {
                std::cout << "  Alerts: ";
                for (const auto& alert : args.alert_list) {
                    std::cout << "\"" << alert << "\" ";
                }
                std::cout << std::endl;
            }
            if (!args.disaster_list.empty()) {
                std::cout << "  Disasters: ";
                for (const auto& disaster : args.disaster_list) {
                    std::cout << "\"" << disaster << "\" ";
                }
                std::cout << std::endl;
            }
        }
        
        // レポート送信
        auto result = client->send_report_data();
        
        if (!result.has_value()) {
            std::cerr << "Report sending failed: " << result.error().message() << std::endl;
            return 1;
        }
        
        const auto& report_result = result.value();
        std::cout << "\n=== Report Results ===" << std::endl;
        std::cout << "Status: " << report_result.type << std::endl;
        std::cout << "Success: " << (report_result.success ? "true" : "false") << std::endl;
        std::cout << "Response Time: " << std::fixed << std::setprecision(2) 
                  << report_result.response_time_ms << "ms" << std::endl;
        
        if (report_result.area_code.has_value()) {
            std::cout << "Area Code: " << report_result.area_code.value() << std::endl;
        }
        if (report_result.packet_id.has_value()) {
            std::cout << "Packet ID: " << report_result.packet_id.value() << std::endl;
        }
        
        std::cout << "✓ Sensor data report completed successfully" << std::endl;
        return 0;
        
    } catch (const std::exception& e) {
        std::cerr << "Error: " << e.what() << std::endl;
        return 1;
    }
}

int main(int argc, char** argv) {
    Args args;
    if (!parse_args(argc, argv, args)) {
        return 2;
    }
    
    switch (args.mode) {
        case ClientMode::Weather:
            return run_weather_mode(args);
        case ClientMode::Report:
            return run_report_mode(args);
        default:
            std::cerr << "Invalid mode" << std::endl;
            return 1;
    }
}