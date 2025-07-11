#include <iostream>
#include <chrono>
#include "common/clients/WeatherClient.hpp"
#include "common/clients/LocationClient.hpp"
#include "common/clients/QueryClient.hpp"
#include "common/packet/types/LocationPacket.hpp"

using namespace wip::clients;
using namespace wip::packet;

int main(int argc, char* argv[]) {
    bool use_coord = false;
    bool use_proxy = false;
    bool debug = false;
    for (int i = 1; i < argc; ++i) {
        std::string arg = argv[i];
        if (arg == "--coord") use_coord = true;
        else if (arg == "--proxy") use_proxy = true;
        else if (arg == "--debug") debug = true;
    }

    if (use_proxy)
        std::cout << "Weather Client Example - Via Weather Server (Proxy Mode)\n";
    else
        std::cout << "Weather Client Example - Direct Communication\n";
    std::cout << std::string(60, '=') << std::endl;

    PacketIDGenerator12Bit pidg;

    if (use_coord) {
        if (use_proxy) {
            std::cout << "\n1. Coordinate-based request via Weather Server (Proxy)\n";
            std::cout << std::string(50, '-') << std::endl;

            auto start = std::chrono::steady_clock::now();
            WeatherClient client{"", 0, debug};

            auto req = LocationRequest::create_coordinate_lookup(
                35.6895, 139.6917, pidg.next_id(), true, true, true, true, true);

            // WeatherClient には直接 LocationRequest を送るAPIが未実装のため、
            // ここでは LocationClient でエリアコードを取得してから WeatherClient
            // で天気データを取得する簡易手順で代用する。
            LocationClient locClient{"", 0, debug};
            auto [area, _] = locClient.get_location_data(35.6895, 139.6917);
            auto result = client.get_weather_data(area, true, true, true, true, true);

            if (!result.empty() && result.find("error") == result.end()) {
                auto elapsed = std::chrono::steady_clock::now() - start;
                std::cout << "\n\xE2\x9C\x93 Request successful via Weather Server! (Execution time: "
                          << std::chrono::duration<double>(elapsed).count() << "s)\n";
                std::cout << "=== Received packet content ===" << std::endl;
                for (auto& [k, v] : result) {
                    std::cout << "  " << k << ": " << v << std::endl;
                }
                std::cout << "==============================" << std::endl;
            } else {
                std::cout << "\n\xE2\x9C\x97 Request failed" << std::endl;
            }
        } else {
            std::cout << "\n1. Direct coordinate-based request (LocationClient + QueryClient)\n";
            std::cout << std::string(65, '-') << std::endl;

            auto start = std::chrono::steady_clock::now();
            LocationClient locClient{"", 0, debug, 60};
            QueryClient queryClient{"", 0, debug};
            if (debug)
                std::cout << "QueryClient connecting to " << queryClient.host() << ":" << queryClient.port() << std::endl;

            std::cout << "Step 1: Getting area code from coordinates..." << std::endl;
            auto stats_before = locClient.get_cache_stats();
            std::cout << "Cache stats before request: cache_size=" << stats_before["cache_size"] << std::endl;

            auto [area, _] = locClient.get_location_data(35.6895, 139.6917, true);
            auto stats_after = locClient.get_cache_stats();
            std::cout << "Cache stats after request: cache_size=" << stats_after["cache_size"] << std::endl;

            if (!area.empty()) {
                std::cout << "\xE2\x9C\x93 Area code obtained: " << area << std::endl;

                std::cout << "\n--- Cache Test: Getting same coordinates again ---" << std::endl;
                auto [area2, _2] = locClient.get_location_data(35.6895, 139.6917, true);
                if (!area2.empty()) {
                    std::cout << "\xE2\x9C\x93 Second request - Area code: " << area2 << std::endl;
                } else {
                    std::cout << "\n\xE2\x9C\x97 Second request failed" << std::endl;
                }

                std::cout << "\nStep 2: Getting weather data..." << std::endl;
                auto result = queryClient.get_weather_data(area, true, true, true, true, true);
                if (!result.empty()) {
                    auto elapsed = std::chrono::steady_clock::now() - start;
                    std::cout << "\n\xE2\x9C\x93 Direct request successful! (Execution time: "
                              << std::chrono::duration<double>(elapsed).count() << "s)\n";
                    std::cout << "=== Received weather data ===" << std::endl;
                    result["latitude"] = "35.6895";
                    result["longitude"] = "139.6917";
                    for (auto& [k, v] : result) {
                        std::cout << "  " << k << ": " << v << std::endl;
                    }
                    std::cout << "==============================" << std::endl;
                } else {
                    std::cout << "\n\xE2\x9C\x97 Weather data request failed" << std::endl;
                }
            } else {
                std::cout << "\n\xE2\x9C\x97 Failed to get area code from coordinates" << std::endl;
            }
        }
    } else {
        if (use_proxy) {
            std::cout << "\n1. Area code request via Weather Server (Proxy)\n";
            std::cout << std::string(45, '-') << std::endl;

            auto start = std::chrono::steady_clock::now();
            WeatherClient client{"", 0, debug};
            auto result = client.get_weather_data("460010", true, true, true, true, true);

            if (!result.empty() && result.find("error") == result.end()) {
                auto elapsed = std::chrono::steady_clock::now() - start;
                std::cout << "\n\xE2\x9C\x93 Success via Weather Server! (Execution time: "
                          << std::chrono::duration<double,std::milli>(elapsed).count() << "ms)\n";
                for (auto& [k, v] : result) {
                    std::cout << "  " << k << ": " << v << std::endl;
                }
            } else {
                std::cout << "\n\xE2\x9C\x97 Failed to get weather data via Weather Server" << std::endl;
                if (debug && result.find("error") != result.end())
                    std::cout << "  Error: " << result["error"] << std::endl;
            }
        } else {
            std::cout << "\n1. Direct area code request (QueryClient)\n";
            std::cout << std::string(40, '-') << std::endl;

            auto start = std::chrono::steady_clock::now();
            QueryClient queryClient{"", 0, debug};
            if (debug)
                std::cout << "QueryClient connecting to " << queryClient.host() << ":" << queryClient.port() << std::endl;
            auto result = queryClient.get_weather_data("460010", true, true, true, true, true);

            if (!result.empty() && result.find("error") == result.end()) {
                auto elapsed = std::chrono::steady_clock::now() - start;
                std::cout << "\n\xE2\x9C\x93 Direct request successful! (Execution time: "
                          << std::chrono::duration<double>(elapsed).count() << "s)\n";
                std::cout << "=== Received weather data ===" << std::endl;
                for (auto& [k, v] : result) {
                    std::cout << "  " << k << ": " << v << std::endl;
                }
                std::cout << "==============================" << std::endl;
            } else {
                std::cout << "\n\xE2\x9C\x97 Failed to get weather data" << std::endl;
                if (debug && result.find("error") != result.end())
                    std::cout << "  Error: " << result["error"] << std::endl;
            }
        }
    }
    return 0;
}

