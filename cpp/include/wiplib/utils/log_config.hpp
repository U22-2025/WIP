#pragma once

#include <string>
#include <memory>
#include <vector>
#include <unordered_map>
#include <mutex>
#include <atomic>
#include <chrono>
#include <fstream>
#include <functional>
#include <queue>
#include <thread>
#include <filesystem>
// Optional: async logging. Define WIPLIB_NO_ASYNC_LOG to disable.
#ifndef WIPLIB_NO_ASYNC_LOG
# include <condition_variable>
#endif

namespace wiplib::utils {

/**
 * @brief ログレベル
 */
enum class LogLevel {
    Trace = 0,
    Debug = 1,
    Info = 2,
    Warning = 3,
    Error = 4,
    Critical = 5,
    Off = 6
};

/**
 * @brief ログエントリ
 */
struct LogEntry {
    LogLevel level;
    std::string logger_name;
    std::string message;
    std::chrono::system_clock::time_point timestamp;
    std::string thread_id;
    std::string file;
    int line = 0;
    std::string function;
    std::unordered_map<std::string, std::string> metadata;
};

/**
 * @brief ログシンク（出力先）
 */
class LogSink {
public:
    virtual ~LogSink() = default;
    
    /**
     * @brief ログエントリを書き込み
     * @param entry ログエントリ
     */
    virtual void write(const LogEntry& entry) = 0;
    
    /**
     * @brief ログをフラッシュ
     */
    virtual void flush() {}
    
    /**
     * @brief シンクを閉じる
     */
    virtual void close() {}
    
    /**
     * @brief 最小ログレベルを設定
     * @param level 最小レベル
     */
    void set_min_level(LogLevel level) { min_level_ = level; }
    
    /**
     * @brief 最小ログレベルを取得
     * @return 最小レベル
     */
    LogLevel get_min_level() const { return min_level_; }

protected:
    LogLevel min_level_ = LogLevel::Info;
};

/**
 * @brief コンソールログシンク
 */
class ConsoleLogSink : public LogSink {
public:
    explicit ConsoleLogSink(bool use_colors = true);
    void write(const LogEntry& entry) override;

private:
    bool use_colors_;
    std::mutex console_mutex_;
    std::string colorize(LogLevel level, const std::string& text) const;
};

/**
 * @brief ファイルログシンク
 */
class FileLogSink : public LogSink {
public:
    /**
     * @brief コンストラクタ
     * @param file_path ファイルパス
     * @param max_file_size 最大ファイルサイズ（0で無制限）
     * @param max_files 最大ファイル数（ローテーション用）
     */
    explicit FileLogSink(const std::filesystem::path& file_path,
                        size_t max_file_size = 10 * 1024 * 1024,  // 10MB
                        size_t max_files = 5);
    
    ~FileLogSink();
    
    void write(const LogEntry& entry) override;
    void flush() override;
    void close() override;

private:
    std::filesystem::path file_path_;
    size_t max_file_size_;
    size_t max_files_;
    std::unique_ptr<std::ofstream> file_stream_;
    std::mutex file_mutex_;
    size_t current_file_size_{0};
    
    void rotate_file();
    std::filesystem::path get_rotated_file_path(size_t index) const;
};

/**
 * @brief ネットワークログシンク
 */
class NetworkLogSink : public LogSink {
public:
    /**
     * @brief コンストラクタ
     * @param host ホスト
     * @param port ポート
     * @param protocol プロトコル（"tcp" or "udp"）
     */
    explicit NetworkLogSink(const std::string& host, uint16_t port, const std::string& protocol = "tcp");
    
    ~NetworkLogSink();
    
    void write(const LogEntry& entry) override;
    void flush() override;
    void close() override;

private:
    std::string host_;
    uint16_t port_;
    std::string protocol_;
    int socket_fd_{-1};
    std::mutex network_mutex_;
    
    bool connect_socket();
    void disconnect_socket();
    std::string serialize_entry(const LogEntry& entry) const;
};

/**
 * @brief 統一ログフォーマッター
 */
class UnifiedLogFormatter {
public:
    /**
     * @brief フォーマット設定
     */
    struct FormatConfig {
        std::string timestamp_format = "%Y-%m-%d %H:%M:%S";
        bool include_thread_id = true;
        bool include_file_info = false;
        bool include_function = false;
        bool include_metadata = false;
        std::string field_separator = " | ";
        std::string metadata_prefix = "[";
        std::string metadata_suffix = "]";
    };
    
