#pragma once

#ifdef _WIN32
#include <winsock2.h>
#include <ws2tcpip.h>
#include <BaseTsd.h>
#pragma comment(lib, "ws2_32.lib")
#ifndef ssize_t
using ssize_t = SSIZE_T;
#endif

namespace wip {
namespace platform {
using socket_t = SOCKET;
inline int close_socket(SOCKET s) { return closesocket(s); }
constexpr SOCKET invalid_socket = INVALID_SOCKET;
struct SocketInitializer {
    SocketInitializer() {
        WSADATA wsa{};
        WSAStartup(MAKEWORD(2,2), &wsa);
    }
    ~SocketInitializer() { WSACleanup(); }
};
} // namespace platform
} // namespace wip

#else // POSIX

#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <unistd.h>

namespace wip {
namespace platform {
using socket_t = int;
inline int close_socket(int s) { return ::close(s); }
constexpr int invalid_socket = -1;
struct SocketInitializer {};
} // namespace platform
} // namespace wip

#endif
