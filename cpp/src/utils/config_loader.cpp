#include "wiplib/utils/config_loader.hpp"
#include <sstream>
#include <filesystem>

#include "wiplib/utils/env.hpp"

namespace wiplib::utils {

ConfigLoader::ConfigLoader() = default;
ConfigLoader::~ConfigLoader() { stop_file_watching(); }

bool ConfigLoader::load_from_file(const std::string& file_path, ConfigFormat) {
    // Minimal: not parsing complex formats, just false to indicate unsupported
    (void)file_path; return false;
}

bool ConfigLoader::load_from_json_string(const std::string& json) { (void)json; return false; }

size_t ConfigLoader::load_from_environment(const std::string& prefix) {
    size_t n = 0; (void)prefix; return n;
}

size_t ConfigLoader::load_from_command_line(int argc, char* argv[]) {
    size_t n = 0; for (int i=1;i<argc;++i) { std::string a = argv[i]; auto eq = a.find('='); if (a.rfind("--",0)==0 && eq!=std::string::npos) { std::string k = a.substr(2, eq-2); std::string v = a.substr(eq+1); set(k, v); n++; } } return n;
}

std::string ConfigLoader::get_string(const std::string& key, const std::string& def) const { if (auto* v = find_value(key)) { try { return std::get<std::string>(*v); } catch (...) {} } return def; }
int64_t ConfigLoader::get_int(const std::string& key, int64_t def) const { if (auto* v = find_value(key)) { try { return std::get<int64_t>(*v); } catch (...) {} } return def; }
double ConfigLoader::get_double(const std::string& key, double def) const { if (auto* v = find_value(key)) { try { return std::get<double>(*v); } catch (...) {} } return def; }
bool ConfigLoader::get_bool(const std::string& key, bool def) const { if (auto* v = find_value(key)) { try { return std::get<bool>(*v); } catch (...) {} } return def; }
std::vector<std::string> ConfigLoader::get_string_array(const std::string& key, const std::vector<std::string>& def) const { if (auto* v = find_value(key)) { try { return std::get<std::vector<std::string>>(*v); } catch (...) {} } return def; }

bool ConfigLoader::has(const std::string& key) const { return find_value(key) != nullptr; }
bool ConfigLoader::remove(const std::string& key) { return config_data_.erase(key) > 0; }
void ConfigLoader::clear() { config_data_.clear(); }
bool ConfigLoader::save_to_file(const std::string& file_path, ConfigFormat) const { std::ofstream ofs(file_path); if (!ofs) return false; ofs << to_json_string(); return true; }
std::string ConfigLoader::to_json_string() const { std::ostringstream ss; ss << '{'; bool first=true; for (const auto& [k,v]: config_data_) { if (!first) ss << ','; first=false; ss << '"'<<k<<'"'<<":"<<'"'<<get_string(k,"")<<'"'; } ss << '}'; return ss.str(); }
std::vector<std::string> ConfigLoader::get_all_keys() const { std::vector<std::string> keys; keys.reserve(config_data_.size()); for (auto& [k,_]: config_data_) keys.push_back(k); return keys; }
std::vector<std::string> ConfigLoader::get_keys_with_prefix(const std::string& prefix) const { std::vector<std::string> keys; for (auto& [k,_]: config_data_) if (k.rfind(prefix,0)==0) keys.push_back(k); return keys; }
bool ConfigLoader::start_file_watching(const std::string& file_path, std::chrono::milliseconds) { watched_file_path_ = file_path; file_watching_enabled_ = true; return true; }
void ConfigLoader::stop_file_watching() { file_watching_enabled_ = false; if (file_watcher_thread_ && file_watcher_thread_->joinable()) file_watcher_thread_->join(); }
size_t ConfigLoader::add_change_listener(ConfigChangeListener) { return next_listener_id_++; }
bool ConfigLoader::remove_change_listener(size_t) { return true; }
void ConfigLoader::add_validator(const std::string&, std::function<bool(const ConfigValue&)>) {}
bool ConfigLoader::validate() const { return true; }
void ConfigLoader::load_defaults(const std::unordered_map<std::string, ConfigValue>& d) { for (auto& [k,v]: d) config_data_[k]=v; }
std::unordered_map<std::string, ConfigValue> ConfigLoader::get_section(const std::string& prefix) const { std::unordered_map<std::string, ConfigValue> out; for (auto& [k,v]: config_data_) if (k.rfind(prefix,0)==0) out[k]=v; return out; }
std::string ConfigLoader::get_debug_info() const { return "config_keys=" + std::to_string(config_data_.size()); }

ConfigFormat ConfigLoader::detect_format(const std::string&) const { return ConfigFormat::JSON; }
bool ConfigLoader::parse_json(const std::string&) { return false; }
bool ConfigLoader::parse_yaml(const std::string&) { return false; }
bool ConfigLoader::parse_ini(const std::string&) { return false; }
bool ConfigLoader::parse_toml(const std::string&) { return false; }
bool ConfigLoader::parse_xml(const std::string&) { return false; }
std::string ConfigLoader::serialize_json() const { return to_json_string(); }
void ConfigLoader::file_watcher_loop() {}
void ConfigLoader::notify_change_listeners(const std::string&, const ConfigValue&, const ConfigValue&) {}
std::vector<std::string> ConfigLoader::split_key(const std::string& k) const { return {k}; }
ConfigValue* ConfigLoader::find_value(const std::string& key) { auto it = config_data_.find(key); return it==config_data_.end()?nullptr:&it->second; }
const ConfigValue* ConfigLoader::find_value(const std::string& key) const { auto it = config_data_.find(key); return it==config_data_.end()?nullptr:&it->second; }
std::string ConfigLoader::to_string(const ConfigValue& v) const { try { return std::get<std::string>(v);} catch(...) {return "";} }
ConfigValue ConfigLoader::from_string(const std::string& s) const { return ConfigValue{s}; }

// GlobalConfig
std::unique_ptr<ConfigLoader> GlobalConfig::instance_;
std::mutex GlobalConfig::instance_mutex_;
ConfigLoader& GlobalConfig::instance() { std::lock_guard<std::mutex> lk(instance_mutex_); if (!instance_) instance_ = std::make_unique<ConfigLoader>(); return *instance_; }
bool GlobalConfig::load(const std::string& file_path, ConfigFormat f) { return instance().load_from_file(file_path, f); }

// utils
namespace config_utils {
std::string normalize_env_var_name(const std::string& k, const std::string& p) {
    std::string r = p;
    for (char c : k) r += (c == '.' ? '_' : std::toupper(c));
    return r;
}

std::optional<std::string> get_env_var(const std::string& n) {
    return getenv_os(n);
}

bool parse_bool(const std::string& s) {
    return s == "1" || s == "true" || s == "yes";
}

std::filesystem::path expand_path(const std::filesystem::path& p) {
    return p;
}

bool validate_config_file(const std::filesystem::path& fp) {
    return std::filesystem::exists(fp);
}
} // namespace config_utils

} // namespace wiplib::utils
