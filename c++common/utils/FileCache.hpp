#pragma once
#include <string>
#include <unordered_map>
#include <chrono>
#include <optional>
#include "third_party/json.hpp"

class PersistentCache {
public:
    explicit PersistentCache(const std::string &cache_file = "WIP_Client/coordinate_cache.json", int ttl_hours = 24);

    std::optional<std::string> get(const std::string &key);
    void set(const std::string &key, const std::string &area_code);
    void clear();
    std::size_t size() const;

private:
    void load_cache();
    void save_cache();

    std::string cache_file_;
    long ttl_seconds_;
    nlohmann::json cache_;
};
