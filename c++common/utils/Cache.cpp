#include "Cache.hpp"

Cache::Cache(std::chrono::seconds default_ttl)
    : default_ttl_(default_ttl) {}

void Cache::set(const std::string &key, const std::any &value, std::chrono::seconds ttl) {
    std::lock_guard<std::mutex> lock(mutex_);
    auto expire = std::chrono::system_clock::now() + (ttl.count() == 0 ? default_ttl_ : ttl);
    cache_[key] = {value, expire};
}

std::optional<std::any> Cache::get(const std::string &key) {
    std::lock_guard<std::mutex> lock(mutex_);
    auto it = cache_.find(key);
    if (it == cache_.end()) return std::nullopt;
    if (std::chrono::system_clock::now() > it->second.expire) {
        cache_.erase(it);
        return std::nullopt;
    }
    return it->second.value;
}

void Cache::remove(const std::string &key) {
    std::lock_guard<std::mutex> lock(mutex_);
    cache_.erase(key);
}

void Cache::clear() {
    std::lock_guard<std::mutex> lock(mutex_);
    cache_.clear();
}

std::size_t Cache::size() const {
    std::lock_guard<std::mutex> lock(mutex_);
    return cache_.size();
}

