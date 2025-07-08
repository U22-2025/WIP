#ifndef COMMON_PACKET_CORE_EXTENDED_FIELD_H
#define COMMON_PACKET_CORE_EXTENDED_FIELD_H

#include <string>
#include <unordered_map>
#include <optional>
#include <vector>
#include <stdint.h>

namespace common {
namespace packet {
namespace core {

class ExtendedField {
public:
    void set(const std::string &key, const std::string &value);
    std::optional<std::string> get(const std::string &key) const;
    bool empty() const { return data_.empty(); }
    uint64_t toBits() const;
    static ExtendedField fromBits(uint64_t bits);
    std::unordered_map<std::string,std::string> toDict() const { return data_; }
private:
    std::unordered_map<std::string,std::string> data_;
};

} // namespace core
} // namespace packet
} // namespace common

#endif
