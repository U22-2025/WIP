#include "include/wiplib/client/auth_config.hpp"
#include <iostream>
#include <cstdlib>

int main() {
    // Test environment variable reading
    std::cout << "=== Environment Variables ===" << std::endl;
    std::cout << "QUERY_GENERATOR_REQUEST_AUTH_ENABLED: " << 
        (std::getenv("QUERY_GENERATOR_REQUEST_AUTH_ENABLED") ? std::getenv("QUERY_GENERATOR_REQUEST_AUTH_ENABLED") : "not set") << std::endl;
    std::cout << "QUERY_SERVER_PASSPHRASE: " << 
        (std::getenv("QUERY_SERVER_PASSPHRASE") ? std::getenv("QUERY_SERVER_PASSPHRASE") : "not set") << std::endl;
    
    // Test AuthConfig
    std::cout << "\n=== AuthConfig Test ===" << std::endl;
    auto auth_cfg = wiplib::client::AuthConfig::from_env();
    std::cout << "Auth enabled: " << (auth_cfg.enabled ? "true" : "false") << std::endl;
    std::cout << "Query passphrase: " << 
        (auth_cfg.query.has_value() ? auth_cfg.query.value() : "not set") << std::endl;
    
    return 0;
}