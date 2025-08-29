#pragma once

#include <string>
#include <optional>
#include <map>
#include <vector>
#include <fstream>
#include <sstream>

namespace wiplib::compatibility {

/**
 * @brief Python互換設定管理クラス
 * Python版のconfig.jsonと同一の形式をサポート
 */
class PythonConfig {
public:
    struct ServerSettings {
        std::string host = "wip.ncc.onl";
        uint16_t port = 4110;
        bool use_ssl = false;
        std::optional<std::string> auth_token{};
        int timeout_ms = 5000;
        int retry_count = 3;
    };
    
    struct LoggingSettings {
        std::string level = "INFO";
        std::string format = "[%(asctime)s] %(levelname)s: %(message)s";
        std::optional<std::string> file_path{};
        bool console_output = true;
        int max_file_size_mb = 10;
        int backup_count = 5;
    };
    
    struct CacheSettings {
        bool enabled = true;
        int ttl_seconds = 300;
        int max_entries = 1000;
        std::optional<std::string> cache_dir{};
        bool persistent = false;
    };
    
    struct ClientSettings {
        std::optional<double> default_latitude{};
        std::optional<double> default_longitude{};
        std::optional<std::string> default_area_code{};
        bool debug = false;
        std::string user_agent = "WIPLib-CPP/1.0";
    };

public:
    PythonConfig() = default;
    
    /**
     * @brief Python形式のJSONファイルから設定を読み込み
     * @param file_path 設定ファイルのパス
     * @return 読み込み成功時true
     */
    bool load_from_file(const std::string& file_path);
    
    /**
     * @brief JSON文字列から設定を読み込み
     * @param json_content JSON文字列
     * @return 読み込み成功時true
     */
    bool load_from_json(const std::string& json_content);
    
    /**
     * @brief 環境変数から設定をオーバーライド
     * Python版と同じ環境変数名をサポート
     */
    void load_from_environment();
    
    /**
     * @brief Python形式のJSONファイルに設定を保存
     * @param file_path 保存先ファイルのパス
     * @return 保存成功時true
     */
    bool save_to_file(const std::string& file_path) const;
    
    /**
     * @brief JSON文字列として設定を出力
     * @return JSON形式の設定文字列
     */
    std::string to_json() const;
    
    /**
     * @brief 設定の妥当性チェック
     * @return エラーメッセージ（空の場合は正常）
     */
    std::string validate() const;

    // アクセサ
    const ServerSettings& server() const { return server_; }
    ServerSettings& server() { return server_; }
    
    const LoggingSettings& logging() const { return logging_; }
    LoggingSettings& logging() { return logging_; }
    
    const CacheSettings& cache() const { return cache_; }
    CacheSettings& cache() { return cache_; }
    
    const ClientSettings& client() const { return client_; }
    ClientSettings& client() { return client_; }
    
    /**
     * @brief Python版と同じキー名でのアクセス
     */
    std::optional<std::string> get_string(const std::string& key) const;
    std::optional<int> get_int(const std::string& key) const;
    std::optional<bool> get_bool(const std::string& key) const;
    std::optional<double> get_double(const std::string& key) const;
    
    void set_string(const std::string& key, const std::string& value);
    void set_int(const std::string& key, int value);
    void set_bool(const std::string& key, bool value);
    void set_double(const std::string& key, double value);

private:
    ServerSettings server_;
    LoggingSettings logging_;
    CacheSettings cache_;
    ClientSettings client_;
    
    // 追加の設定項目（Python版との互換性のため）
    std::map<std::string, std::string> additional_settings_;
    
    /**
     * @brief 簡易JSONパーサー（Python版JSONと互換性のため）
     */
    bool parse_json_simple(const std::string& json);
    
    /**
     * @brief 簡易JSON生成器
     */
    std::string generate_json() const;
    
    /**
     * @brief 環境変数名をPython版と統一
     */
    std::string get_env_var(const std::string& key) const;
};

/**
 * @brief グローバル設定インスタンス（Python版のシングルトンパターンに対応）
 */
PythonConfig& get_global_config();

/**
 * @brief デフォルト設定ファイルパスを取得（Python版と同じ場所）
 */
std::string get_default_config_path();

/**
 * @brief Python版と同じ設定ファイル検索パス
 */
std::vector<std::string> get_config_search_paths();

} // namespace wiplib::compatibility
