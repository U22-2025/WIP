#pragma once

#include <string>
#include "../platform.hpp"

#ifdef _WIN32
#include <winsock2.h>
#include <ws2tcpip.h>
#else
#include <netdb.h>
#include <arpa/inet.h>
#endif

namespace wip {
namespace utils {

inline in_addr resolve_hostname(const std::string& host) {
    in_addr addr{};
#ifdef _WIN32
    if (InetPtonA(AF_INET, host.c_str(), &addr) == 1) {
        return addr;
    }
    hostent* he = gethostbyname(host.c_str());
    if (he && he->h_addr_list && he->h_addr_list[0]) {
        addr = *reinterpret_cast<in_addr*>(he->h_addr_list[0]);
    } else {
        addr.s_addr = INADDR_NONE;
    }
#else
    if (inet_pton(AF_INET, host.c_str(), &addr) == 1) {
        return addr;
    }
    hostent* he = gethostbyname(host.c_str());
    if (he && he->h_addr_list && he->h_addr_list[0]) {
        addr = *reinterpret_cast<in_addr*>(he->h_addr_list[0]);
    } else {
        addr.s_addr = INADDR_NONE;
    }
#endif
    return addr;
}

} // namespace utils
} // namespace wip

