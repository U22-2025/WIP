#include "wiplib/utils/file_cache.hpp"
#include <filesystem>
#include <fstream>

namespace fs = std::filesystem;
namespace wiplib::utils {

FileCache::FileCache(const std::string& dir, size_t max_size, std::chrono::seconds ttl)
    : cache_dir_(dir), max_size_(max_size), default_ttl_(ttl) { ensure_cache_directory(); }
FileCache::~FileCache() { if (cleanup_thread_ && cleanup_thread_->joinable()) { running_ = false; cleanup_thread_->join(); } }

bool FileCache::put(const std::string& key, const std::vector<uint8_t>& data, std::optional<std::chrono::seconds> ttl) {
    if (!ensure_cache_directory()) return false; std::string path = generate_file_path(key); if (!write_data_to_file(path, data)) return false; std::lock_guard<std::mutex> lk(entries_mutex_); FileCacheEntry e{key, path, std::chrono::steady_clock::now(), std::chrono::steady_clock::now(), ttl.value_or(default_ttl_), data.size(), {}}; entries_[key] = e; stats_.writes++; stats_.total_entries = entries_.size(); stats_.total_disk_usage = calculate_total_disk_usage(); return true;
}

bool FileCache::put_string(const std::string& key, const std::string& data, std::optional<std::chrono::seconds> ttl) { return put(key, std::vector<uint8_t>(data.begin(), data.end()), ttl); }
bool FileCache::put_file(const std::string& key, const std::string& src, std::optional<std::chrono::seconds> ttl) { std::ifstream ifs(src, std::ios::binary); if (!ifs) return false; std::vector<uint8_t> buf((std::istreambuf_iterator<char>(ifs)), {}); return put(key, buf, ttl); }

std::optional<std::vector<uint8_t>> FileCache::get(const std::string& key) { std::lock_guard<std::mutex> lk(entries_mutex_); auto it = entries_.find(key); if (it==entries_.end()) { stats_.misses++; return std::nullopt; } if (it->second.is_expired() || !fs::exists(it->second.file_path)) { stats_.expirations++; entries_.erase(it); return std::nullopt; } std::ifstream ifs(it->second.file_path, std::ios::binary); std::vector<uint8_t> data((std::istreambuf_iterator<char>(ifs)), {}); stats_.hits++; return data; }
std::optional<std::string> FileCache::get_string(const std::string& key) { auto v = get(key); if (!v) return std::nullopt; return std::string(v->begin(), v->end()); }
std::optional<std::string> FileCache::get_file_path(const std::string& key) { std::lock_guard<std::mutex> lk(entries_mutex_); auto it = entries_.find(key); if (it==entries_.end()) return std::nullopt; return it->second.file_path; }
bool FileCache::copy_to_file(const std::string& key, const std::string& dst) { auto v = get(key); if (!v) return false; std::ofstream ofs(dst, std::ios::binary); ofs.write(reinterpret_cast<const char*>(v->data()), static_cast<std::streamsize>(v->size())); return true; }
bool FileCache::remove(const std::string& key) { std::lock_guard<std::mutex> lk(entries_mutex_); auto it = entries_.find(key); if (it==entries_.end()) return false; fs::remove(it->second.file_path); entries_.erase(it); stats_.deletes++; stats_.total_entries = entries_.size(); stats_.total_disk_usage = calculate_total_disk_usage(); return true; }
bool FileCache::contains(const std::string& key) const { std::lock_guard<std::mutex> lk(entries_mutex_); return entries_.count(key)>0; }
size_t FileCache::size() const { std::lock_guard<std::mutex> lk(entries_mutex_); return entries_.size(); }
bool FileCache::empty() const { return size() == 0; }
void FileCache::clear() { std::lock_guard<std::mutex> lk(entries_mutex_); for (auto& [k,e] : entries_) fs::remove(e.file_path); entries_.clear(); stats_.total_entries = 0; stats_.total_disk_usage = 0; }
size_t FileCache::cleanup_expired() { size_t removed=0; std::lock_guard<std::mutex> lk(entries_mutex_); for (auto it=entries_.begin(); it!=entries_.end();) { if (it->second.is_expired()) { fs::remove(it->second.file_path); it = entries_.erase(it); removed++; stats_.expirations++; } else ++it; } stats_.total_entries = entries_.size(); stats_.total_disk_usage = calculate_total_disk_usage(); return removed; }
size_t FileCache::enforce_size_limit() { size_t removed=0; while (get_disk_usage() > max_size_) { if (entries_.empty()) break; auto it = entries_.begin(); fs::remove(it->second.file_path); entries_.erase(it); removed++; } stats_.total_entries = entries_.size(); stats_.total_disk_usage = calculate_total_disk_usage(); return removed; }
FileCacheStats FileCache::get_stats() const { return stats_; }
void FileCache::reset_stats() { stats_ = FileCacheStats{}; }
size_t FileCache::get_disk_usage() const { return calculate_total_disk_usage(); }
void FileCache::set_max_size(size_t s) { max_size_ = s; }
void FileCache::set_default_ttl(std::chrono::seconds s) { default_ttl_ = s; }
std::string FileCache::get_cache_directory() const { return cache_dir_; }
std::vector<std::string> FileCache::get_all_keys() const { std::vector<std::string> keys; keys.reserve(entries_.size()); for (auto& [k,_]: entries_) keys.push_back(k); return keys; }
std::optional<FileCacheEntry> FileCache::get_entry_info(const std::string& key) const { auto it = entries_.find(key); if (it==entries_.end()) return std::nullopt; return it->second; }
size_t FileCache::verify_integrity() { size_t issues=0; for (auto& [k,e] : entries_) if (!fs::exists(e.file_path)) issues++; return issues; }
bool FileCache::load_index() { return true; }
void FileCache::set_auto_cleanup(bool enabled, std::chrono::seconds interval) { auto_cleanup_enabled_ = enabled; cleanup_interval_ = interval; if (enabled && !cleanup_thread_) cleanup_thread_ = std::make_unique<std::thread>(&FileCache::cleanup_loop, this); }

std::string FileCache::generate_file_path(const std::string& key) const { return cache_dir_ + "/" + sanitize_key(key); }
std::string FileCache::calculate_hash(const std::vector<uint8_t>&) const { return ""; }
std::string FileCache::sanitize_key(const std::string& key) const { std::string s=key; for (char& c: s) if (!std::isalnum((unsigned char)c)) c='_'; return s; }
bool FileCache::ensure_cache_directory() const { return fs::exists(cache_dir_) || fs::create_directories(cache_dir_); }
bool FileCache::write_data_to_file(const std::string& path, const std::vector<uint8_t>& data) { std::ofstream ofs(path, std::ios::binary); if (!ofs) return false; ofs.write(reinterpret_cast<const char*>(data.data()), static_cast<std::streamsize>(data.size())); return true; }
std::optional<std::vector<uint8_t>> FileCache::read_data_from_file(const std::string& path) { std::ifstream ifs(path, std::ios::binary); if (!ifs) return std::nullopt; std::vector<uint8_t> data((std::istreambuf_iterator<char>(ifs)), {}); return data; }
void FileCache::update_access_time(const std::string&) {}
void FileCache::cleanup_loop() { while (running_) { std::this_thread::sleep_for(cleanup_interval_); if (!auto_cleanup_enabled_) continue; cleanup_expired(); enforce_size_limit(); } }
size_t FileCache::calculate_total_disk_usage() const { size_t total=0; for (auto& [k,e]: entries_) if (fs::exists(e.file_path)) total += static_cast<size_t>(fs::file_size(e.file_path)); return total; }
std::vector<std::string> FileCache::get_oldest_keys(size_t) const { return {}; }
bool FileCache::remove_file_safe(const std::string& path) { return fs::remove(path); }
std::string FileCache::get_index_file_path() const { return cache_dir_ + "/index.json"; }

// PersistentStorage (minimal)
PersistentStorage::PersistentStorage(const std::string& dir) : storage_dir_(dir) { ensure_storage_directory(); }
PersistentStorage::~PersistentStorage() = default;
bool PersistentStorage::store(const std::string& key, const std::vector<uint8_t>& data, const std::unordered_map<std::string, std::string>&) { std::ofstream ofs(get_data_file_path(key), std::ios::binary); if (!ofs) return false; ofs.write(reinterpret_cast<const char*>(data.data()), static_cast<std::streamsize>(data.size())); return true; }
std::optional<std::vector<uint8_t>> PersistentStorage::load(const std::string& key) { std::ifstream ifs(get_data_file_path(key), std::ios::binary); if (!ifs) return std::nullopt; std::vector<uint8_t> data((std::istreambuf_iterator<char>(ifs)), {}); return data; }
std::optional<std::unordered_map<std::string, std::string>> PersistentStorage::get_metadata(const std::string&) { return std::nullopt; }
bool PersistentStorage::remove(const std::string& key) { return fs::remove(get_data_file_path(key)); }
bool PersistentStorage::exists(const std::string& key) { return fs::exists(get_data_file_path(key)); }
std::vector<std::string> PersistentStorage::list_keys() const { std::vector<std::string> keys; for (auto& e : fs::directory_iterator(storage_dir_)) keys.push_back(e.path().filename().string()); return keys; }
size_t PersistentStorage::get_storage_size() const { size_t total=0; for (auto& e: fs::directory_iterator(storage_dir_)) if (fs::is_regular_file(e)) total += static_cast<size_t>(fs::file_size(e)); return total; }
void PersistentStorage::set_compression_enabled(bool en) { compression_enabled_ = en; }
void PersistentStorage::set_encryption_enabled(bool en, const std::string& key) { encryption_enabled_ = en; encryption_key_ = key; }
std::string PersistentStorage::get_data_file_path(const std::string& key) const { return storage_dir_ + "/" + key; }
std::string PersistentStorage::get_metadata_file_path(const std::string& key) const { return storage_dir_ + "/" + key + ".meta"; }
bool PersistentStorage::ensure_storage_directory() const { return fs::exists(storage_dir_) || fs::create_directories(storage_dir_); }
std::vector<uint8_t> PersistentStorage::compress_data(const std::vector<uint8_t>& d) const { return d; }
std::vector<uint8_t> PersistentStorage::decompress_data(const std::vector<uint8_t>& d) const { return d; }
std::vector<uint8_t> PersistentStorage::encrypt_data(const std::vector<uint8_t>& d) const { return d; }
std::vector<uint8_t> PersistentStorage::decrypt_data(const std::vector<uint8_t>& d) const { return d; }

namespace cache_utils {
std::string normalize_key(const std::string& key) { std::string s=key; for (char& c: s) if (!std::isalnum((unsigned char)c)) c='_'; return s; }
size_t get_directory_size(const std::string& dir) { size_t total=0; for (auto& e: fs::recursive_directory_iterator(dir)) if (fs::is_regular_file(e)) total += static_cast<size_t>(fs::file_size(e)); return total; }
bool remove_directory_recursive(const std::string& dir) { return fs::remove_all(dir) > 0; }
std::string create_temp_file(const std::string& prefix) { auto p = fs::temp_directory_path() / (prefix + "XXXX"); return p.string(); }
}

} // namespace wiplib::utils

