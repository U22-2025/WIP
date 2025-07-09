#include "PacketIDGenerator.hpp"
#include <random>

namespace wip {
namespace clients {
namespace utils {

PacketIDGenerator::PacketIDGenerator() {
    std::random_device rd;
    std::mt19937 gen(rd());
    std::uniform_int_distribution<uint16_t> dist(0, MAX_ID - 1);
    current_ = dist(gen);
}

PacketIDGenerator& PacketIDGenerator::instance() {
    static PacketIDGenerator inst;
    return inst;
}

uint16_t PacketIDGenerator::next_id() {
    std::lock_guard<std::mutex> lock(mtx_);
    uint16_t pid = current_;
    current_ = static_cast<uint16_t>((current_ + 1) % MAX_ID);
    return pid;
}

std::array<uint8_t,2> PacketIDGenerator::next_id_bytes() {
    uint16_t pid = next_id();
    std::array<uint8_t,2> bytes{};
    bytes[0] = static_cast<uint8_t>(pid & 0xFF);
    bytes[1] = static_cast<uint8_t>((pid >> 8) & 0x0F);
    return bytes;
}

} // namespace utils
} // namespace clients
} // namespace wip
