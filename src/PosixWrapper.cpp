#include "PosixWrapper.h"

namespace PosixWrapper {

socket_t create_socket() {
#ifdef _WIN32
    WSADATA wsa;
    WSAStartup(MAKEWORD(2,2), &wsa);
    return socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
#else
    return socket(AF_INET, SOCK_STREAM, 0);
#endif
}

int close_socket(socket_t sock) {
#ifdef _WIN32
    return closesocket(sock);
#else
    return close(sock);
#endif
}

int open_file(const char* path, int flags) {
#ifdef _WIN32
    return _open(path, flags);
#else
    return open(path, flags);
#endif
}

int close_file(int fd) {
#ifdef _WIN32
    return _close(fd);
#else
    return close(fd);
#endif
}

} // namespace PosixWrapper
