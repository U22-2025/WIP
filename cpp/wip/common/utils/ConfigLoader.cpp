#include "ConfigLoader.hpp"
#include <fstream>
#include <regex>
#include <cstdlib>
#include <stdexcept>

namespace {
inline void set_env_var(const char* key, const char* value) {
#ifdef _WIN32
    if (_putenv_s(key, value) != 0) {
#else
    if (setenv(key, value, 1) != 0) {
#endif
        throw std::runtime_error(std::string("Failed to set environment variable: ") + key);
    }
}
} // namespace

ConfigLoader::ConfigLoader(const std::string &config_path) {
    load_env();
    if (config_path.empty()) {
        config_path_ = std::filesystem::current_path() / "config.ini";
    } else {
        config_path_ = config_path;
    }
    load_config();
}

void ConfigLoader::load_env() {
    std::ifstream f(".env");
    if (!f.is_open()) return;
    std::string line;
    while (std::getline(f, line)) {
        auto pos = line.find('=');
        if (pos == std::string::npos) continue;
        std::string key = trim(line.substr(0,pos));
        std::string value = trim(line.substr(pos+1));
        if(!key.empty()) {
            set_env_var(key.c_str(), value.c_str());
        }
    }
}

void ConfigLoader::load_config() {
    if (!std::filesystem::exists(config_path_)) return;
    std::ifstream f(config_path_);
    std::string line;
    std::string section;
    while (std::getline(f, line)) {
        line = trim(line);
        if (line.empty() || line[0] == ';' || line[0] == '#') continue;
        if (line.front() == '[' && line.back() == ']') {
            section = line.substr(1, line.size()-2);
            continue;
        }
        auto pos = line.find('=');
        if (pos == std::string::npos) continue;
        std::string key = trim(line.substr(0,pos));
        std::string value = trim(line.substr(pos+1));
        config_[section][key] = value;
    }
    expand_env_vars();
}

void ConfigLoader::expand_env_vars() {
    std::regex pattern(R"(\$\{([^}]+)\})");
    for (auto &sec : config_) {
        for (auto &kv : sec.second) {
            std::string value = kv.second;
            std::smatch m;
            while (std::regex_search(value, m, pattern)) {
                const char *env = getenv(m[1].str().c_str());
                if (env) {
                    value.replace(m.position(0), m.length(0), env);
                } else {
                    value.replace(m.position(0), m.length(0), m[0].str());
                }
            }
            kv.second = value;
        }
    }
}

std::optional<std::string> ConfigLoader::get(const std::string &section, const std::string &key) const {
    auto sit = config_.find(section);
    if (sit == config_.end()) return std::nullopt;
    auto it = sit->second.find(key);
    if (it == sit->second.end()) return std::nullopt;
    return it->second;
}

std::optional<int> ConfigLoader::get_int(const std::string &section, const std::string &key) const {
    auto val = get(section, key);
    if (!val) return std::nullopt;
    try { return std::stoi(*val); } catch (...) { return std::nullopt; }
}

std::optional<bool> ConfigLoader::get_bool(const std::string &section, const std::string &key) const {
    auto val = get(section, key);
    if (!val) return std::nullopt;
    std::string lower = *val;
    for (auto &c: lower) c = ::tolower(c);
    if (lower == "true" || lower == "1" || lower == "yes") return true;
    if (lower == "false" || lower == "0" || lower == "no") return false;
    return std::nullopt;
}

std::map<std::string, std::string> ConfigLoader::get_section(const std::string &section) const {
    auto it = config_.find(section);
    if (it == config_.end()) return {};
    return it->second;
}

bool ConfigLoader::has_section(const std::string &section) const {
    return config_.count(section) > 0;
}

std::vector<std::string> ConfigLoader::sections() const {
    std::vector<std::string> result;
    for (const auto &p : config_) result.push_back(p.first);
    return result;
}

std::string ConfigLoader::trim(const std::string &s) {
    size_t start = s.find_first_not_of(" \t\r\n");
    if (start == std::string::npos) return "";
    size_t end = s.find_last_not_of(" \t\r\n");
    return s.substr(start, end - start + 1);
}

