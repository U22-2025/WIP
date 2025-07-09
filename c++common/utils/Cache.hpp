#ifndef WIP_UTILS_CACHE_HPP
#define WIP_UTILS_CACHE_HPP

#include <string>
#include <unordered_map>
#include <chrono>
#include <mutex>

namespace wip {
namespace utils {

class Cache {
public:
    explicit Cache(std::chrono::seconds ttl = std::chrono::minutes(30));

    void set(const std::string& key, const std::string& value,
             std::chrono::seconds ttl = std::chrono::seconds(0));
    bool get(const std::string& key, std::string& value);
    void clear();
    std::size_t size() const;

private:
    struct Entry {
        std::string value;
        std::chrono::steady_clock::time_point expire;
    };

    std::unordered_map<std::string, Entry> cache_;
    std::chrono::seconds default_ttl_;
    mutable std::mutex mtx_;
};

} // namespace utils
} // namespace wip

#endif // WIP_UTILS_CACHE_HPP
