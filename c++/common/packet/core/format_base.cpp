#include "format_base.h"
#include "bit_utils.h"
#include <numeric>

namespace common {
namespace packet {
namespace core {

FormatBase::FormatBase() {}

uint64_t FormatBase::calcChecksum(const std::vector<uint8_t> &data) {
    uint64_t sum = std::accumulate(data.begin(), data.end(), 0u);
    while (sum >> 12) sum = (sum & 0xFFF) + (sum >> 12);
    return (~sum) & 0xFFF;
}

FormatBase::u128 FormatBase::toBits() const {
    u128 bits = 0;
    bits |= static_cast<u128>(version & 0xF) << 0;
    bits |= static_cast<u128>(packet_id & 0xFFF) << 4;
    bits |= static_cast<u128>(type & 0x7) << 16;
    bits |= static_cast<u128>(checksum & 0xFFF) << 116;
    return bits;
}

void FormatBase::fromBits(u128 bits) {
    version = extract_bits(bits,0,4);
    packet_id = extract_bits(bits,4,12);
    type = extract_bits(bits,16,3);
    checksum = extract_bits(bits,116,12);
}

std::vector<uint8_t> FormatBase::toBytes() const {
    u128 bits = toBits();
    std::vector<uint8_t> data(16,0);
    for(int i=0;i<16;++i) data[i] = static_cast<uint8_t>(bits>>(i*8));
    uint64_t cs = calcChecksum(data);
    bits |= static_cast<u128>(cs) << 116;
    for(int i=0;i<16;++i) data[i] = static_cast<uint8_t>(bits>>(i*8));
    return data;
}

void FormatBase::fromBytes(const std::vector<uint8_t> &data) {
    if(data.size()<16) return;
    u128 bits=0;
    for(int i=0;i<16;++i) bits |= static_cast<u128>(data[i])<<(i*8);
    fromBits(bits);
}

} // namespace core
} // namespace packet
} // namespace common
