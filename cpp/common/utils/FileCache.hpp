#ifndef WIP_UTILS_FILECACHE_HPP
#define WIP_UTILS_FILECACHE_HPP

#include <string>
#include <unordered_map>
#include <chrono>
#include <mutex>

namespace wip {
namespace utils {

class FileCache {
public:
    explicit FileCache(
        const std::string& path,
        std::chrono::minutes ttl =
            std::chrono::duration_cast<std::chrono::minutes>(
                std::chrono::hours(24)));

    bool get(const std::string& key, std::string& value);
    void set(const std::string& key, const std::string& value);
    void clear();
    std::size_t size() const;

private:
    void load();
    void save();
    std::string path_;
    std::chrono::seconds ttl_;
    std::unordered_map<std::string, std::pair<std::string, std::time_t>> cache_;
    mutable std::mutex mtx_;
};

} // namespace utils
} // namespace wip

#endif // WIP_UTILS_FILECACHE_HPP
