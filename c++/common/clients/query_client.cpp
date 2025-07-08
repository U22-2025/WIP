#include "query_client.h"
#include <sys/socket.h>
#include <arpa/inet.h>
#include <unistd.h>

namespace common {
namespace clients {

QueryClient::QueryClient(const std::string &host, int port) : host_(host), port_(port) {}

packet::models::Response QueryClient::send(const packet::models::Request &req) {
    int sock = socket(AF_INET, SOCK_DGRAM, 0);
    sockaddr_in addr{};
    addr.sin_family = AF_INET;
    addr.sin_port = htons(port_);
    inet_pton(AF_INET, host_.c_str(), &addr.sin_addr);
    auto bytes = req.toBytes();
    sendto(sock, bytes.data(), bytes.size(), 0, (sockaddr*)&addr, sizeof(addr));
    char buf[1024];
    ssize_t len = recvfrom(sock, buf, sizeof(buf), 0, nullptr, nullptr);
    close(sock);
    packet::models::Response res;
    if(len>0) {
        res.fromBytes(std::vector<uint8_t>(buf, buf+len));
    }
    return res;
}

} // namespace clients
} // namespace common
