#include "FileCache.hpp"
#include <fstream>
#include <filesystem>
#include <ctime>

PersistentCache::PersistentCache(const std::string &cache_file, int ttl_hours)
    : cache_file_(cache_file), ttl_seconds_(static_cast<long>(ttl_hours) * 3600) {
    load_cache();
}

void PersistentCache::load_cache() {
    std::ifstream f(cache_file_);
    if (!f.is_open()) return;
    try {
        f >> cache_;
        long now = std::time(nullptr);
        for (auto it = cache_.begin(); it != cache_.end(); ) {
            if (!it->contains("timestamp") || !it->contains("area_code") ||
                now - (*it)["timestamp"].get<long>() >= ttl_seconds_) {
                it = cache_.erase(it);
            } else {
                ++it;
            }
        }
    } catch (...) {
        cache_.clear();
    }
}

void PersistentCache::save_cache() {
    std::ofstream f(cache_file_);
    if (!f.is_open()) return;
    f << cache_.dump(2);
}

std::optional<std::string> PersistentCache::get(const std::string &key) {
    auto it = cache_.find(key);
    if (it == cache_.end()) return std::nullopt;
    long now = std::time(nullptr);
    if (now - (*it)["timestamp"].get<long>() >= ttl_seconds_) {
        cache_.erase(it);
        save_cache();
        return std::nullopt;
    }
    return (*it)["area_code"].get<std::string>();
}

void PersistentCache::set(const std::string &key, const std::string &area_code) {
    cache_[key] = { {"area_code", area_code}, {"timestamp", std::time(nullptr)} };
    save_cache();
}

void PersistentCache::clear() {
    cache_.clear();
    std::filesystem::remove(cache_file_);
}

std::size_t PersistentCache::size() const {
    return cache_.size();
}

