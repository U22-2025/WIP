#pragma once
#include <string>
#include <map>
#include <optional>
#include <vector>
#include <filesystem>

class ConfigLoader {
public:
    explicit ConfigLoader(const std::string &config_path = "");

    std::optional<std::string> get(const std::string &section, const std::string &key) const;
    std::optional<int> get_int(const std::string &section, const std::string &key) const;
    std::optional<bool> get_bool(const std::string &section, const std::string &key) const;
    std::map<std::string, std::string> get_section(const std::string &section) const;
    bool has_section(const std::string &section) const;
    std::vector<std::string> sections() const;

private:
    void load_env();
    void load_config();
    void expand_env_vars();
    static void set_env_var(const std::string &key, const std::string &value);
    static std::string trim(const std::string &s);

    std::filesystem::path config_path_;
    std::map<std::string, std::map<std::string, std::string>> config_;
};
