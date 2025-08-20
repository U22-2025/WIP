#pragma once

/**
 * @brief Windows/POSIX互換性ヘッダー
 * 
 * プラットフォーム間の差異を吸収し、統一的なAPIを提供
 */

#ifdef _WIN32
    #include <winsock2.h>
    #include <ws2tcpip.h>
    #include <io.h>
    #include <process.h>
    #include <intrin.h>
    
    // 型定義
    using ssize_t = long long;
    using socklen_t = int;
    using suseconds_t = long;
    
    // マクロ定義
    #ifndef SHUT_RD
        #define SHUT_RD SD_RECEIVE
    #endif
    #ifndef SHUT_WR
        #define SHUT_WR SD_SEND
    #endif
    #ifndef SHUT_RDWR
        #define SHUT_RDWR SD_BOTH
    #endif
    
    // エラーコード互換
    #ifndef EAGAIN
        #define EAGAIN WSAEWOULDBLOCK
    #endif
    #ifndef EWOULDBLOCK
        #define EWOULDBLOCK WSAEWOULDBLOCK
    #endif
    #ifndef EINPROGRESS
        #define EINPROGRESS WSAEINPROGRESS
    #endif
    
    // 関数マクロ（ソケット専用）
    #define platform_close_socket(s) ::closesocket(s)
    #define platform_socket_error() WSAGetLastError()
    #define platform_popcount(x) __popcnt(x)
    
    // timeval構造体はwinsock2.hで定義済み
    
#else  // POSIX (Linux, macOS, etc.)
    #include <sys/socket.h>
    #include <netinet/in.h>
    #include <arpa/inet.h>
    #include <netdb.h>
    #include <unistd.h>
    #include <errno.h>
    #include <sys/time.h>
    
    // 関数マクロ
    #define platform_close_socket(s) ::close(s)
    #define platform_socket_error() errno
    #define platform_popcount(x) __builtin_popcount(x)
    
#endif

namespace wiplib::utils {

/**
 * @brief プラットフォーム固有の初期化
 */
inline bool initialize_platform() {
#ifdef _WIN32
    WSADATA wsaData;
    return WSAStartup(MAKEWORD(2, 2), &wsaData) == 0;
#else
    return true;  // POSIX では何もしない
#endif
}

/**
 * @brief プラットフォーム固有のクリーンアップ
 */
inline void cleanup_platform() {
#ifdef _WIN32
    WSACleanup();
#endif
}

/**
 * @brief ソケット操作のラッパー関数
 */
inline int platform_setsockopt(int sockfd, int level, int optname, const void* optval, socklen_t optlen) {
#ifdef _WIN32
    return ::setsockopt(sockfd, level, optname, reinterpret_cast<const char*>(optval), optlen);
#else
    return ::setsockopt(sockfd, level, optname, optval, optlen);
#endif
}

inline int platform_getsockopt(int sockfd, int level, int optname, void* optval, socklen_t* optlen) {
#ifdef _WIN32
    return ::getsockopt(sockfd, level, optname, reinterpret_cast<char*>(optval), reinterpret_cast<int*>(optlen));
#else
    return ::getsockopt(sockfd, level, optname, optval, optlen);
#endif
}

inline ssize_t platform_send(int sockfd, const void* buf, size_t len, int flags) {
#ifdef _WIN32
    return ::send(sockfd, reinterpret_cast<const char*>(buf), static_cast<int>(len), flags);
#else
    return ::send(sockfd, buf, len, flags);
#endif
}

inline ssize_t platform_recv(int sockfd, void* buf, size_t len, int flags) {
#ifdef _WIN32
    return ::recv(sockfd, reinterpret_cast<char*>(buf), static_cast<int>(len), flags);
#else
    return ::recv(sockfd, buf, len, flags);
#endif
}

inline ssize_t platform_sendto(int sockfd, const void* buf, size_t len, int flags, 
                              const struct sockaddr* dest_addr, socklen_t addrlen) {
#ifdef _WIN32
    return ::sendto(sockfd, reinterpret_cast<const char*>(buf), static_cast<int>(len), flags, dest_addr, addrlen);
#else
    return ::sendto(sockfd, buf, len, flags, dest_addr, addrlen);
#endif
}

inline ssize_t platform_recvfrom(int sockfd, void* buf, size_t len, int flags,
                                 struct sockaddr* src_addr, socklen_t* addrlen) {
#ifdef _WIN32
    return ::recvfrom(sockfd, reinterpret_cast<char*>(buf), static_cast<int>(len), flags, src_addr, addrlen);
#else
    return ::recvfrom(sockfd, buf, len, flags, src_addr, addrlen);
#endif
}

}  // namespace wiplib::utils