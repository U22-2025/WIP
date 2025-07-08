#ifndef WIP_CLIENT_CLIENT_H
#define WIP_CLIENT_CLIENT_H

#include <string>
#include "../common/clients/query_client.h"
#include "../common/clients/location_client.h"

namespace WIP_Client {

class Client {
public:
    Client(const std::string &host="localhost", int port=4110);

    common::packet::models::Response getWeather(double lat, double lon);

private:
    common::clients::QueryClient query_;
    common::clients::LocationClient location_;
};

} // namespace WIP_Client

#endif
