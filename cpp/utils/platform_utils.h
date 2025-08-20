#pragma once

#include <cstdlib>
#include <string>
#include <optional>
#include <filesystem>
#include <codecvt>
#include <locale>

namespace wip {

inline std::filesystem::path join_paths(std::initializer_list<std::filesystem::path> parts) {
    std::filesystem::path result;
    for (const auto& p : parts) {
        result /= p;
    }
    return result;
}

enum class EnvKey {
    HomeDir,
    ConfigDir
};

inline std::optional<std::string> get_env(EnvKey key) {
    const char* name = nullptr;
#ifdef _WIN32
    switch (key) {
        case EnvKey::HomeDir: name = "USERPROFILE"; break;
        case EnvKey::ConfigDir: name = "APPDATA"; break;
    }
#else
    switch (key) {
        case EnvKey::HomeDir: name = "HOME"; break;
        case EnvKey::ConfigDir: name = "XDG_CONFIG_HOME"; break;
    }
#endif
    if (!name) {
        return std::nullopt;
    }
    if (const char* value = std::getenv(name)) {
        return std::string(value);
    }
    return std::nullopt;
}

inline std::u16string utf8_to_utf16(const std::string& input) {
    std::wstring_convert<std::codecvt_utf8_utf16<char16_t>, char16_t> conv;
    return conv.from_bytes(input);
}

inline std::string utf16_to_utf8(const std::u16string& input) {
    std::wstring_convert<std::codecvt_utf8_utf16<char16_t>, char16_t> conv;
    return conv.to_bytes(input);
}

} // namespace wip