    /**
     * @brief コンストラクタ
     * @param config フォーマット設定
     */
    UnifiedLogFormatter();
    explicit UnifiedLogFormatter(const FormatConfig& config);
    
    /**
     * @brief ログエントリをフォーマット
     * @param entry ログエントリ
     * @return フォーマットされた文字列
     */
    std::string format(const LogEntry& entry) const;
    
    /**
     * @brief JSONフォーマットで出力
     * @param entry ログエントリ
     * @return JSON文字列
     */
    std::string format_json(const LogEntry& entry) const;
    
    /**
     * @brief 設定を更新
     * @param new_config 新しい設定
     */
    void update_config(const FormatConfig& new_config);

private:
    FormatConfig config_;
    mutable std::mutex format_mutex_;
    
    std::string level_to_string(LogLevel level) const;
    std::string format_timestamp(const std::chrono::system_clock::time_point& timestamp) const;
    std::string format_metadata(const std::unordered_map<std::string, std::string>& metadata) const;
};

/**
 * @brief ロガークラス
 */
class Logger {
public:
    /**
     * @brief コンストラクタ
     * @param name ロガー名
     */
    explicit Logger(const std::string& name);
    
    ~Logger();
    
    /**
     * @brief ログシンクを追加
     * @param sink ログシンク
     */
    void add_sink(std::shared_ptr<LogSink> sink);
    
    /**
     * @brief ログシンクを削除
     * @param sink ログシンク
     */
    void remove_sink(std::shared_ptr<LogSink> sink);
    
    /**
     * @brief 全ログシンクをクリア
     */
    void clear_sinks();
    
    /**
     * @brief 最小ログレベルを設定
     * @param level 最小レベル
     */
    void set_level(LogLevel level);
    
    /**
     * @brief 最小ログレベルを取得
     * @return 最小レベル
     */
    LogLevel get_level() const;
    
    /**
     * @brief ログを出力
     * @param level ログレベル
     * @param message メッセージ
     * @param file ファイル名
     * @param line 行番号
     * @param function 関数名
     */
    void log(LogLevel level, const std::string& message, 
             const std::string& file = "", int line = 0, const std::string& function = "");
    
    /**
     * @brief メタデータ付きログを出力
     * @param level ログレベル
     * @param message メッセージ
     * @param metadata メタデータ
     * @param file ファイル名
     * @param line 行番号
     * @param function 関数名
     */
    void log_with_metadata(LogLevel level, const std::string& message,
                          const std::unordered_map<std::string, std::string>& metadata,
                          const std::string& file = "", int line = 0, const std::string& function = "");
    
    /**
     * @brief トレースログ
     */
    void trace(const std::string& message, const std::string& file = "", int line = 0, const std::string& function = "");
    
    /**
     * @brief デバッグログ
     */
    void debug(const std::string& message, const std::string& file = "", int line = 0, const std::string& function = "");
    
    /**
     * @brief 情報ログ
     */
    void info(const std::string& message, const std::string& file = "", int line = 0, const std::string& function = "");
    
    /**
     * @brief 警告ログ
     */
    void warning(const std::string& message, const std::string& file = "", int line = 0, const std::string& function = "");
    
    /**
     * @brief エラーログ
     */
    void error(const std::string& message, const std::string& file = "", int line = 0, const std::string& function = "");
    
    /**
     * @brief 重大ログ
     */
    void critical(const std::string& message, const std::string& file = "", int line = 0, const std::string& function = "");
    
    /**
     * @brief フォーマット済みログを出力
     */
    template<typename... Args>
    void log_formatted(LogLevel level, const std::string& format, Args&&... args);
    
    /**
     * @brief ログをフラッシュ
     */
    void flush();
    
    /**
     * @brief 非同期ログを有効化/無効化
     * @param enabled 非同期有効フラグ
     * @param queue_size キューサイズ
     */
    void set_async_logging(bool enabled, size_t queue_size = 1000);
    
    /**
     * @brief ロガー名を取得
     * @return ロガー名
     */
    std::string get_name() const;

private:
    std::string name_;
    std::vector<std::shared_ptr<LogSink>> sinks_;
    std::mutex sinks_mutex_;
    LogLevel min_level_;
    
