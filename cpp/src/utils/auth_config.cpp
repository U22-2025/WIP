#include "wiplib/client/auth_config.hpp"
#include <cstdlib>
#include <string>
#include <algorithm>

namespace wiplib::client {

static bool env_truthy(const char* v){
    if (!v) return false;
    std::string s(v);
    std::transform(s.begin(), s.end(), s.begin(), [](unsigned char c){ return static_cast<char>(std::tolower(c));});
    return (s == "1" || s == "true" || s == "yes" || s == "on");
}

AuthConfig AuthConfig::from_env(){
    AuthConfig cfg{};
    cfg.enabled = env_truthy(std::getenv("WIP_CLIENT_AUTH_ENABLED"));
    cfg.verify_response = env_truthy(std::getenv("WIP_CLIENT_VERIFY_RESPONSE_AUTH"));
    if (const char* p = std::getenv("WEATHER_SERVER_PASSPHRASE")) cfg.weather = std::string(p);
    if (const char* p = std::getenv("LOCATION_SERVER_PASSPHRASE")) cfg.location = std::string(p);
    if (const char* p = std::getenv("QUERY_SERVER_PASSPHRASE"))   cfg.query = std::string(p);
    if (const char* p = std::getenv("REPORT_SERVER_PASSPHRASE"))  cfg.report = std::string(p);
    return cfg;
}

} // namespace wiplib::client

