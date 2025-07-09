#ifndef WIP_CLIENTS_UTILS_PACKET_ID_GENERATOR_HPP
#define WIP_CLIENTS_UTILS_PACKET_ID_GENERATOR_HPP

#include <mutex>
#include <cstdint>

namespace wip {
namespace clients {
namespace utils {

class PacketIDGenerator12Bit {
public:
    PacketIDGenerator12Bit();
    uint16_t next_id();
private:
    std::mutex mtx_;
    uint16_t current_;
    static constexpr uint16_t MAX_ID = 4096;
};

} // namespace utils
} // namespace clients
} // namespace wip

#endif // WIP_CLIENTS_UTILS_PACKET_ID_GENERATOR_HPP
