#pragma once

#include <optional>
#include <string>

namespace wiplib::client {

struct AuthConfig {
    bool enabled = false;
    bool verify_response = false; // optional, default off
    std::optional<std::string> weather{};
    std::optional<std::string> location{};
    std::optional<std::string> query{};
    std::optional<std::string> report{};

    static AuthConfig from_env();
};

} // namespace wiplib::client

