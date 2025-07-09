#include "Cache.hpp"

namespace wip {
namespace utils {

Cache::Cache(std::chrono::seconds ttl) : default_ttl_(ttl) {}

void Cache::set(const std::string& key, const std::string& value,
                std::chrono::seconds ttl) {
    std::lock_guard<std::mutex> lock(mtx_);
    auto actual = ttl.count() > 0 ? ttl : default_ttl_;
    cache_[key] = {value, std::chrono::steady_clock::now() + actual};
}

bool Cache::get(const std::string& key, std::string& value) {
    std::lock_guard<std::mutex> lock(mtx_);
    auto it = cache_.find(key);
    if (it == cache_.end()) return false;
    if (std::chrono::steady_clock::now() > it->second.expire) {
        cache_.erase(it);
        return false;
    }
    value = it->second.value;
    return true;
}

void Cache::clear() {
    std::lock_guard<std::mutex> lock(mtx_);
    cache_.clear();
}

std::size_t Cache::size() const {
    std::lock_guard<std::mutex> lock(mtx_);
    return cache_.size();
}

} // namespace utils
} // namespace wip
