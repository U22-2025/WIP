#pragma once

#include <string>
#include <unordered_map>
#include <vector>
#include <variant>
#include <optional>
#include <memory>
#include <fstream>
#include <mutex>
#include <functional>
#include <chrono>
#include <atomic>
#include <thread>

namespace wiplib::utils {

/**
 * @brief 設定値の型
 */
using ConfigValue = std::variant<
    std::string,
    int64_t,
    double,
    bool,
    std::vector<std::string>
>;

/**
 * @brief 設定変更イベント
 */
struct ConfigChangeEvent {
    std::string key;
    ConfigValue old_value;
    ConfigValue new_value;
    std::chrono::steady_clock::time_point timestamp;
};

/**
 * @brief 設定変更リスナー
 */
using ConfigChangeListener = std::function<void(const ConfigChangeEvent&)>;

/**
 * @brief 設定ファイル形式
 */
enum class ConfigFormat {
    Auto,
    JSON,
    YAML,
    INI,
    TOML,
    XML
};

/**
 * @brief 設定ファイル読み込み・管理クラス
 */
class ConfigLoader {
public:
    /**
     * @brief コンストラクタ
     */
    ConfigLoader();
    
    ~ConfigLoader();
    
    /**
     * @brief 設定ファイルを読み込み
     * @param file_path ファイルパス
     * @param format ファイル形式（Autoで自動判定）
     * @return 成功時true
     */
    bool load_from_file(const std::string& file_path, ConfigFormat format = ConfigFormat::Auto);
    
    /**
     * @brief JSON文字列から設定を読み込み
     * @param json_content JSON文字列
     * @return 成功時true
     */
    bool load_from_json_string(const std::string& json_content);
    
    /**
     * @brief 環境変数から設定を読み込み
     * @param prefix 環境変数のプレフィックス（例："WIPLIB_"）
     * @return 読み込まれた設定数
     */
    size_t load_from_environment(const std::string& prefix = "");
    
    /**
     * @brief コマンドライン引数から設定を読み込み
     * @param argc 引数数
     * @param argv 引数配列
     * @return 読み込まれた設定数
     */
    size_t load_from_command_line(int argc, char* argv[]);
    
    /**
     * @brief 設定値を取得
     * @param key キー（ドット記法対応: "server.port"）
     * @param default_value デフォルト値
     * @return 設定値
     */
    template<typename T>
    T get(const std::string& key, const T& default_value = T{}) const;
    
    /**
     * @brief 文字列として設定値を取得
     * @param key キー
     * @param default_value デフォルト値
     * @return 設定値
     */
    std::string get_string(const std::string& key, const std::string& default_value = "") const;
    
    /**
     * @brief 整数として設定値を取得
     * @param key キー
     * @param default_value デフォルト値
     * @return 設定値
     */
    int64_t get_int(const std::string& key, int64_t default_value = 0) const;
    
    /**
     * @brief 浮動小数点数として設定値を取得
     * @param key キー
     * @param default_value デフォルト値
     * @return 設定値
     */
    double get_double(const std::string& key, double default_value = 0.0) const;
    
    /**
     * @brief 真偽値として設定値を取得
     * @param key キー
     * @param default_value デフォルト値
     * @return 設定値
     */
    bool get_bool(const std::string& key, bool default_value = false) const;
    
    /**
     * @brief 文字列配列として設定値を取得
     * @param key キー
     * @param default_value デフォルト値
     * @return 設定値
     */
    std::vector<std::string> get_string_array(const std::string& key, const std::vector<std::string>& default_value = {}) const;
    
    /**
     * @brief 設定値を設定
     * @param key キー
     * @param value 値
     */
    template<typename T>
    void set(const std::string& key, const T& value);
    
    /**
     * @brief 設定値の存在チェック
     * @param key キー
     * @return 存在する場合true
     */
    bool has(const std::string& key) const;
    
    /**
     * @brief 設定を削除
     * @param key キー
     * @return 削除された場合true
     */
    bool remove(const std::string& key);
    
    /**
     * @brief 全設定をクリア
     */
    void clear();
    
    /**
     * @brief 設定をファイルに保存
     * @param file_path ファイルパス
     * @param format ファイル形式
     * @return 成功時true
     */
    bool save_to_file(const std::string& file_path, ConfigFormat format = ConfigFormat::JSON) const;
    
    /**
     * @brief 設定をJSON文字列として取得
     * @return JSON文字列
     */
    std::string to_json_string() const;
    
    /**
     * @brief 全キー一覧を取得
     * @return キー一覧
     */
    std::vector<std::string> get_all_keys() const;
    
    /**
     * @brief プレフィックスに一致するキー一覧を取得
     * @param prefix プレフィックス
     * @return キー一覧
     */
    std::vector<std::string> get_keys_with_prefix(const std::string& prefix) const;
    
    /**
     * @brief ファイル変更監視を開始
     * @param file_path 監視するファイルパス
     * @param poll_interval ポーリング間隔
     * @return 成功時true
     */
    bool start_file_watching(const std::string& file_path, std::chrono::milliseconds poll_interval = std::chrono::milliseconds{1000});
    
