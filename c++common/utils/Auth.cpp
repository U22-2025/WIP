#include "Auth.hpp"
#include <openssl/hmac.h>
#include <openssl/evp.h>
#include <sstream>
#include <iomanip>
#include <cstdlib>

namespace {
std::string to_hex(const unsigned char* data, std::size_t len) {
    std::ostringstream oss;
    for (std::size_t i = 0; i < len; ++i) {
        oss << std::hex << std::setw(2) << std::setfill('0') << static_cast<int>(data[i]);
    }
    return oss.str();
}
}

WIPAuth::WIPAuth(const std::string &secret_key)
    : secret_key_(secret_key.empty() ? std::getenv("WIP_SECRET_KEY") ? std::getenv("WIP_SECRET_KEY") : "" : secret_key),
      token_expiry_(std::chrono::hours(1))
{
    if (secret_key_.empty()) {
        throw std::runtime_error("WIP_SECRET_KEY not set");
    }
}

std::string WIPAuth::generate_packet_signature(const std::vector<unsigned char> &data) const {
    unsigned int len = EVP_MAX_MD_SIZE;
    unsigned char result[EVP_MAX_MD_SIZE];
    HMAC(EVP_sha256(), secret_key_.data(), secret_key_.size(), data.data(), data.size(), result, &len);
    return to_hex(result, len);
}

bool WIPAuth::verify_packet_signature(const std::vector<unsigned char> &data, const std::string &signature) const {
    return generate_packet_signature(data) == signature;
}

std::pair<std::string, std::chrono::system_clock::time_point> WIPAuth::generate_api_token(const std::string &client_id) const {
    auto expiry = std::chrono::system_clock::now() + token_expiry_;
    auto ts = std::chrono::duration_cast<std::chrono::seconds>(expiry.time_since_epoch()).count();
    std::string token_data = client_id + ":" + std::to_string(ts);
    unsigned int len = EVP_MAX_MD_SIZE;
    unsigned char result[EVP_MAX_MD_SIZE];
    HMAC(EVP_sha256(), secret_key_.data(), secret_key_.size(), reinterpret_cast<const unsigned char*>(token_data.data()), token_data.size(), result, &len);
    std::string token = to_hex(result, len);
    return {token + ":" + std::to_string(ts), expiry};
}

bool WIPAuth::verify_api_token(const std::string &token, const std::string &client_id) const {
    auto pos = token.rfind(':');
    if (pos == std::string::npos) return false;
    std::string token_part = token.substr(0, pos);
    long expiry_ts = 0;
    try {
        expiry_ts = std::stol(token.substr(pos+1));
    } catch (...) {
        return false;
    }
    auto expiry = std::chrono::system_clock::time_point{std::chrono::seconds(expiry_ts)};
    if (std::chrono::system_clock::now() > expiry) return false;
    auto expected = generate_api_token(client_id).first;
    std::string expected_part = expected.substr(0, expected.find(':'));
    return token_part == expected_part;
}

std::vector<unsigned char> WIPAuth::calculate_auth_hash(int packet_id, int timestamp, const std::string &passphrase) {
    std::string data = std::to_string(packet_id) + ":" + std::to_string(timestamp) + ":" + passphrase;
    unsigned int len = EVP_MAX_MD_SIZE;
    std::vector<unsigned char> result(EVP_MAX_MD_SIZE);
    HMAC(EVP_sha256(), passphrase.data(), passphrase.size(), reinterpret_cast<const unsigned char*>(data.data()), data.size(), result.data(), &len);
    result.resize(len);
    return result;
}

bool WIPAuth::verify_auth_hash(int packet_id, int timestamp, const std::string &passphrase, const std::vector<unsigned char> &received_hash) {
    auto expected = calculate_auth_hash(packet_id, timestamp, passphrase);
    return expected == received_hash;
}

WIPAuth &get_default_auth() {
    static WIPAuth instance;
    return instance;
}

