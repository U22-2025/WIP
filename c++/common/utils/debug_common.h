#ifndef COMMON_UTILS_DEBUG_COMMON_H
#define COMMON_UTILS_DEBUG_COMMON_H

#include <string>
#include <iostream>
#include <iomanip>

namespace common {
namespace utils {

inline void debug_print(const std::string &msg, const std::string &prefix="[DEBUG]") {
    std::cout << prefix << " " << msg << std::endl;
}

inline std::string debug_hex(const std::string &data, size_t max_len=0) {
    std::ostringstream oss;
    size_t len = data.size();
    if (max_len && len > max_len) len = max_len;
    for (size_t i=0;i<len;++i) {
        oss << std::hex << std::setw(2) << std::setfill('0')
            << (static_cast<unsigned int>(static_cast<unsigned char>(data[i]))) << ' ';
    }
    if (max_len && data.size() > max_len) oss << "...";
    return oss.str();
}

} // namespace utils
} // namespace common

#endif
