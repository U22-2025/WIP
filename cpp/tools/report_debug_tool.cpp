#include <iostream>
#include <iomanip>
#include <cstring>
#include "wiplib/utils/platform_compat.hpp"

#include "wiplib/client/report_client.hpp"

void dump_packet_hex(const std::vector<uint8_t>& data) {
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

void analyze_packet_structure(const std::vector<uint8_t>& data) {
    if (data.size() < 16) {
        std::cout << "Packet too small for analysis\n";
        return;
    }
    
    std::cout << "=== Packet Structure Analysis ===\n";
    
    // ヘッダー解析（正しいビットフィールド解析）
    // Bit layout: version(4) + packet_id(12) + type(3) + flags(8) + ...
    uint16_t first16 = static_cast<uint16_t>(data[0]) | (static_cast<uint16_t>(data[1]) << 8);
    uint8_t version = first16 & 0x0F;
    uint16_t packet_id = (first16 >> 4) & 0x0FFF;
    
    // Type is stored in bits 16-18, which spans data[2] bits 0-2
    uint8_t packet_type = data[2] & 0x07;  // Extract lower 3 bits
    
    std::cout << "Version: " << static_cast<int>(version) << "\n";
    std::cout << "Packet ID: " << packet_id << "\n";
    std::cout << "Packet Type: " << static_cast<int>(packet_type) << " (expected: 4 for ReportRequest)\n";
    
    // Show raw bytes for debugging
    std::cout << "Raw header bytes: ";
    for (int i = 0; i < 3; ++i) {
        std::cout << "0x" << std::hex << std::setw(2) << std::setfill('0') << static_cast<int>(data[i]) << " ";
    }
    std::cout << std::dec << "\n";
    
    // フラグ解析
    if (data.size() > 3) {
        uint8_t flags = data[3];
        std::cout << "Flags: 0x" << std::hex << static_cast<int>(flags) << std::dec << "\n";
        std::cout << "  Weather: " << ((flags & 0x01) ? "true" : "false") << "\n";
        std::cout << "  Temperature: " << ((flags & 0x02) ? "true" : "false") << "\n";
        std::cout << "  Precipitation: " << ((flags & 0x04) ? "true" : "false") << "\n";
        std::cout << "  Alert: " << ((flags & 0x08) ? "true" : "false") << "\n";
        std::cout << "  Disaster: " << ((flags & 0x10) ? "true" : "false") << "\n";
        std::cout << "  Extended: " << ((flags & 0x20) ? "true" : "false") << "\n";
    }
    
    // エリアコード解析（オフセット8-11）
    if (data.size() >= 12) {
        uint32_t area_code = 
            static_cast<uint32_t>(data[8]) |
            (static_cast<uint32_t>(data[9]) << 8) |
            (static_cast<uint32_t>(data[10]) << 16) |
            (static_cast<uint32_t>(data[11]) << 24);
        std::cout << "Area Code: " << area_code << "\n";
    }
    
    std::cout << "========================\n\n";
}

int test_packet_generation() {
    std::cout << "=== Testing Packet Generation ===\n";
    
    try {
        // SimpleReportClientを作成（実際の送信は行わない）
        wiplib::client::ReportClient client("127.0.0.1", 4112, true);
        
        // データ設定
        client.set_sensor_data(
            "130010",  // 東京
            1,         // 晴れ
            25.5f,     // 25.5°C
            30,        // 30%
            std::vector<std::string>{"強風注意報"},
            std::vector<std::string>{"地震情報"}
        );
        
        std::cout << "Sensor data set successfully\n";
        
        // 直接パケット生成をテスト
        auto request_result = wiplib::packet::compat::PyReportRequest::create_sensor_data_report(
            "130010",
            1,
            25.5f,
            30,
            std::vector<std::string>{"強風注意報"},
            std::vector<std::string>{"地震情報"},
            1  // version
        );
        
        // パケットIDを設定
        auto pid_gen = std::make_unique<wiplib::packet::compat::PyPacketIDGenerator>();
        request_result.header.packet_id = pid_gen->next_id();
        
        std::cout << "Request packet created\n";
        std::cout << "  Area Code: " << request_result.header.area_code << "\n";
        std::cout << "  Packet ID: " << request_result.header.packet_id << "\n";
        std::cout << "  Type: " << static_cast<int>(request_result.header.type) << "\n";
        
        // パケットをバイト配列に変換
        auto packet_data = request_result.to_bytes();
        
        if (packet_data.empty()) {
            std::cout << "ERROR: Failed to encode packet to bytes\n";
            return 1;
        }
        
        std::cout << "Packet encoded successfully (" << packet_data.size() << " bytes)\n";
        
        // パケット内容をダンプ
        dump_packet_hex(packet_data);
        analyze_packet_structure(packet_data);
        
        return 0;
        
    } catch (const std::exception& e) {
        std::cout << "ERROR: " << e.what() << "\n";
        return 1;
    }
}

int test_socket_creation() {
    std::cout << "=== Testing Socket Creation ===\n";
    
    // UDPソケット作成
    int sock = socket(AF_INET, SOCK_DGRAM, 0);
    if (sock < 0) {
        std::cout << "ERROR: Failed to create socket: " << strerror(errno) << "\n";
        return 1;
    }
    
    std::cout << "Socket created successfully (fd: " << sock << ")\n";
    
    // タイムアウト設定
    struct timeval timeout;
    timeout.tv_sec = 10;
    timeout.tv_usec = 0;
    
    if (wiplib::utils::platform_setsockopt(sock, SOL_SOCKET, SO_RCVTIMEO, &timeout, sizeof(timeout)) < 0) {
        std::cout << "ERROR: Failed to set socket timeout: " << strerror(errno) << "\n";
        platform_close_socket(sock);
        return 1;
    }
    
    std::cout << "Socket timeout set to 10 seconds\n";
    
    // 送信先アドレス設定
    struct sockaddr_in server_addr;
    memset(&server_addr, 0, sizeof(server_addr));
    server_addr.sin_family = AF_INET;
    server_addr.sin_port = htons(4112);
    
    if (inet_pton(AF_INET, "127.0.0.1", &server_addr.sin_addr) != 1) {
        std::cout << "ERROR: Failed to parse IP address\n";
        platform_close_socket(sock);
        return 1;
    }
    
    std::cout << "Target address set to 127.0.0.1:4112\n";
    
    // テストデータ送信
    std::string test_data = "TEST_PACKET";
    ssize_t sent_bytes = sendto(sock, test_data.c_str(), test_data.length(), 0,
                               reinterpret_cast<struct sockaddr*>(&server_addr), sizeof(server_addr));
    
    if (sent_bytes < 0) {
        std::cout << "ERROR: Failed to send test data: " << strerror(errno) << "\n";
        platform_close_socket(sock);
        return 1;
    }
    
    std::cout << "Test data sent successfully (" << sent_bytes << " bytes)\n";
    
    platform_close_socket(sock);
    return 0;
}

int main(int argc, char** argv) {
    std::cout << "=== Report Packet Debug Tool ===\n\n";
    
    if (argc > 1 && std::string(argv[1]) == "socket") {
        return test_socket_creation();
    } else if (argc > 1 && std::string(argv[1]) == "packet") {
        return test_packet_generation();
    } else {
        std::cout << "Running all tests...\n\n";
        
        int result1 = test_packet_generation();
        std::cout << "\n";
        int result2 = test_socket_creation();
        
        return (result1 == 0 && result2 == 0) ? 0 : 1;
    }
}