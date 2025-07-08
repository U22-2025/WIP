#include "file_cache.h"
#include <fstream>
#include <nlohmann/json.hpp>

namespace common {
namespace utils {

using json = nlohmann::json;

PersistentCache::PersistentCache(const std::string &path, std::chrono::hours ttl)
    : path_(path), ttl_(std::chrono::duration_cast<std::chrono::seconds>(ttl)) {
    load();
}

void PersistentCache::load() {
    std::ifstream f(path_);
    if (!f.good()) return;
    json j; f >> j;
    auto now = std::chrono::system_clock::now();
    for (auto &el : j.items()) {
        auto ts = std::chrono::system_clock::time_point(std::chrono::seconds(el.value()["timestamp"].get<long>()));
        if (now - ts < ttl_) {
            cache_[el.key()] = {el.value()["area_code"].get<std::string>(), ts};
        }
    }
}

void PersistentCache::save() {
    json j;
    for (auto &kv : cache_) {
        j[kv.first] = { {"area_code", kv.second.first}, {"timestamp", std::chrono::duration_cast<std::chrono::seconds>(kv.second.second.time_since_epoch()).count()} };
    }
    std::ofstream f(path_);
    f << j.dump(2);
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
