#include "wiplib/utils/env.hpp"
#include "wiplib/utils/encoding.hpp"

#include <cstdlib>

namespace wiplib::utils {

std::optional<std::string> getenv_os(const std::string& key) {
#ifdef _WIN32
    std::string os_key = key;
    if (key == "HOME") {
        os_key = "USERPROFILE"; // WindowsのHOME相当
    }
#else
    std::string os_key = key;
#endif
    const char* value = std::getenv(os_key.c_str());
    if (!value) {
        return std::nullopt;
    }
#ifdef _WIN32
    // Windowsでは環境変数のエンコーディング差異を吸収
    std::u16string u16 = utf8_to_utf16(value);
    return utf16_to_utf8(u16);
#else
    return std::string(value);
#endif
}

} // namespace wiplib::utils

