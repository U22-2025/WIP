#include "wiplib/client/auth_config.hpp"
#include "wiplib/utils/dotenv.hpp"
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
    // Load .env if present (once per process). Do not overwrite explicit env.
    (void)wiplib::utils::load_dotenv(".env", /*overwrite=*/false, /*max_parent_levels=*/3);
    AuthConfig cfg{};

    // Python版と同様に、各サービスごとに個別に認証設定をチェック
    cfg.weather_request_auth_enabled =
        env_truthy(std::getenv("WEATHER_SERVER_REQUEST_AUTH_ENABLED"));
    cfg.location_resolver_request_auth_enabled =
        env_truthy(std::getenv("LOCATION_RESOLVER_REQUEST_AUTH_ENABLED"));
    cfg.query_generator_request_auth_enabled =
        env_truthy(std::getenv("QUERY_GENERATOR_REQUEST_AUTH_ENABLED"));
    cfg.report_server_request_auth_enabled =
        env_truthy(std::getenv("REPORT_SERVER_REQUEST_AUTH_ENABLED"));

    // 全体の有効化フラグは、いずれかのサービスで認証が有効な場合にtrue
    cfg.enabled = cfg.weather_request_auth_enabled || 
                  cfg.location_resolver_request_auth_enabled ||
                  cfg.query_generator_request_auth_enabled ||
                  cfg.report_server_request_auth_enabled;

    cfg.verify_response = env_truthy(std::getenv("WIP_CLIENT_VERIFY_RESPONSE_AUTH"));
    cfg.request_response_auth = env_truthy(std::getenv("WIP_CLIENT_REQUEST_RESPONSE_AUTH"));
    
    // 個別のサーバー向けレスポンス認証設定
    cfg.weather_server_response_auth_enabled = 
        env_truthy(std::getenv("WEATHER_SERVER_RESPONSE_AUTH_ENABLED"));
    cfg.location_server_response_auth_enabled = 
        env_truthy(std::getenv("LOCATION_SERVER_RESPONSE_AUTH_ENABLED"));
    cfg.query_server_response_auth_enabled = 
        env_truthy(std::getenv("QUERY_SERVER_RESPONSE_AUTH_ENABLED"));
    cfg.report_server_response_auth_enabled = 
        env_truthy(std::getenv("REPORT_SERVER_RESPONSE_AUTH_ENABLED"));

    if (const char* p = std::getenv("WEATHER_SERVER_PASSPHRASE")) cfg.weather = std::string(p);
    if (const char* p = std::getenv("LOCATION_SERVER_PASSPHRASE")) cfg.location = std::string(p);
    if (const char* p = std::getenv("QUERY_SERVER_PASSPHRASE"))   cfg.query = std::string(p);
    if (const char* p = std::getenv("REPORT_SERVER_PASSPHRASE"))  cfg.report = std::string(p);
    return cfg;
}

} // namespace wiplib::client
