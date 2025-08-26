#include <iostream>
#include <iomanip>
#include <bitset>

#include "wiplib/packet/report_packet_compat.hpp"
#include "wiplib/packet/codec.hpp"

void debug_header_encoding() {
    std::cout << "=== Header Encoding Debug ===\n";
    
    // Create a test request
    auto request = wiplib::packet::compat::PyReportRequest::create_sensor_data_report(
        "130010",  // 東京
        1,         // 晴れ
        25.5f,     // 25.5°C
        30,        // 30%
        std::vector<std::string>{"強風注意報"},
        std::vector<std::string>{"地震情報"},
        1  // version
    );
    
    // Set packet ID
    auto pid_gen = std::make_unique<wiplib::packet::compat::PyPacketIDGenerator>();
    request.header.packet_id = pid_gen->next_id();
    
    std::cout << "Original header values:\n";
    std::cout << "  Version: " << static_cast<int>(request.header.version) << "\n";
    std::cout << "  Packet ID: " << request.header.packet_id << "\n";
    std::cout << "  Type: " << static_cast<int>(request.header.type) << " (should be 4)\n";
    std::cout << "  Area Code: " << request.header.area_code << "\n";
    
    // Encode the header manually
    auto header_result = wiplib::proto::encode_header(request.header);
    if (!header_result.has_value()) {
        std::cout << "ERROR: Failed to encode header\n";
        return;
    }
    
    auto header_bytes = header_result.value();
    
    std::cout << "\nEncoded header bytes:\n";
    for (size_t i = 0; i < header_bytes.size(); ++i) {
        std::cout << std::setw(2) << std::setfill('0') << std::hex 
                  << static_cast<int>(header_bytes[i]) << " ";
        if ((i + 1) % 8 == 0) std::cout << "\n";
    }
    std::cout << std::dec << "\n";
    
    // Decode the header back
    std::span<const uint8_t> span(header_bytes.data(), header_bytes.size());
    auto decoded_result = wiplib::proto::decode_header(span);
    if (!decoded_result.has_value()) {
        std::cout << "ERROR: Failed to decode header\n";
        return;
    }
    
    auto decoded_header = decoded_result.value();
    
    std::cout << "\nDecoded header values:\n";
    std::cout << "  Version: " << static_cast<int>(decoded_header.version) << "\n";
    std::cout << "  Packet ID: " << decoded_header.packet_id << "\n";
    std::cout << "  Type: " << static_cast<int>(decoded_header.type) << "\n";
    std::cout << "  Area Code: " << decoded_header.area_code << "\n";
    
    // Analyze bit positions manually
    std::cout << "\nBit analysis of first 3 bytes:\n";
    for (int i = 0; i < 3; ++i) {
        std::cout << "Byte " << i << ": " << std::bitset<8>(header_bytes[i]) 
                  << " (0x" << std::hex << static_cast<int>(header_bytes[i]) << std::dec << ")\n";
    }
    
    // Manual extraction of type field (bits 16-18)
    uint32_t first24bits = static_cast<uint32_t>(header_bytes[0]) |
                          (static_cast<uint32_t>(header_bytes[1]) << 8) |
                          (static_cast<uint32_t>(header_bytes[2]) << 16);
    
    uint8_t extracted_type = static_cast<uint8_t>((first24bits >> 16) & 0x7u);
    std::cout << "\nManual type extraction:\n";
    std::cout << "  First 24 bits: 0x" << std::hex << first24bits << std::dec << "\n";
    std::cout << "  Extracted type: " << static_cast<int>(extracted_type) << "\n";
}

void debug_full_packet_encoding() {
    std::cout << "\n=== Full Packet Encoding Debug ===\n";
    
    // Create a test request
    auto request = wiplib::packet::compat::PyReportRequest::create_sensor_data_report(
        "130010",  // 東京
        1,         // 晴れ
        25.5f,     // 25.5°C
        30,        // 30%
        std::vector<std::string>{"強風注意報"},
        std::vector<std::string>{"地震情報"},
        1  // version
    );
    
    // Set packet ID
    auto pid_gen = std::make_unique<wiplib::packet::compat::PyPacketIDGenerator>();
    request.header.packet_id = pid_gen->next_id();
    
    std::cout << "Request header type before encoding: " << static_cast<int>(request.header.type) << "\n";
    
    // Convert to proto::Packet format
    wiplib::proto::Packet packet;
    packet.header = request.header;
    
    std::cout << "Packet header type in proto::Packet: " << static_cast<int>(packet.header.type) << "\n";
    
    // Encode the packet
    auto packet_data = request.to_bytes();
    
    if (packet_data.empty()) {
        std::cout << "ERROR: Failed to encode packet\n";
        return;
    }
    
    std::cout << "Encoded packet size: " << packet_data.size() << " bytes\n";
    
    // Show the type byte specifically
    if (packet_data.size() >= 3) {
        std::cout << "Type byte (offset 2): 0x" << std::hex 
                  << static_cast<int>(packet_data[2]) << std::dec 
                  << " (" << static_cast<int>(packet_data[2]) << ")\n";
    }
    
    // Try to decode the packet back
    auto decoded_result = wiplib::proto::decode_packet(packet_data);
    if (decoded_result.has_value()) {
        auto decoded_packet = decoded_result.value();
        std::cout << "Decoded packet type: " << static_cast<int>(decoded_packet.header.type) << "\n";
    } else {
        std::cout << "Failed to decode packet\n";
    }
}

int main() {
    std::cout << "=== Packet Encoding Debug Tool ===\n\n";
    
    debug_header_encoding();
    debug_full_packet_encoding();
    
    return 0;
}