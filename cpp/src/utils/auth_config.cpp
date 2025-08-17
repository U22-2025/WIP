#include "wiplib/client/auth_config.hpp"
#include <cstdlib>
#include <string>
#include <algorithm>
#include <iostream>

namespace wiplib::client {

static bool env_truthy(const char* v){
    if (!v) return false;
    std::string s(v);
    std::transform(s.begin(), s.end(), s.begin(), [](unsigned char c){ return static_cast<char>(std::tolower(c));});
    return (s == "1" || s == "true" || s == "yes" || s == "on");
}

AuthConfig AuthConfig::from_env(){
    AuthConfig cfg{};
    
    // Debug: Print environment variable values
    const char* auth_enabled = std::getenv("QUERY_GENERATOR_REQUEST_AUTH_ENABLED");
    const char* query_pass = std::getenv("QUERY_SERVER_PASSPHRASE");
    std::cerr << "DEBUG: QUERY_GENERATOR_REQUEST_AUTH_ENABLED = " << (auth_enabled ? auth_enabled : "NULL") << std::endl;
    std::cerr << "DEBUG: QUERY_SERVER_PASSPHRASE = " << (query_pass ? query_pass : "NULL") << std::endl;
    
    // Python互換の環境変数のみを使用
    cfg.enabled = env_truthy(std::getenv("QUERY_GENERATOR_REQUEST_AUTH_ENABLED"));
    cfg.verify_response = env_truthy(std::getenv("WIP_CLIENT_VERIFY_RESPONSE_AUTH"));
    
    std::cerr << "DEBUG: env_truthy result = " << (cfg.enabled ? "true" : "false") << std::endl;
    
    // パスフレーズはPython互換の環境変数名を使用
    if (const char* p = std::getenv("WEATHER_SERVER_PASSPHRASE")) cfg.weather = std::string(p);
    if (const char* p = std::getenv("LOCATION_SERVER_PASSPHRASE")) cfg.location = std::string(p);
    if (const char* p = std::getenv("QUERY_SERVER_PASSPHRASE"))   cfg.query = std::string(p);
    if (const char* p = std::getenv("REPORT_SERVER_PASSPHRASE"))  cfg.report = std::string(p);
    return cfg;
}

} // namespace wiplib::client

