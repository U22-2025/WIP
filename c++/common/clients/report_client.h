#ifndef COMMON_CLIENTS_REPORT_CLIENT_H
#define COMMON_CLIENTS_REPORT_CLIENT_H

#include <string>
#include "../packet/models/request.h"
#include "../packet/models/response.h"

namespace common {
namespace clients {

class ReportClient {
public:
    ReportClient(const std::string &host="localhost", int port=4110);
    models::Response send(const models::Request &req);
private:
    std::string host_;
    int port_;
};

} // namespace clients
} // namespace common

#endif
