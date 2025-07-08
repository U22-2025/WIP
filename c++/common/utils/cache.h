#ifndef COMMON_UTILS_CACHE_H
#define COMMON_UTILS_CACHE_H

#include <unordered_map>
#include <chrono>
#include <mutex>
#include <optional>

namespace common {
namespace utils {

template <typename Key, typename Value>
class Cache {
public:
    explicit Cache(std::chrono::seconds ttl = std::chrono::minutes(30)) : ttl_(ttl) {}

    void set(const Key &key, const Value &value) {
        std::lock_guard<std::mutex> lock(mutex_);
        auto expire = std::chrono::steady_clock::now() + ttl_;
        store_[key] = {value, expire};
    }

    std::optional<Value> get(const Key &key) {
        std::lock_guard<std::mutex> lock(mutex_);
        auto it = store_.find(key);
        if (it == store_.end()) return std::nullopt;
        if (std::chrono::steady_clock::now() > it->second.expire) {
            store_.erase(it);
            return std::nullopt;
        }
        return it->second.value;
    }

    void clear() {
        std::lock_guard<std::mutex> lock(mutex_);
        store_.clear();
    }

    size_t size() const {
        std::lock_guard<std::mutex> lock(mutex_);
        return store_.size();
    }

private:
    struct Entry { Value value; std::chrono::steady_clock::time_point expire; };
    std::unordered_map<Key, Entry> store_;
    std::chrono::seconds ttl_;
    mutable std::mutex mutex_;
};

} // namespace utils
} // namespace common

#endif // COMMON_UTILS_CACHE_H
