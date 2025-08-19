#include "include/wiplib/client/client.hpp"
#include "include/wiplib/client/client_async.hpp"
#include <iostream>

int main() {
    try {
        // Test Client construction
        wiplib::client::Client client("localhost", 8080);
        std::cout << "Client created successfully" << std::endl;
        
        // Test property access
        client.set_coordinates(35.6762, 139.6503);
        auto lat = client.latitude();
        auto lon = client.longitude();
        
        if (lat.has_value() && lon.has_value()) {
            std::cout << "Coordinates: " << lat.value() << ", " << lon.value() << std::endl;
        }
        
        // Test ClientAsync construction
        wiplib::client::ClientAsync async_client("localhost", 8080);
        std::cout << "AsyncClient created successfully" << std::endl;
        
        return 0;
    } catch (const std::exception& e) {
        std::cerr << "Error: " << e.what() << std::endl;
        return 1;
    }
}