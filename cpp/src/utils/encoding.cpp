#include "wiplib/utils/encoding.hpp"

#include <codecvt>
#include <locale>

namespace wiplib::utils {

std::u16string utf8_to_utf16(const std::string& str) {
    std::wstring_convert<std::codecvt_utf8_utf16<char16_t>, char16_t> conv;
    return conv.from_bytes(str);
}

std::string utf16_to_utf8(const std::u16string& str) {
    std::wstring_convert<std::codecvt_utf8_utf16<char16_t>, char16_t> conv;
    return conv.to_bytes(str);
}

} // namespace wiplib::utils

