#include "client.h"
#include <iostream>
#include <getopt.h>

using namespace WIP_Client;

int main(int argc, char** argv) {
    bool useCoord = false;
    bool useProxy = false;

    const option long_opts[] = {
        {"coord", no_argument, nullptr, 'c'},
        {"proxy", no_argument, nullptr, 'p'},
        {nullptr, 0, nullptr, 0}
    };
    int opt;
    while((opt=getopt_long(argc, argv, "cp", long_opts, nullptr)) != -1) {
        if(opt=='c') useCoord=true;
        else if(opt=='p') useProxy=true;
    }

    std::cout << (useProxy? "Weather Client Example - Via Weather Server (Proxy Mode)" : "Weather Client Example - Direct Communication") << '\n';
    std::cout << std::string(60,'=') << '\n';

    Client client("localhost", 4110, useProxy);

    if(useCoord) {
        std::cout << "\n1. Coordinate-based request" << (useProxy? " via Weather Server" : " (direct)") << '\n';
        client.setCoordinates(35.6895, 139.6917);
        auto result = client.getWeather();
        if(!result.empty()) {
            std::cout << "\n\u2713 Request successful" << (useProxy? " via Weather Server" : "") << "!" << '\n';
            std::cout << "=== Received packet content ===" << '\n';
            for(const auto& kv : result) {
                std::cout << "  " << kv.first << ": " << kv.second << '\n';
            }
            std::cout << "==============================" << '\n';
        } else {
            std::cout << "\n\u2717 Request failed" << '\n';
        }
    } else {
        std::cout << "\n1. Area code request" << (useProxy? " via Weather Server" : " (direct)") << '\n';
        client.setAreaCode(460010);
        auto result = client.getWeather();
        if(!result.empty()) {
            std::cout << "\n\u2713 Request successful" << (useProxy? " via Weather Server" : "") << "!" << '\n';
            for(const auto& kv : result) {
                std::cout << "  " << kv.first << ": " << kv.second << '\n';
            }
        } else {
            std::cout << "\n\u2717 Failed to get weather data" << '\n';
        }
    }
}