    // 非同期ログ（オプション）
    std::atomic<bool> async_enabled_{false};
#ifndef WIPLIB_NO_ASYNC_LOG
    std::queue<LogEntry> log_queue_;
    std::mutex queue_mutex_;
    std::condition_variable queue_cv_;
    std::unique_ptr<std::thread> async_thread_;
    std::atomic<bool> running_{true};
#endif
    
    void write_to_sinks(const LogEntry& entry);
#ifndef WIPLIB_NO_ASYNC_LOG
    void async_worker();
#endif
    std::string get_thread_id() const;
};

/**
 * @brief ログマネージャー
 */
class LogManager {
public:
    /**
     * @brief シングルトンインスタンスを取得
     */
    static LogManager& instance();
    
    /**
     * @brief ロガーを取得（存在しない場合は作成）
     * @param name ロガー名
     * @return ロガー
     */
    std::shared_ptr<Logger> get_logger(const std::string& name);
    
    /**
     * @brief デフォルトロガーを取得
     * @return デフォルトロガー
     */
    std::shared_ptr<Logger> get_default_logger();
    
    /**
     * @brief ロガーを削除
     * @param name ロガー名
     */
    void remove_logger(const std::string& name);
    
    /**
     * @brief 全ロガーをクリア
     */
    void clear_loggers();
    
    /**
     * @brief グローバルレベルを設定
     * @param level グローバルレベル
     */
    void set_global_level(LogLevel level);
    
    /**
     * @brief グローバルフォーマッターを設定
     * @param formatter フォーマッター
     */
    void set_global_formatter(std::shared_ptr<UnifiedLogFormatter> formatter);
    
    /**
     * @brief グローバルシンクを追加
     * @param sink ログシンク
     */
    void add_global_sink(std::shared_ptr<LogSink> sink);
    
    /**
     * @brief 全ロガーをフラッシュ
     */
    void flush_all();
    
    /**
     * @brief シャットダウン
     */
    void shutdown();

private:
    std::unordered_map<std::string, std::shared_ptr<Logger>> loggers_;
    std::mutex loggers_mutex_;
    LogLevel global_level_{LogLevel::Info};
    std::shared_ptr<UnifiedLogFormatter> global_formatter_;
    std::vector<std::shared_ptr<LogSink>> global_sinks_;
    
    LogManager() = default;
    ~LogManager();
};

/**
 * @brief ログマクロ
 */
#define WIPLIB_LOG_TRACE(logger, message) \
    logger->trace(message, __FILE__, __LINE__, __FUNCTION__)

#define WIPLIB_LOG_DEBUG(logger, message) \
    logger->debug(message, __FILE__, __LINE__, __FUNCTION__)

#define WIPLIB_LOG_INFO(logger, message) \
    logger->info(message, __FILE__, __LINE__, __FUNCTION__)

#define WIPLIB_LOG_WARNING(logger, message) \
    logger->warning(message, __FILE__, __LINE__, __FUNCTION__)

#define WIPLIB_LOG_ERROR(logger, message) \
    logger->error(message, __FILE__, __LINE__, __FUNCTION__)

#define WIPLIB_LOG_CRITICAL(logger, message) \
    logger->critical(message, __FILE__, __LINE__, __FUNCTION__)

/**
 * @brief ログユーティリティ
 */
namespace log_utils {
    /**
     * @brief ログレベルを文字列から解析
     * @param level_str レベル文字列
     * @return ログレベル
     */
    LogLevel parse_log_level(const std::string& level_str);
    
    /**
     * @brief ログレベルを文字列に変換
     * @param level ログレベル
     * @return レベル文字列
     */
    std::string log_level_to_string(LogLevel level);
    
    /**
     * @brief ファイルローテーション設定を初期化
     * @param base_path ベースパス
     * @param max_size 最大サイズ
     * @param max_files 最大ファイル数
     * @return ファイルシンク
     */
    std::shared_ptr<FileLogSink> create_rotating_file_sink(
        const std::filesystem::path& base_path,
        size_t max_size = 10 * 1024 * 1024,
        size_t max_files = 5
    );
    
    /**
     * @brief 基本ログ設定を初期化
     * @param level 最小レベル
     * @param log_to_console コンソール出力有効
     * @param log_file ログファイルパス（空文字で無効）
     */
    void setup_basic_logging(LogLevel level = LogLevel::Info,
                            bool log_to_console = true,
                            const std::filesystem::path& log_file = {});
}

} // namespace wiplib::utils
