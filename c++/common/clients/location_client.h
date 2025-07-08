#ifndef COMMON_CLIENTS_LOCATION_CLIENT_H
#define COMMON_CLIENTS_LOCATION_CLIENT_H

#include <string>
#include "../packet/models/request.h"
#include "../packet/models/response.h"

namespace common {
namespace clients {

class LocationClient {
public:
    LocationClient(const std::string &host="localhost", int port=4111);
    models::Response send(const models::Request &req);
private:
    std::string host_;
    int port_;
};

} // namespace clients
} // namespace common

#endif
