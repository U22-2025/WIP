#ifndef COMMON_CLIENTS_UTILS_PACKET_ID_GENERATOR_H
#define COMMON_CLIENTS_UTILS_PACKET_ID_GENERATOR_H

#include <atomic>
#include <cstdint>

namespace common {
namespace clients {
namespace utils {

class PacketIDGenerator12Bit {
public:
    PacketIDGenerator12Bit() : current_(0) {}
    uint16_t next() {
        uint16_t id = current_.fetch_add(1, std::memory_order_relaxed) & 0x0FFF;
        return id;
    }
private:
    std::atomic<uint16_t> current_;
};

} // namespace utils
} // namespace clients
} // namespace common

#endif
