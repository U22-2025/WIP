#include <iostream>
#include <cstdlib>
#include <cstring>

#include "wiplib/client/simple_report_client.hpp"

int main() {
    std::cout << "=== Environment Variable Test ===\n";
    
    // Check environment variables directly
    const char* auth_enabled = std::getenv("REPORT_SERVER_REQUEST_AUTH_ENABLED");
    const char* auth_passphrase = std::getenv("REPORT_SERVER_PASSPHRASE");
    
    std::cout << "REPORT_SERVER_REQUEST_AUTH_ENABLED: " 
              << (auth_enabled ? auth_enabled : "NULL") << "\n";
    std::cout << "REPORT_SERVER_PASSPHRASE: " 
              << (auth_passphrase ? auth_passphrase : "NULL") << "\n";
    
    // Test SimpleReportClient initialization
    std::cout << "\n=== SimpleReportClient Test ===\n";
    
    try {
        wiplib::client::SimpleReportClient client("127.0.0.1", 4112, true);
        
        std::cout << "SimpleReportClient created successfully\n";
        
        // Set some test data
        client.set_sensor_data("130030", 1, 25.5f, 30, std::nullopt, std::nullopt);
        
        std::cout << "Test data set successfully\n";
        
        // Try to create a request (this will show auth status)
        auto result = client.send_report_data();
        
        if (result.has_value()) {
            std::cout << "Request succeeded\n";
        } else {
            std::cout << "Request failed\n";
        }
        
    } catch (const std::exception& e) {
        std::cout << "Error: " << e.what() << "\n";
    }
    
    return 0;
}