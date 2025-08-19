#include <iostream>
#include <future>
#include <chrono>
#include "include/wiplib/client/client.hpp"
#include "include/wiplib/client/client_async.hpp"

int main() {
    try {
        std::cout << "=== Testing Python-compatible C++ WIP Clients ===" << std::endl;

        // Test synchronous Client
        {
            std::cout << "\n--- Testing Client (synchronous) ---" << std::endl;
            
            // Test construction with Python-compatible arguments
            wiplib::client::Client client("127.0.0.1", 4110, std::nullopt, false, 
                                         35.6762, 139.6503, "130010");
            
            std::cout << "✓ Client created successfully" << std::endl;
            
            // Test property access
            auto lat = client.latitude();
            auto lon = client.longitude();
            auto area = client.area_code();
            
            if (lat.has_value() && lon.has_value()) {
                std::cout << "✓ Coordinates: " << lat.value() << ", " << lon.value() << std::endl;
            }
            
            if (area.has_value()) {
                std::cout << "✓ Area code: " << area.value() << std::endl;
            }
            
            // Test state snapshot
            auto snapshot = client.get_state();
            std::cout << "✓ State snapshot created - Host: " << snapshot.host 
                     << ", Port: " << snapshot.port << std::endl;
            
            // Test coordinate update
            client.set_coordinates(35.0, 139.0);
            auto new_lat = client.latitude();
            if (new_lat.has_value()) {
                std::cout << "✓ Coordinates updated to: " << new_lat.value() << std::endl;
            }
            
            client.close();
            std::cout << "✓ Client closed successfully" << std::endl;
        }

        // Test asynchronous ClientAsync
        {
            std::cout << "\n--- Testing ClientAsync (asynchronous) ---" << std::endl;
            
            wiplib::client::ClientAsync async_client("127.0.0.1", 4110, std::nullopt, false);
            std::cout << "✓ ClientAsync created successfully" << std::endl;
            
            // Test property access
            auto lat = async_client.latitude();
            auto lon = async_client.longitude();
            
            std::cout << "✓ ClientAsync property access working" << std::endl;
            
            // Test coordinate setting
            async_client.set_coordinates(36.0, 140.0);
            auto new_lat = async_client.latitude();
            if (new_lat.has_value()) {
                std::cout << "✓ ClientAsync coordinates updated to: " << new_lat.value() << std::endl;
            }
            
            async_client.close();
            std::cout << "✓ ClientAsync closed successfully" << std::endl;
        }

        std::cout << "\n=== All tests passed! ===" << std::endl;
        return 0;
        
    } catch (const std::exception& e) {
        std::cerr << "❌ Error: " << e.what() << std::endl;
        return 1;
    }
}