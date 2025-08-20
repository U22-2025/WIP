#include "wiplib/compatibility/python_config.hpp"
#include <iostream>
#include <regex>
#include <cstdlib>
#include <filesystem>

namespace wiplib::compatibility {

bool PythonConfig::load_from_file(const std::string& file_path) {
    std::ifstream file(file_path);
    if (!file.is_open()) {
        return false;
    }
    
    std::stringstream buffer;
    buffer << file.rdbuf();
    return load_from_json(buffer.str());
}

bool PythonConfig::load_from_json(const std::string& json_content) {
    // 簡易JSONパーサー（実際の実装では nlohmann/json などを使用することを推奨）
    return parse_json_simple(json_content);
}

void PythonConfig::load_from_environment() {
    // Python版と同じ環境変数名
    auto env_host = get_env_var("WIPLIB_HOST");
    if (!env_host.empty()) {
        server_.host = env_host;
    }
    
    auto env_port = get_env_var("WIPLIB_PORT");
    if (!env_port.empty()) {
        try {
            server_.port = static_cast<uint16_t>(std::stoi(env_port));
        } catch (...) {
            // Invalid port, ignore
        }
    }
    
    auto env_debug = get_env_var("WIPLIB_DEBUG");
    if (!env_debug.empty()) {
        client_.debug = (env_debug == "1" || env_debug == "true" || env_debug == "True");
    }
    
    auto env_timeout = get_env_var("WIPLIB_TIMEOUT");
    if (!env_timeout.empty()) {
        try {
            server_.timeout_ms = std::stoi(env_timeout);
        } catch (...) {
            // Invalid timeout, ignore
        }
    }
    
    auto env_log_level = get_env_var("WIPLIB_LOG_LEVEL");
    if (!env_log_level.empty()) {
        logging_.level = env_log_level;
    }
    
    auto env_cache_enabled = get_env_var("WIPLIB_CACHE_ENABLED");
    if (!env_cache_enabled.empty()) {
        cache_.enabled = (env_cache_enabled == "1" || env_cache_enabled == "true" || env_cache_enabled == "True");
    }
}

bool PythonConfig::save_to_file(const std::string& file_path) const {
    std::ofstream file(file_path);
    if (!file.is_open()) {
        return false;
    }
    
    file << to_json();
    return file.good();
}

std::string PythonConfig::to_json() const {
    return generate_json();
}

std::string PythonConfig::validate() const {
    std::vector<std::string> errors;
    
    if (server_.host.empty()) {
        errors.push_back("サーバーホストが指定されていません");
    }
    
    if (server_.port == 0 || server_.port > 65535) {
        errors.push_back("無効なポート番号です: " + std::to_string(server_.port));
    }
    
    if (server_.timeout_ms <= 0) {
        errors.push_back("タイムアウト値は正の値である必要があります");
    }
    
    if (server_.retry_count < 0) {
        errors.push_back("リトライ回数は0以上である必要があります");
    }
    
    if (cache_.ttl_seconds <= 0) {
        errors.push_back("キャッシュTTLは正の値である必要があります");
    }
    
    if (cache_.max_entries <= 0) {
        errors.push_back("キャッシュエントリ数は正の値である必要があります");
    }
    
    // 座標の妥当性チェック
    if (client_.default_latitude.has_value()) {
        double lat = client_.default_latitude.value();
        if (lat < -90.0 || lat > 90.0) {
            errors.push_back("緯度は-90から90の範囲で指定してください");
        }
    }
    
    if (client_.default_longitude.has_value()) {
        double lon = client_.default_longitude.value();
        if (lon < -180.0 || lon > 180.0) {
            errors.push_back("経度は-180から180の範囲で指定してください");
        }
    }
    
    if (errors.empty()) {
        return "";
    }
    
    std::string result = "設定エラー:\n";
    for (const auto& error : errors) {
        result += "- " + error + "\n";
    }
    return result;
}

std::optional<std::string> PythonConfig::get_string(const std::string& key) const {
    // Python版と同じキー名でのマッピング
    if (key == "server.host") return server_.host;
    if (key == "logging.level") return logging_.level;
    if (key == "logging.format") return logging_.format;
    if (key == "client.user_agent") return client_.user_agent;
    
    auto it = additional_settings_.find(key);
    if (it != additional_settings_.end()) {
        return it->second;
    }
    
    return std::nullopt;
}

std::optional<int> PythonConfig::get_int(const std::string& key) const {
    if (key == "server.port") return static_cast<int>(server_.port);
    if (key == "server.timeout_ms") return server_.timeout_ms;
    if (key == "server.retry_count") return server_.retry_count;
    if (key == "cache.ttl_seconds") return cache_.ttl_seconds;
    if (key == "cache.max_entries") return cache_.max_entries;
    if (key == "logging.max_file_size_mb") return logging_.max_file_size_mb;
    if (key == "logging.backup_count") return logging_.backup_count;
    
    return std::nullopt;
}

std::optional<bool> PythonConfig::get_bool(const std::string& key) const {
    if (key == "server.use_ssl") return server_.use_ssl;
    if (key == "cache.enabled") return cache_.enabled;
    if (key == "cache.persistent") return cache_.persistent;
    if (key == "logging.console_output") return logging_.console_output;
    if (key == "client.debug") return client_.debug;
    
    return std::nullopt;
}

std::optional<double> PythonConfig::get_double(const std::string& key) const {
    if (key == "client.default_latitude") return client_.default_latitude;
    if (key == "client.default_longitude") return client_.default_longitude;
    
    return std::nullopt;
}

void PythonConfig::set_string(const std::string& key, const std::string& value) {
    if (key == "server.host") { server_.host = value; return; }
    if (key == "logging.level") { logging_.level = value; return; }
    if (key == "logging.format") { logging_.format = value; return; }
    if (key == "client.user_agent") { client_.user_agent = value; return; }
    
    additional_settings_[key] = value;
}

void PythonConfig::set_int(const std::string& key, int value) {
    if (key == "server.port") { server_.port = static_cast<uint16_t>(value); return; }
    if (key == "server.timeout_ms") { server_.timeout_ms = value; return; }
    if (key == "server.retry_count") { server_.retry_count = value; return; }
    if (key == "cache.ttl_seconds") { cache_.ttl_seconds = value; return; }
    if (key == "cache.max_entries") { cache_.max_entries = value; return; }
    if (key == "logging.max_file_size_mb") { logging_.max_file_size_mb = value; return; }
    if (key == "logging.backup_count") { logging_.backup_count = value; return; }
}

void PythonConfig::set_bool(const std::string& key, bool value) {
    if (key == "server.use_ssl") { server_.use_ssl = value; return; }
    if (key == "cache.enabled") { cache_.enabled = value; return; }
    if (key == "cache.persistent") { cache_.persistent = value; return; }
    if (key == "logging.console_output") { logging_.console_output = value; return; }
    if (key == "client.debug") { client_.debug = value; return; }
}

void PythonConfig::set_double(const std::string& key, double value) {
    if (key == "client.default_latitude") { client_.default_latitude = value; return; }
    if (key == "client.default_longitude") { client_.default_longitude = value; return; }
}

bool PythonConfig::parse_json_simple(const std::string& json) {
    // 簡易JSONパーサー実装（実際の実装では外部ライブラリを推奨）
    // ここでは基本的なパターンのみをサポート
    
    try {
        // サーバー設定
        std::regex host_regex(R"("host"\s*:\s*"([^"]*)")");
        std::smatch match;
        if (std::regex_search(json, match, host_regex)) {
            server_.host = match[1].str();
        }
        
        std::regex port_regex(R"("port"\s*:\s*(\d+))");
        if (std::regex_search(json, match, port_regex)) {
            server_.port = static_cast<uint16_t>(std::stoi(match[1].str()));
        }
        
        std::regex timeout_regex(R"("timeout_ms"\s*:\s*(\d+))");
        if (std::regex_search(json, match, timeout_regex)) {
            server_.timeout_ms = std::stoi(match[1].str());
        }
        
        // ログ設定
        std::regex log_level_regex(R"("level"\s*:\s*"([^"]*)")");
        if (std::regex_search(json, match, log_level_regex)) {
            logging_.level = match[1].str();
        }
        
        // キャッシュ設定
        std::regex cache_enabled_regex(R"("enabled"\s*:\s*(true|false))");
        if (std::regex_search(json, match, cache_enabled_regex)) {
            cache_.enabled = (match[1].str() == "true");
        }
        
        // デバッグ設定
        std::regex debug_regex(R"("debug"\s*:\s*(true|false))");
        if (std::regex_search(json, match, debug_regex)) {
            client_.debug = (match[1].str() == "true");
        }
        
        return true;
    } catch (...) {
        return false;
    }
}

std::string PythonConfig::generate_json() const {
    std::ostringstream oss;
    oss << "{\n";
    oss << "  \"server\": {\n";
    oss << "    \"host\": \"" << server_.host << "\",\n";
    oss << "    \"port\": " << server_.port << ",\n";
    oss << "    \"use_ssl\": " << (server_.use_ssl ? "true" : "false") << ",\n";
    oss << "    \"timeout_ms\": " << server_.timeout_ms << ",\n";
    oss << "    \"retry_count\": " << server_.retry_count << "\n";
    oss << "  },\n";
    
    oss << "  \"logging\": {\n";
    oss << "    \"level\": \"" << logging_.level << "\",\n";
    oss << "    \"format\": \"" << logging_.format << "\",\n";
    oss << "    \"console_output\": " << (logging_.console_output ? "true" : "false") << ",\n";
    oss << "    \"max_file_size_mb\": " << logging_.max_file_size_mb << ",\n";
    oss << "    \"backup_count\": " << logging_.backup_count << "\n";
    oss << "  },\n";
    
    oss << "  \"cache\": {\n";
    oss << "    \"enabled\": " << (cache_.enabled ? "true" : "false") << ",\n";
    oss << "    \"ttl_seconds\": " << cache_.ttl_seconds << ",\n";
    oss << "    \"max_entries\": " << cache_.max_entries << ",\n";
    oss << "    \"persistent\": " << (cache_.persistent ? "true" : "false") << "\n";
    oss << "  },\n";
    
    oss << "  \"client\": {\n";
    oss << "    \"debug\": " << (client_.debug ? "true" : "false") << ",\n";
    oss << "    \"user_agent\": \"" << client_.user_agent << "\"";
    
    if (client_.default_latitude.has_value()) {
        oss << ",\n    \"default_latitude\": " << client_.default_latitude.value();
    }
    if (client_.default_longitude.has_value()) {
        oss << ",\n    \"default_longitude\": " << client_.default_longitude.value();
    }
    if (client_.default_area_code.has_value()) {
        oss << ",\n    \"default_area_code\": \"" << client_.default_area_code.value() << "\"";
    }
    
    oss << "\n  }\n";
    oss << "}\n";
    
    return oss.str();
}

std::string PythonConfig::get_env_var(const std::string& key) const {
    const char* value = std::getenv(key.c_str());
    return value ? std::string(value) : std::string();
}

// グローバル設定インスタンス
static PythonConfig global_config_instance;

PythonConfig& get_global_config() {
    return global_config_instance;
}

std::string get_default_config_path() {
    // Python版と同じ設定ファイルパス
    #ifdef _WIN32
        const char* home = std::getenv("USERPROFILE");
        if (home) {
            return std::string(home) + "\\.wiplib\\config.json";
        }
        return "C:\\wiplib\\config.json";
    #else
        const char* home = std::getenv("HOME");
        if (home) {
            return std::string(home) + "/.wiplib/config.json";
        }
        return "/etc/wiplib/config.json";
    #endif
}

std::vector<std::string> get_config_search_paths() {
    std::vector<std::string> paths;
    
    // Python版と同じ検索順序
    paths.push_back("./config.json");                  // カレントディレクトリ
    paths.push_back("./wiplib_config.json");
    paths.push_back(get_default_config_path());        // ホームディレクトリ
    
    #ifndef _WIN32
        paths.push_back("/usr/local/etc/wiplib/config.json");
        paths.push_back("/etc/wiplib/config.json");
    #endif
    
    return paths;
}

} // namespace wiplib::compatibility