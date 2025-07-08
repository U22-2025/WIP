#ifndef WIP_CLIENT_CLIENT_H
#define WIP_CLIENT_CLIENT_H

#include <string>
#include <map>
#include <optional>
#include "../common/clients/query_client.h"
#include "../common/clients/location_client.h"
#include "../common/clients/utils/packet_id_generator.h"

namespace WIP_Client {

class Client {
public:
    Client(const std::string &host="localhost", int port=4110, bool proxy=false);

    void setCoordinates(double lat, double lon);
    void setAreaCode(int code);

    std::map<std::string,std::string> getWeather();

private:
    std::string host_;
    int port_;
    bool proxy_;
    std::optional<double> lat_;
    std::optional<double> lon_;
    std::optional<int> area_;

    common::clients::QueryClient query_;
    common::clients::LocationClient location_;
    common::clients::utils::PacketIDGenerator12Bit pidg_;
};

} // namespace WIP_Client

#endif
