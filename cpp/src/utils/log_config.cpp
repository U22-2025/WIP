#include "wiplib/utils/log_config.hpp"
#include <iostream>
#include <sstream>
#include <iomanip>
#include <ctime>

namespace wiplib::utils {

// ConsoleLogSink
ConsoleLogSink::ConsoleLogSink(bool use_colors) : use_colors_(use_colors) {}

std::string ConsoleLogSink::colorize(LogLevel level, const std::string& text) const {
    if (!use_colors_) return text;
    const char* c = "\033[0m";
    switch (level) {
        case LogLevel::Trace: c = "\033[37m"; break;
        case LogLevel::Debug: c = "\033[36m"; break;
        case LogLevel::Info: c = "\033[32m"; break;
        case LogLevel::Warning: c = "\033[33m"; break;
        case LogLevel::Error: c = "\033[31m"; break;
        case LogLevel::Critical: c = "\033[35m"; break;
        default: break;
    }
    return std::string(c) + text + "\033[0m";
}

void ConsoleLogSink::write(const LogEntry& entry) {
    std::lock_guard<std::mutex> lk(console_mutex_);
    std::time_t tt = std::chrono::system_clock::to_time_t(entry.timestamp);
    std::tm tm{};
#if defined(_WIN32)
    localtime_s(&tm, &tt);
#else
    localtime_r(&tt, &tm);
#endif
    std::ostringstream ss;
    ss << std::put_time(&tm, "%F %T") << " [" << entry.logger_name << "] " << entry.message;
    std::cout << colorize(entry.level, ss.str()) << std::endl;
}

// FileLogSink
FileLogSink::FileLogSink(const std::string& file_path, size_t max_file_size, size_t max_files)
    : file_path_(file_path), max_file_size_(max_file_size), max_files_(max_files) {
    file_stream_ = std::make_unique<std::ofstream>(file_path_, std::ios::app);
}

FileLogSink::~FileLogSink() { close(); }

void FileLogSink::write(const LogEntry& entry) {
    std::lock_guard<std::mutex> lk(file_mutex_);
    if (!file_stream_ || !file_stream_->is_open()) return;
    std::time_t tt = std::chrono::system_clock::to_time_t(entry.timestamp);
    std::tm tm{};
#if defined(_WIN32)
    localtime_s(&tm, &tt);
#else
    localtime_r(&tt, &tm);
#endif
    (*file_stream_) << std::put_time(&tm, "%F %T") << " [" << entry.logger_name << "] " << entry.message << '\n';
    current_file_size_ += entry.message.size() + 32;
    if (max_file_size_ && current_file_size_ > max_file_size_) rotate_file();
}

void FileLogSink::flush() { if (file_stream_) file_stream_->flush(); }

void FileLogSink::close() { if (file_stream_) { file_stream_->flush(); file_stream_->close(); } }

void FileLogSink::rotate_file() {
    if (!file_stream_) return;
    file_stream_->close();
    for (size_t i = max_files_; i-- > 1;) {
        std::string src = get_rotated_file_path(i-1);
        std::string dst = get_rotated_file_path(i);
        std::remove(dst.c_str());
        std::rename(src.c_str(), dst.c_str());
    }
    std::rename(file_path_.c_str(), get_rotated_file_path(0).c_str());
    file_stream_ = std::make_unique<std::ofstream>(file_path_, std::ios::trunc);
    current_file_size_ = 0;
}

std::string FileLogSink::get_rotated_file_path(size_t index) const {
    return file_path_ + "." + std::to_string(index + 1);
}

// NetworkLogSink (minimal TCP not implemented, just noop)
NetworkLogSink::NetworkLogSink(const std::string& host, uint16_t port, const std::string& protocol)
    : host_(host), port_(port), protocol_(protocol) {}
NetworkLogSink::~NetworkLogSink() { close(); }
bool NetworkLogSink::connect_socket() { return false; }
void NetworkLogSink::disconnect_socket() {}
std::string NetworkLogSink::serialize_entry(const LogEntry& e) const { return e.message; }
void NetworkLogSink::write(const LogEntry& entry) { (void)entry; }
void NetworkLogSink::flush() {}
void NetworkLogSink::close() {}

// UnifiedLogFormatter
UnifiedLogFormatter::UnifiedLogFormatter() : config_{} {}
UnifiedLogFormatter::UnifiedLogFormatter(const FormatConfig& config) : config_(config) {}

std::string UnifiedLogFormatter::level_to_string(LogLevel l) const {
    switch (l) { case LogLevel::Trace: return "TRACE"; case LogLevel::Debug: return "DEBUG"; case LogLevel::Info: return "INFO"; case LogLevel::Warning: return "WARN"; case LogLevel::Error: return "ERROR"; case LogLevel::Critical: return "CRIT"; default: return "OFF"; }
}

std::string UnifiedLogFormatter::format_timestamp(const std::chrono::system_clock::time_point& tp) const {
    std::time_t tt = std::chrono::system_clock::to_time_t(tp);
    std::tm tm{};
#if defined(_WIN32)
    localtime_s(&tm, &tt);
#else
    localtime_r(&tt, &tm);
#endif
    char buf[64]; std::strftime(buf, sizeof(buf), config_.timestamp_format.c_str(), &tm);
    return std::string(buf);
}

std::string UnifiedLogFormatter::format_metadata(const std::unordered_map<std::string, std::string>& md) const {
    if (!config_.include_metadata || md.empty()) return "";
    std::ostringstream ss; ss << config_.metadata_prefix;
    bool first = true; for (const auto& [k,v] : md) { if (!first) ss << ','; first=false; ss << k << '=' << v; }
    ss << config_.metadata_suffix; return ss.str();
}

std::string UnifiedLogFormatter::format(const LogEntry& e) const {
    std::lock_guard<std::mutex> lk(format_mutex_);
    std::ostringstream ss;
    ss << format_timestamp(e.timestamp) << config_.field_separator << level_to_string(e.level)
       << config_.field_separator << e.logger_name << config_.field_separator << e.message;
    auto md = format_metadata(e.metadata); if (!md.empty()) ss << config_.field_separator << md;
    return ss.str();
}

std::string UnifiedLogFormatter::format_json(const LogEntry& e) const {
    std::ostringstream ss; ss << '{' << "\"time\":\"" << format_timestamp(e.timestamp) << "\"," << "\"level\":\"" << level_to_string(e.level) << "\"," << "\"logger\":\"" << e.logger_name << "\"," << "\"msg\":\"" << e.message << "\"}"; return ss.str();
}

void UnifiedLogFormatter::update_config(const FormatConfig& cfg) { std::lock_guard<std::mutex> lk(format_mutex_); config_ = cfg; }

// Logger
Logger::Logger(const std::string& name) : name_(name), min_level_(LogLevel::Info) {}
Logger::~Logger() { running_ = false; if (async_thread_ && async_thread_->joinable()) async_thread_->join(); }
void Logger::add_sink(std::shared_ptr<LogSink> s) { std::lock_guard<std::mutex> lk(sinks_mutex_); sinks_.push_back(std::move(s)); }
void Logger::remove_sink(std::shared_ptr<LogSink> s) { std::lock_guard<std::mutex> lk(sinks_mutex_); sinks_.erase(std::remove(sinks_.begin(), sinks_.end(), s), sinks_.end()); }
void Logger::clear_sinks() { std::lock_guard<std::mutex> lk(sinks_mutex_); sinks_.clear(); }
void Logger::set_level(LogLevel l) { min_level_ = l; }
LogLevel Logger::get_level() const { return min_level_; }
void Logger::write_to_sinks(const LogEntry& e) { std::lock_guard<std::mutex> lk(sinks_mutex_); for (auto& s : sinks_) if (e.level >= s->get_min_level()) s->write(e); }
std::string Logger::get_thread_id() const { std::ostringstream ss; ss << std::this_thread::get_id(); return ss.str(); }

void Logger::log(LogLevel level, const std::string& message, const std::string& file, int line, const std::string& function) {
    if (level < min_level_) return;
    LogEntry e{level, name_, message, std::chrono::system_clock::now(), get_thread_id(), file, line, function, {}};
    if (async_enabled_) {
        std::lock_guard<std::mutex> lk(queue_mutex_); log_queue_.push(e); queue_cv_.notify_one();
    } else {
        write_to_sinks(e);
    }
}

void Logger::log_with_metadata(LogLevel level, const std::string& message, const std::unordered_map<std::string, std::string>& metadata, const std::string& file, int line, const std::string& function) {
    if (level < min_level_) return; LogEntry e{level, name_, message, std::chrono::system_clock::now(), get_thread_id(), file, line, function, metadata}; if (async_enabled_) { std::lock_guard<std::mutex> lk(queue_mutex_); log_queue_.push(e); queue_cv_.notify_one(); } else { write_to_sinks(e);} }

void Logger::trace(const std::string& m, const std::string& f, int l, const std::string& fn) { log(LogLevel::Trace, m, f, l, fn); }
void Logger::debug(const std::string& m, const std::string& f, int l, const std::string& fn) { log(LogLevel::Debug, m, f, l, fn); }
void Logger::info(const std::string& m, const std::string& f, int l, const std::string& fn) { log(LogLevel::Info, m, f, l, fn); }
void Logger::warning(const std::string& m, const std::string& f, int l, const std::string& fn) { log(LogLevel::Warning, m, f, l, fn); }
void Logger::error(const std::string& m, const std::string& f, int l, const std::string& fn) { log(LogLevel::Error, m, f, l, fn); }
void Logger::critical(const std::string& m, const std::string& f, int l, const std::string& fn) { log(LogLevel::Critical, m, f, l, fn); }

void Logger::flush() { std::lock_guard<std::mutex> lk(sinks_mutex_); for (auto& s : sinks_) s->flush(); }

void Logger::set_async_logging(bool enabled, size_t) { async_enabled_ = enabled; if (enabled && !async_thread_) { async_thread_ = std::make_unique<std::thread>(&Logger::async_worker, this); } }

std::string Logger::get_name() const { return name_; }

void Logger::async_worker() {
    while (running_) {
        std::unique_lock<std::mutex> lk(queue_mutex_);
        queue_cv_.wait_for(lk, std::chrono::milliseconds(200), [this]{ return !log_queue_.empty() || !running_; });
        if (!running_) break;
        while (!log_queue_.empty()) { auto e = log_queue_.front(); log_queue_.pop(); lk.unlock(); write_to_sinks(e); lk.lock(); }
    }
}

// LogManager
LogManager& LogManager::instance() { static LogManager inst; return inst; }
LogManager::~LogManager() { shutdown(); }
std::shared_ptr<Logger> LogManager::get_logger(const std::string& name) { std::lock_guard<std::mutex> lk(loggers_mutex_); auto it = loggers_.find(name); if (it != loggers_.end()) return it->second; auto l = std::make_shared<Logger>(name); if (global_formatter_ && !global_sinks_.empty()) { for (auto& s : global_sinks_) l->add_sink(s); } loggers_[name] = l; return l; }
std::shared_ptr<Logger> LogManager::get_default_logger() { return get_logger("default"); }
void LogManager::remove_logger(const std::string& name) { std::lock_guard<std::mutex> lk(loggers_mutex_); loggers_.erase(name); }
void LogManager::clear_loggers() { std::lock_guard<std::mutex> lk(loggers_mutex_); loggers_.clear(); }
void LogManager::set_global_level(LogLevel l) { global_level_ = l; }
void LogManager::set_global_formatter(std::shared_ptr<UnifiedLogFormatter> fmt) { global_formatter_ = std::move(fmt); }
void LogManager::add_global_sink(std::shared_ptr<LogSink> sink) { std::lock_guard<std::mutex> lk(loggers_mutex_); global_sinks_.push_back(std::move(sink)); }
void LogManager::flush_all() { std::lock_guard<std::mutex> lk(loggers_mutex_); for (auto& [n,l] : loggers_) l->flush(); }
void LogManager::shutdown() { flush_all(); }

// log_utils
LogLevel log_utils::parse_log_level(const std::string& s) { if (s=="trace") return LogLevel::Trace; if (s=="debug") return LogLevel::Debug; if (s=="info") return LogLevel::Info; if (s=="warn"||s=="warning") return LogLevel::Warning; if (s=="error") return LogLevel::Error; if (s=="critical"||s=="fatal") return LogLevel::Critical; return LogLevel::Info; }
std::string log_utils::log_level_to_string(LogLevel l) { switch(l){case LogLevel::Trace:return"trace";case LogLevel::Debug:return"debug";case LogLevel::Info:return"info";case LogLevel::Warning:return"warning";case LogLevel::Error:return"error";case LogLevel::Critical:return"critical";default:return"off";} }

} // namespace wiplib::utils
