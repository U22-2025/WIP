#include "client.h"
#include <iostream>

namespace WIP_Client {

Client::Client(const std::string &host, int port, bool proxy)
    : host_(host), port_(port), proxy_(proxy),
      query_(host, port), location_(host, port) {}

void Client::setCoordinates(double lat, double lon) {
    lat_ = lat;
    lon_ = lon;
}

void Client::setAreaCode(int code) {
    area_ = code;
}

std::map<std::string,std::string> Client::getWeather() {
    std::map<std::string,std::string> result;
    // Placeholder response mimicking Python version
    if(area_) {
        result["area_code"] = std::to_string(*area_);
    } else if(lat_ && lon_) {
        result["latitude"] = std::to_string(*lat_);
        result["longitude"] = std::to_string(*lon_);
        result["area_code"] = "460010"; // dummy
    }
    result["weather_code"] = "100";
    result["temperature"] = "25";
    result["precipitation_prob"] = "10";
    return result;
}

} // namespace WIP_Client
