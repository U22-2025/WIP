#ifndef WIP_CLIENTS_REPORTCLIENT_HPP
#define WIP_CLIENTS_REPORTCLIENT_HPP

#include <string>
#include <unordered_map>
#include <vector>
#include "utils/PacketIDGenerator.hpp"

namespace wip {
namespace clients {

class ReportClient {
public:
    ReportClient(const std::string& host = "localhost", int port = 4110, bool debug = false);
    ~ReportClient();

    void set_sensor_data(const std::string& area_code,
                         int weather_code = -1,
                         double temperature = 0.0,
                         int precipitation_prob = -1,
                         const std::vector<std::string>& alert = {},
                         const std::vector<std::string>& disaster = {});

    std::unordered_map<std::string, std::string> send_report_data();
    std::unordered_map<std::string, std::string> send_data_simple();
    std::unordered_map<std::string, std::string> get_current_data() const;
    void clear_data();

private:
    void init_auth();
    std::string host_;
    int port_;
    bool debug_;
    int sock_ = -1;
    utils::PacketIDGenerator12Bit pidg_;
    bool auth_enabled_ = false;
    std::string auth_passphrase_;

    std::string area_code_;
    int weather_code_ = -1;
    double temperature_ = 0.0;
    int precipitation_prob_ = -1;
    std::vector<std::string> alert_;
    std::vector<std::string> disaster_;
};

} // namespace clients
} // namespace wip

#endif // WIP_CLIENTS_REPORTCLIENT_HPP
