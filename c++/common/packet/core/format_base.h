#ifndef COMMON_PACKET_CORE_FORMAT_BASE_H
#define COMMON_PACKET_CORE_FORMAT_BASE_H

#include <cstdint>
#include <map>
#include <string>
#include <vector>

namespace common {
namespace packet {
namespace core {

class FormatBase {
public:
    FormatBase();
    virtual ~FormatBase() = default;

    using u128 = unsigned __int128;

    u128 toBits() const;
    void fromBits(u128 bits);

    std::vector<uint8_t> toBytes() const;
    void fromBytes(const std::vector<uint8_t> &data);

    int version{1};
    int packet_id{0};
    int type{0};
    int checksum{0};

protected:
    static uint64_t calcChecksum(const std::vector<uint8_t> &data);
};

} // namespace core
} // namespace packet
} // namespace common

#endif
