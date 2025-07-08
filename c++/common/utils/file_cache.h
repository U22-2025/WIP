#ifndef COMMON_UTILS_FILE_CACHE_H
#define COMMON_UTILS_FILE_CACHE_H

#include <string>
#include <unordered_map>
#include <optional>
#include <chrono>

namespace common {
namespace utils {

class PersistentCache {
public:
    explicit PersistentCache(const std::string &path, std::chrono::hours ttl = std::chrono::hours(24));

    std::optional<std::string> get(const std::string &key);
    void set(const std::string &key, const std::string &value);
    void clear();
    size_t size() const { return cache_.size(); }

private:
    std::string path_;
    std::chrono::seconds ttl_;
    std::unordered_map<std::string, std::pair<std::string, std::chrono::system_clock::time_point>> cache_;
    void load();
    void save();
};

} // namespace utils
} // namespace common

#endif
