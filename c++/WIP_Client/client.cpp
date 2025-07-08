#include "client.h"

namespace WIP_Client {

Client::Client(const std::string &host, int port)
    : query_(host, port), location_(host, port) {}

common::packet::models::Response Client::getWeather(double lat, double lon) {
    common::packet::models::Request req;
    req.version = 1;
    req.packet_id = 1;
    req.type = 0;
    // placeholder; no coordinates
    return query_.send(req);
}

} // namespace WIP_Client
