#pragma once
#include <unordered_map>
#include <string>
#include <chrono>
#include <any>
#include <mutex>
#include <optional>

class Cache {
public:
    explicit Cache(std::chrono::seconds default_ttl = std::chrono::minutes(30));

    void set(const std::string &key, const std::any &value, std::chrono::seconds ttl = std::chrono::seconds(0));
    std::optional<std::any> get(const std::string &key);
    void remove(const std::string &key);
    void clear();
    std::size_t size() const;

private:
    struct Entry {
        std::any value;
        std::chrono::system_clock::time_point expire;
    };

    std::unordered_map<std::string, Entry> cache_;
    mutable std::mutex mutex_;
    std::chrono::seconds default_ttl_;
};
