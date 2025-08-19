#include "wiplib/packet/bit_utils.hpp"
#include <algorithm>
#include <cassert>

namespace wiplib::packet {

uint64_t extract_bits(uint64_t data, uint8_t bit_offset, uint8_t bit_length) {
    assert(bit_length <= 64);
    assert(bit_offset + bit_length <= 64);
    
    if (bit_length == 0) return 0;
    
    // Create mask
    uint64_t mask = (1ULL << bit_length) - 1;
    
    // Extract from specified position
    return (data >> bit_offset) & mask;
}

uint64_t extract_bits(std::span<const uint8_t> data, uint32_t bit_offset, uint8_t bit_length) {
    assert(bit_length <= 64);
    
    if (bit_length == 0) return 0;
    
    uint32_t byte_offset = bit_offset / 8;
    uint8_t bit_pos = bit_offset % 8;
    
    uint64_t result = 0;
    uint8_t bits_read = 0;
    
    // Calculate required bytes
    uint32_t bytes_needed = (bit_pos + bit_length + 7) / 8;
    
    // Check byte boundary
    if (byte_offset + bytes_needed > data.size()) {
        return 0; // Insufficient data
    }
    
    // Read bytes in big-endian
    for (uint32_t i = 0; i < bytes_needed && bits_read < bit_length; ++i) {
        uint8_t byte_data = data[byte_offset + i];
        uint8_t bits_from_byte = std::min(static_cast<uint8_t>(8 - (i == 0 ? bit_pos : 0)), 
                                         static_cast<uint8_t>(bit_length - bits_read));
        
        if (i == 0 && bit_pos > 0) {
            // Partial read from first byte
            byte_data = byte_data & ((1 << (8 - bit_pos)) - 1);
        }
        
        result = (result << bits_from_byte) | (byte_data >> (8 - bits_from_byte - (i == 0 ? bit_pos : 0)));
        bits_read += bits_from_byte;
    }
    
    return result;
}

uint64_t set_bits(uint64_t data, uint8_t bit_offset, uint8_t bit_length, uint64_t value) {
    assert(bit_length <= 64);
    assert(bit_offset + bit_length <= 64);
    
    if (bit_length == 0) return data;
    
    // Create mask
    uint64_t mask = ((1ULL << bit_length) - 1) << bit_offset;
    
    // Clear existing bits and set new value
    return (data & ~mask) | ((value & ((1ULL << bit_length) - 1)) << bit_offset);
}

void set_bits(std::span<uint8_t> data, uint32_t bit_offset, uint8_t bit_length, uint64_t value) {
    assert(bit_length <= 64);
    
    if (bit_length == 0) return;
    
    uint32_t byte_offset = bit_offset / 8;
    uint8_t bit_pos = bit_offset % 8;
    
    uint8_t bits_written = 0;
    uint32_t bytes_needed = (bit_pos + bit_length + 7) / 8;
    
    // Check byte boundary
    if (byte_offset + bytes_needed > data.size()) {
        return; // Insufficient data
    }
    
    // Write bytes in big-endian
    for (uint32_t i = 0; i < bytes_needed && bits_written < bit_length; ++i) {
        uint8_t bits_to_write = std::min(static_cast<uint8_t>(8 - (i == 0 ? bit_pos : 0)), 
                                        static_cast<uint8_t>(bit_length - bits_written));
        
        uint8_t shift = bit_length - bits_written - bits_to_write;
        uint8_t byte_value = static_cast<uint8_t>((value >> shift) & ((1 << bits_to_write) - 1));
        
        if (i == 0 && bit_pos > 0) {
            // Partial write to first byte
            uint8_t mask = ((1 << bits_to_write) - 1) << (8 - bit_pos - bits_to_write);
            data[byte_offset + i] = (data[byte_offset + i] & ~mask) | (byte_value << (8 - bit_pos - bits_to_write));
        } else {
            // Complete byte write
            uint8_t bit_position = 8 - bits_to_write;
            uint8_t mask = ((1 << bits_to_write) - 1) << bit_position;
            data[byte_offset + i] = (data[byte_offset + i] & ~mask) | (byte_value << bit_position);
        }
        
        bits_written += bits_to_write;
    }
}

uint16_t read_le16(const uint8_t* data) {
    return static_cast<uint16_t>(data[0]) | (static_cast<uint16_t>(data[1]) << 8);
}

uint32_t read_le32(const uint8_t* data) {
    return static_cast<uint32_t>(data[0]) | 
           (static_cast<uint32_t>(data[1]) << 8) |
           (static_cast<uint32_t>(data[2]) << 16) |
           (static_cast<uint32_t>(data[3]) << 24);
}

uint64_t read_le64(const uint8_t* data) {
    return static_cast<uint64_t>(data[0]) | 
           (static_cast<uint64_t>(data[1]) << 8) |
           (static_cast<uint64_t>(data[2]) << 16) |
           (static_cast<uint64_t>(data[3]) << 24) |
           (static_cast<uint64_t>(data[4]) << 32) |
           (static_cast<uint64_t>(data[5]) << 40) |
           (static_cast<uint64_t>(data[6]) << 48) |
           (static_cast<uint64_t>(data[7]) << 56);
}

void write_le16(uint8_t* data, uint16_t value) {
    data[0] = static_cast<uint8_t>(value & 0xFF);
    data[1] = static_cast<uint8_t>((value >> 8) & 0xFF);
}

void write_le32(uint8_t* data, uint32_t value) {
    data[0] = static_cast<uint8_t>(value & 0xFF);
    data[1] = static_cast<uint8_t>((value >> 8) & 0xFF);
    data[2] = static_cast<uint8_t>((value >> 16) & 0xFF);
    data[3] = static_cast<uint8_t>((value >> 24) & 0xFF);
}

void write_le64(uint8_t* data, uint64_t value) {
    data[0] = static_cast<uint8_t>(value & 0xFF);
    data[1] = static_cast<uint8_t>((value >> 8) & 0xFF);
    data[2] = static_cast<uint8_t>((value >> 16) & 0xFF);
    data[3] = static_cast<uint8_t>((value >> 24) & 0xFF);
    data[4] = static_cast<uint8_t>((value >> 32) & 0xFF);
    data[5] = static_cast<uint8_t>((value >> 40) & 0xFF);
    data[6] = static_cast<uint8_t>((value >> 48) & 0xFF);
    data[7] = static_cast<uint8_t>((value >> 56) & 0xFF);
}

} // namespace wiplib::packet