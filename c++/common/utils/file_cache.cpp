#include "file_cache.h"
#include <fstream>
#include <sstream>

namespace common {
namespace utils {

PersistentCache::PersistentCache(const std::string &path, std::chrono::hours ttl)
    : path_(path), ttl_(std::chrono::duration_cast<std::chrono::seconds>(ttl)) {
    load();
}

void PersistentCache::load() {
    std::ifstream f(path_);
    if (!f.good()) return;
    std::string line;
    auto now = std::chrono::system_clock::now();
    while (std::getline(f, line)) {
        std::istringstream iss(line);
        std::string key, ts_str, value;
        if (std::getline(iss, key, ',') && std::getline(iss, ts_str, ',') && std::getline(iss, value)) {
            long ts_val = std::stol(ts_str);
            auto ts = std::chrono::system_clock::time_point(std::chrono::seconds(ts_val));
            if (now - ts < ttl_) {
                cache_[key] = {value, ts};
            }
        }
    }
}

void PersistentCache::save() {
    std::ofstream f(path_);
    for (auto &kv : cache_) {
        long ts = std::chrono::duration_cast<std::chrono::seconds>(kv.second.second.time_since_epoch()).count();
        f << kv.first << "," << ts << "," << kv.second.first << "\n";
    }
}

std::optional<std::string> PersistentCache::get(const std::string &key) {
    auto it = cache_.find(key);
    if (it == cache_.end()) return std::nullopt;
    if (std::chrono::system_clock::now() - it->second.second > ttl_) {
        cache_.erase(it);
        save();
        return std::nullopt;
    }
    return it->second.first;
}

void PersistentCache::set(const std::string &key, const std::string &value) {
    cache_[key] = {value, std::chrono::system_clock::now()};
    save();
}

void PersistentCache::clear() {
    cache_.clear();
    std::remove(path_.c_str());
}

} // namespace utils
} // namespace common
