#include "auth.h"
#include <openssl/hmac.h>
#include <sstream>
#include <iomanip>

namespace common {
namespace utils {

static std::string to_hex(const unsigned char *data, size_t len) {
    std::ostringstream oss;
    for (size_t i = 0; i < len; ++i) {
        oss << std::hex << std::setw(2) << std::setfill('0') << (int)data[i];
    }
    return oss.str();
}

WIPAuth::WIPAuth(const std::string &secret_key) : secret_key_(secret_key) {}

std::string WIPAuth::generatePacketSignature(const std::string &data) const {
    unsigned char md[EVP_MAX_MD_SIZE];
    unsigned int md_len = 0;
    HMAC(EVP_sha256(), secret_key_.data(), (int)secret_key_.size(),
         reinterpret_cast<const unsigned char *>(data.data()), data.size(), md, &md_len);
    return to_hex(md, md_len);
}

bool WIPAuth::verifyPacketSignature(const std::string &data, const std::string &sig) const {
    return generatePacketSignature(data) == sig;
}

std::pair<std::string, std::chrono::system_clock::time_point>
WIPAuth::generateApiToken(const std::string &client_id) const {
    auto expiry = std::chrono::system_clock::now() + std::chrono::hours(1);
    std::string payload = client_id + ":" + std::to_string(std::chrono::duration_cast<std::chrono::seconds>(expiry.time_since_epoch()).count());
    std::string token = generatePacketSignature(payload);
    return {token + ":" + std::to_string(std::chrono::duration_cast<std::chrono::seconds>(expiry.time_since_epoch()).count()), expiry};
}

bool WIPAuth::verifyApiToken(const std::string &token, const std::string &client_id) const {
    auto pos = token.rfind(':');
    if (pos == std::string::npos) return false;
    std::string token_part = token.substr(0, pos);
    long expiry_ts = std::stol(token.substr(pos+1));
    auto expiry = std::chrono::system_clock::from_time_t(expiry_ts);
    if (std::chrono::system_clock::now() > expiry) return false;
    auto expected = generateApiToken(client_id).first;
    expected = expected.substr(0, expected.rfind(':'));
    return token_part == expected;
}

std::string WIPAuth::calculateAuthHash(int packet_id, int timestamp, const std::string &passphrase) {
    std::string data = std::to_string(packet_id) + ":" + std::to_string(timestamp) + ":" + passphrase;
    unsigned char md[EVP_MAX_MD_SIZE];
    unsigned int md_len = 0;
    HMAC(EVP_sha256(), passphrase.data(), (int)passphrase.size(),
         reinterpret_cast<const unsigned char *>(data.data()), data.size(), md, &md_len);
    return to_hex(md, md_len);
}

bool WIPAuth::verifyAuthHash(int packet_id, int timestamp,
                             const std::string &passphrase,
                             const std::string &received_hash) {
    return calculateAuthHash(packet_id, timestamp, passphrase) == received_hash;
}

} // namespace utils
} // namespace common
