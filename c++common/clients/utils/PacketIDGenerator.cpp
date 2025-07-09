#include "PacketIDGenerator.hpp"
#include <random>

namespace wip {
namespace clients {
namespace utils {

PacketIDGenerator12Bit::PacketIDGenerator12Bit() {
    std::random_device rd;
    current_ = rd() % MAX_ID;
}

uint16_t PacketIDGenerator12Bit::next_id() {
    std::lock_guard<std::mutex> lock(mtx_);
    uint16_t id = current_;
    current_ = (current_ + 1) % MAX_ID;
    return id;
}

} // namespace utils
} // namespace clients
} // namespace wip
