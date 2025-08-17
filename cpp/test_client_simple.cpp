#include "include/wiplib/client/wip_client.hpp"
#include <iostream>

int main() {
    try {
        // Test basic construction
        wiplib::client::ServerConfig config;
        config.host = "localhost";
        config.port = 8080;
        
        wiplib::client::WipClient wip_client(config, false);
        std::cout << "WipClient created successfully" << std::endl;
        
        // Test state access
        wip_client.set_coordinates(35.6762, 139.6503);
        auto state = wip_client.state();
        
        if (state.latitude.has_value() && state.longitude.has_value()) {
            std::cout << "Coordinates: " << state.latitude.value() << ", " << state.longitude.value() << std::endl;
        }
        
        return 0;
    } catch (const std::exception& e) {
        std::cerr << "Error: " << e.what() << std::endl;
        return 1;
    }
}