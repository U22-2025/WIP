#pragma once

#include <optional>
#include <string>

namespace wiplib::client {

struct AuthConfig {
    bool enabled = false; // 全体の有効化フラグ（いずれかの認証設定が有効なら true）
    bool weather_request_auth_enabled = false;
    bool location_resolver_request_auth_enabled = false;
    bool query_generator_request_auth_enabled = false;
    bool report_server_request_auth_enabled = false;
    bool verify_response = false; // optional, default off
    bool request_response_auth = false; // サーバーにレスポンス認証を要求するかどうか
    
    // 個別のサーバー向けレスポンス認証設定
    bool weather_server_response_auth_enabled = false;
    bool location_server_response_auth_enabled = false;
    bool query_server_response_auth_enabled = false;
    bool report_server_response_auth_enabled = false;
    std::optional<std::string> weather{};
    std::optional<std::string> location{};
    std::optional<std::string> query{};
    std::optional<std::string> report{};

    static AuthConfig from_env();
};

} // namespace wiplib::client

