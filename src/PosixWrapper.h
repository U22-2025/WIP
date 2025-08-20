#ifndef POSIXWRAPPER_H
#define POSIXWRAPPER_H

#ifdef _WIN32
#include <winsock2.h>
#include <ws2tcpip.h>
#include <windows.h>
#include <io.h>
#include <fcntl.h>
using socket_t = SOCKET;
#else
#include <sys/types.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <unistd.h>
#include <fcntl.h>
using socket_t = int;
#endif

namespace PosixWrapper {
    socket_t create_socket();
    int close_socket(socket_t sock);
    int open_file(const char* path, int flags);
    int close_file(int fd);
}

#endif // POSIXWRAPPER_H
