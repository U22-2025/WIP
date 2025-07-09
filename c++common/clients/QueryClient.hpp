#ifndef WIP_CLIENTS_QUERYCLIENT_HPP
#define WIP_CLIENTS_QUERYCLIENT_HPP

#include <string>
#include <unordered_map>
#include "utils/PacketIDGenerator.hpp"
#include "../../utils/Cache.hpp"

namespace wip {
namespace clients {

class QueryClient {
public:
    QueryClient(const std::string& host = "", int port = 0, bool debug = false,
                int cache_ttl_minutes = 10);
    void close();

    std::unordered_map<std::string, std::string> get_weather_data(
        const std::string& area_code,
        bool weather = false,
        bool temperature = false,
        bool precipitation_prob = false,
        bool alert = false,
        bool disaster = false,
        const std::pair<std::string, int>* source = nullptr,
        double timeout = 5.0,
        bool use_cache = true,
        int day = 0,
        bool force_refresh = false);

    std::unordered_map<std::string, std::string> get_weather_simple(
        const std::string& area_code, bool include_all = false,
        double timeout = 5.0, bool use_cache = true);

    std::unordered_map<std::string, std::string> get_cache_stats() const;
    void clear_cache();

private:
    void init_auth();
    std::string host_;
    int port_;
    bool debug_;
    PacketIDGenerator12Bit pidg_;
    wip::utils::Cache cache_;
    bool auth_enabled_ = false;
    std::string auth_passphrase_;
};

} // namespace clients
} // namespace wip

#endif // WIP_CLIENTS_QUERYCLIENT_HPP
