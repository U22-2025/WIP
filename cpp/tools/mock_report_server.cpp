#include <iostream>
#include <iomanip>
#include <vector>
#include <thread>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <unistd.h>
#include <cstring>

#include "wiplib/packet/report_packet_compat.hpp"

class MockReportServer {
private:
    int socket_fd_;
    uint16_t port_;
    bool debug_;
    bool running_;

public:
    MockReportServer(uint16_t port = 4112, bool debug = true) 
        : socket_fd_(-1), port_(port), debug_(debug), running_(false) {}
    
    ~MockReportServer() {
        stop();
    }
    
    bool start() {
        socket_fd_ = socket(AF_INET, SOCK_DGRAM, 0);
        if (socket_fd_ < 0) {
            std::cerr << "Failed to create socket\n";
            return false;
        }
        
        struct sockaddr_in server_addr;
        memset(&server_addr, 0, sizeof(server_addr));
        server_addr.sin_family = AF_INET;
        server_addr.sin_addr.s_addr = INADDR_ANY;
        server_addr.sin_port = htons(port_);
        
        if (bind(socket_fd_, reinterpret_cast<struct sockaddr*>(&server_addr), sizeof(server_addr)) < 0) {
            std::cerr << "Failed to bind to port " << port_ << "\n";
            close(socket_fd_);
            return false;
        }
        
        if (debug_) {
            std::cout << "Mock Report Server started on port " << port_ << "\n";
        }
        
        running_ = true;
        return true;
    }
    
    void stop() {
        running_ = false;
        if (socket_fd_ >= 0) {
            close(socket_fd_);
            socket_fd_ = -1;
        }
    }
    
    void run() {
        std::vector<uint8_t> buffer(4096);
        struct sockaddr_in client_addr;
        socklen_t client_len = sizeof(client_addr);
        
        while (running_) {
            ssize_t received = recvfrom(socket_fd_, buffer.data(), buffer.size(), 0,
                                       reinterpret_cast<struct sockaddr*>(&client_addr), &client_len);
            
            if (received < 0) {
                if (running_) {
                    std::cerr << "Error receiving data\n";
                }
                continue;
            }
            
            if (debug_) {
                char client_ip[INET_ADDRSTRLEN];
                inet_ntop(AF_INET, &client_addr.sin_addr, client_ip, INET_ADDRSTRLEN);
                std::cout << "Received " << received << " bytes from " << client_ip 
                          << ":" << ntohs(client_addr.sin_port) << "\n";
            }
            
            // Try to parse as report request
            buffer.resize(received);
            processReportRequest(buffer, client_addr);
        }
    }
    
private:
    void processReportRequest(const std::vector<uint8_t>& data, const struct sockaddr_in& client_addr) {
        if (debug_) {
            std::cout << "Processing potential report request...\n";
            
            // Dump packet hex
            std::cout << "Packet dump (" << data.size() << " bytes):\n";
            for (size_t i = 0; i < data.size(); ++i) {
                if (i % 16 == 0) {
                    std::cout << std::setw(4) << std::setfill('0') << std::hex << i << ": ";
                }
                std::cout << std::setw(2) << std::setfill('0') << std::hex << static_cast<int>(data[i]) << " ";
                if ((i + 1) % 16 == 0 || i == data.size() - 1) {
                    std::cout << "\n";
                }
            }
            std::cout << std::dec << std::endl;
        }
        
        // Try to decode as ReportRequest
        auto request_result = wiplib::packet::compat::PyReportRequest::from_bytes(data);
        if (!request_result.has_value()) {
            if (debug_) {
                std::cout << "Failed to decode as ReportRequest\n";
            }
            return;
        }
        
        auto request = request_result.value();
        
        if (debug_) {
            std::cout << "Successfully decoded ReportRequest:\n";
            std::cout << "  Packet ID: " << request.header.packet_id << "\n";
            std::cout << "  Type: " << static_cast<int>(request.header.type) << "\n";
            std::cout << "  Area Code: " << request.header.area_code << "\n";
            std::cout << "  Timestamp: " << request.header.timestamp << "\n";
        }
        
        // Create response
        auto response = wiplib::packet::compat::PyReportResponse::create_ack_response(request, 1);
        auto response_data = response.to_bytes();
        
        if (response_data.empty()) {
            std::cerr << "Failed to encode response\n";
            return;
        }
        
        // Send response
        ssize_t sent = sendto(socket_fd_, response_data.data(), response_data.size(), 0,
                             reinterpret_cast<const struct sockaddr*>(&client_addr), sizeof(client_addr));
        
        if (sent < 0) {
            std::cerr << "Failed to send response\n";
        } else if (debug_) {
            std::cout << "Sent " << sent << " bytes response (Type 5 - ReportResponse)\n";
        }
    }
};

int main(int argc, char** argv) {
    uint16_t port = 4112;
    bool debug = true;
    
    if (argc > 1) {
        port = static_cast<uint16_t>(std::atoi(argv[1]));
    }
    
    MockReportServer server(port, debug);
    
    if (!server.start()) {
        return 1;
    }
    
    std::cout << "Mock Report Server listening on port " << port << "\n";
    std::cout << "Press Ctrl+C to stop...\n";
    
    server.run();
    
    return 0;
}