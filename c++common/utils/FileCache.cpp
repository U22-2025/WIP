#include "FileCache.hpp"
#include <fstream>
#include <ctime>

namespace wip {
namespace utils {

FileCache::FileCache(const std::string& path, std::chrono::hours ttl)
    : path_(path), ttl_(std::chrono::duration_cast<std::chrono::seconds>(ttl)) {
    load();
}

void FileCache::load() {
    std::lock_guard<std::mutex> lock(mtx_);
    cache_.clear();
    std::ifstream in(path_);
    if (!in) return;
    std::string key, value;
    std::time_t ts;
    while (in >> key >> value >> ts) {
        if (std::time(nullptr) - ts < ttl_.count()) {
            cache_[key] = {value, ts};
        }
    }
}

void FileCache::save() {
    std::lock_guard<std::mutex> lock(mtx_);
    std::ofstream out(path_, std::ios::trunc);
    if (!out) return;
    for (const auto& kv : cache_) {
        out << kv.first << ' ' << kv.second.first << ' ' << kv.second.second << '\n';
    }
}

bool FileCache::get(const std::string& key, std::string& value) {
    std::lock_guard<std::mutex> lock(mtx_);
    auto it = cache_.find(key);
    if (it == cache_.end()) return false;
    if (std::time(nullptr) - it->second.second >= ttl_.count()) {
        cache_.erase(it);
        save();
        return false;
    }
    value = it->second.first;
    return true;
}

void FileCache::set(const std::string& key, const std::string& value) {
    std::lock_guard<std::mutex> lock(mtx_);
    cache_[key] = {value, std::time(nullptr)};
    save();
}

void FileCache::clear() {
    std::lock_guard<std::mutex> lock(mtx_);
    cache_.clear();
    std::remove(path_.c_str());
}

std::size_t FileCache::size() const {
    std::lock_guard<std::mutex> lock(mtx_);
    return cache_.size();
}

} // namespace utils
} // namespace wip
