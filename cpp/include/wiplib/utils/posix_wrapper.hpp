#pragma once

#include <cstdlib>
#include <string>

#ifdef _WIN32
#include <fcntl.h>
#include <io.h>
#include <winsock2.h>
#else
#include <fcntl.h>
#include <sys/socket.h>
#include <unistd.h>
#endif

namespace wiplib::utils {

class PosixWrapper {
public:
  static int openFile(const char *path, int flags, int mode = 0644);
  static int closeFile(int fd);
  static ssize_t readFile(int fd, void *buf, size_t count);
  static ssize_t writeFile(int fd, const void *buf, size_t count);
  static int createSocket(int domain, int type, int protocol);
  static int closeSocket(int sock);
  static bool setEnv(const std::string &key, const std::string &value,
                     bool overwrite);
};

#ifdef _WIN32
inline int PosixWrapper::openFile(const char *path, int flags, int mode) {
  return _open(path, flags, mode);
}
inline int PosixWrapper::closeFile(int fd) { return _close(fd); }
inline ssize_t PosixWrapper::readFile(int fd, void *buf, size_t count) {
  return _read(fd, buf, static_cast<unsigned int>(count));
}
inline ssize_t PosixWrapper::writeFile(int fd, const void *buf, size_t count) {
  return _write(fd, buf, static_cast<unsigned int>(count));
}
inline int PosixWrapper::createSocket(int domain, int type, int protocol) {
  return static_cast<int>(::socket(domain, type, protocol));
}
inline int PosixWrapper::closeSocket(int sock) { return ::closesocket(sock); }
inline bool PosixWrapper::setEnv(const std::string &key,
                                 const std::string &value, bool overwrite) {
  if (!overwrite) {
    const char *existing = std::getenv(key.c_str());
    if (existing)
      return true;
  }
  return _putenv_s(key.c_str(), value.c_str()) == 0;
}
#else
inline int PosixWrapper::openFile(const char *path, int flags, int mode) {
  return ::open(path, flags, mode);
}
inline int PosixWrapper::closeFile(int fd) { return ::close(fd); }
inline ssize_t PosixWrapper::readFile(int fd, void *buf, size_t count) {
  return ::read(fd, buf, count);
}
inline ssize_t PosixWrapper::writeFile(int fd, const void *buf, size_t count) {
  return ::write(fd, buf, count);
}
inline int PosixWrapper::createSocket(int domain, int type, int protocol) {
  return ::socket(domain, type, protocol);
}
inline int PosixWrapper::closeSocket(int sock) { return ::close(sock); }
inline bool PosixWrapper::setEnv(const std::string &key,
                                 const std::string &value, bool overwrite) {
  return ::setenv(key.c_str(), value.c_str(), overwrite ? 1 : 0) == 0;
}
#endif

} // namespace wiplib::utils
