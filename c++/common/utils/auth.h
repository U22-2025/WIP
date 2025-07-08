#ifndef COMMON_UTILS_AUTH_H
#define COMMON_UTILS_AUTH_H

#include <string>
#include <chrono>

namespace common {
namespace utils {

class WIPAuth {
public:
    explicit WIPAuth(const std::string &secret_key);

    std::string generatePacketSignature(const std::string &data) const;
    bool verifyPacketSignature(const std::string &data, const std::string &sig) const;

    std::pair<std::string, std::chrono::system_clock::time_point>
    generateApiToken(const std::string &client_id) const;
    bool verifyApiToken(const std::string &token, const std::string &client_id) const;

    static std::string calculateAuthHash(int packet_id, int timestamp,
                                         const std::string &passphrase);
    static bool verifyAuthHash(int packet_id, int timestamp,
                               const std::string &passphrase,
                               const std::string &received_hash);

private:
    std::string secret_key_;
};

} // namespace utils
} // namespace common

#endif // COMMON_UTILS_AUTH_H
