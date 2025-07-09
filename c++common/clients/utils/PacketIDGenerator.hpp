#pragma once
#include <cstdint>
#include <array>
#include <mutex>

namespace wip {
namespace clients {
namespace utils {

class PacketIDGenerator {
public:
    PacketIDGenerator();
    uint16_t next_id();
    std::array<uint8_t,2> next_id_bytes();

    static PacketIDGenerator& instance();

private:
    std::mutex mtx_;
    uint16_t current_;
    static constexpr uint16_t MAX_ID = 4096;
};

} // namespace utils
} // namespace clients
} // namespace wip