    /**
     * @brief ファイル変更監視を停止
     */
    void stop_file_watching();
    
    /**
     * @brief 設定変更リスナーを追加
     * @param listener リスナー関数
     * @return リスナーID
     */
    size_t add_change_listener(ConfigChangeListener listener);
    
    /**
     * @brief 設定変更リスナーを削除
     * @param listener_id リスナーID
     * @return 削除された場合true
     */
    bool remove_change_listener(size_t listener_id);
    
    /**
     * @brief 設定バリデーションルールを追加
     * @param key キー
     * @param validator バリデーター関数
     */
    void add_validator(const std::string& key, std::function<bool(const ConfigValue&)> validator);
    
    /**
     * @brief 設定をバリデーション
     * @return すべて有効な場合true
     */
    bool validate() const;
    
    /**
     * @brief デフォルト設定を読み込み
     * @param defaults デフォルト設定マップ
     */
    void load_defaults(const std::unordered_map<std::string, ConfigValue>& defaults);
    
    /**
     * @brief 設定の階層構造を取得
     * @param prefix プレフィックス
     * @return 階層マップ
     */
    std::unordered_map<std::string, ConfigValue> get_section(const std::string& prefix) const;
    
    /**
     * @brief デバッグ情報を取得
     * @return デバッグ情報文字列
     */
    std::string get_debug_info() const;

private:
    mutable std::mutex config_mutex_;
    std::unordered_map<std::string, ConfigValue> config_data_;
    
    // ファイル監視
    std::atomic<bool> file_watching_enabled_{false};
    std::string watched_file_path_;
    std::chrono::milliseconds watch_poll_interval_{1000};
    std::unique_ptr<std::thread> file_watcher_thread_;
    std::chrono::steady_clock::time_point last_file_mod_time_{};
    
    // リスナー管理
    std::unordered_map<size_t, ConfigChangeListener> change_listeners_;
    size_t next_listener_id_{1};
    std::mutex listeners_mutex_;
    
    // バリデーション
    std::unordered_map<std::string, std::function<bool(const ConfigValue&)>> validators_;
    
    // プライベートメソッド
    ConfigFormat detect_format(const std::string& file_path) const;
    bool parse_json(const std::string& content);
    bool parse_yaml(const std::string& content);
    bool parse_ini(const std::string& content);
    bool parse_toml(const std::string& content);
    bool parse_xml(const std::string& content);
    
    std::string serialize_json() const;
    std::string serialize_yaml() const;
    std::string serialize_ini() const;
    
    void file_watcher_loop();
    void notify_change_listeners(const std::string& key, const ConfigValue& old_value, const ConfigValue& new_value);
    
    std::vector<std::string> split_key(const std::string& key) const;
    ConfigValue* find_value(const std::string& key);
    const ConfigValue* find_value(const std::string& key) const;
    
    template<typename T>
    T convert_value(const ConfigValue& value, const T& default_value) const;
    
    std::string to_string(const ConfigValue& value) const;
    ConfigValue from_string(const std::string& str) const;
};

/**
 * @brief グローバル設定マネージャー
 */
class GlobalConfig {
public:
    /**
     * @brief グローバル設定インスタンスを取得
     */
    static ConfigLoader& instance();
    
    /**
     * @brief 設定ファイルを読み込み
     */
    static bool load(const std::string& file_path, ConfigFormat format = ConfigFormat::Auto);
    
    /**
     * @brief 設定値を取得
     */
    template<typename T>
    static T get(const std::string& key, const T& default_value = T{});
    
    /**
     * @brief 設定値を設定
     */
    template<typename T>
    static void set(const std::string& key, const T& value);

private:
    static std::unique_ptr<ConfigLoader> instance_;
    static std::mutex instance_mutex_;
};

/**
 * @brief 設定ユーティリティ
 */
namespace config_utils {
    /**
     * @brief 環境変数名を正規化
     * @param key キー
     * @param prefix プレフィックス
     * @return 正規化された環境変数名
     */
    std::string normalize_env_var_name(const std::string& key, const std::string& prefix = "");
    
    /**
     * @brief 設定値を環境変数から取得
     * @param env_var_name 環境変数名
     * @return 設定値（見つからない場合nullopt）
     */
    std::optional<std::string> get_env_var(const std::string& env_var_name);
    
    /**
     * @brief 真偽値文字列を解析
     * @param str 文字列
     * @return 真偽値
     */
    bool parse_bool(const std::string& str);
    
    /**
     * @brief パスを展開（~や環境変数を解決）
     * @param path パス文字列
     * @return 展開されたパス
     */
    std::string expand_path(const std::string& path);
    
    /**
     * @brief 設定ファイルの妥当性をチェック
     * @param file_path ファイルパス
     * @return 妥当な場合true
     */
    bool validate_config_file(const std::string& file_path);
}

} // namespace wiplib::utils
