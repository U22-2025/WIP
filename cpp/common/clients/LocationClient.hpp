#ifndef WIP_CLIENTS_LOCATIONCLIENT_HPP
#define WIP_CLIENTS_LOCATIONCLIENT_HPP

#include <string>
#include <unordered_map>
#include "utils/PacketIDGenerator.hpp"
#include "../packet/types/ReportPacket.hpp"
#include "../utils/FileCache.hpp"

namespace wip {
namespace clients {

class LocationClient {
public:
    LocationClient(const std::string& host = "", int port = 0, bool debug = false,
                   int cache_ttl_minutes = 30);
    ~LocationClient();

    std::pair<std::string, double> get_location_data(
        double latitude, double longitude, bool use_cache = true,
        bool weather = true, bool temperature = true,
        bool precipitation_prob = true, bool alert = false,
        bool disaster = false, int day = 0, bool force_refresh = false);

    std::string get_area_code_simple(double latitude, double longitude,
                                    bool use_cache = true);
    void clear_cache();
    std::unordered_map<std::string, std::string> get_cache_stats() const;

private:
    void init_auth();
    std::string host_;
    int port_;
    bool debug_;
    packet::PacketIDGenerator12Bit pidg_;
    wip::utils::FileCache cache_;
    bool auth_enabled_ = false;
    std::string auth_passphrase_;
    int sock_ = -1;
};

} // namespace clients
} // namespace wip

#endif // WIP_CLIENTS_LOCATIONCLIENT_HPP
