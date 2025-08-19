#pragma once

#include <optional>
#include <string>

namespace wiplib::client {

struct AuthConfig {
    bool enabled = false; // global switch via WIP_CLIENT_AUTH_ENABLED
    bool weather_request_auth_enabled = false;
    bool location_resolver_request_auth_enabled = false;
    bool query_generator_request_auth_enabled = false;
    bool report_server_request_auth_enabled = false;
    bool verify_response = false; // optional, default off
    std::optional<std::string> weather{};
    std::optional<std::string> location{};
    std::optional<std::string> query{};
    std::optional<std::string> report{};

    static AuthConfig from_env();
};

} // namespace wiplib::client

