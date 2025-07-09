#pragma once

#include <string>
#include <vector>
#include <chrono>
#include <optional>

class WIPAuth {
public:
    explicit WIPAuth(const std::string &secret_key = "");

    std::string generate_packet_signature(const std::vector<unsigned char> &data) const;
    bool verify_packet_signature(const std::vector<unsigned char> &data, const std::string &signature) const;

    std::pair<std::string, std::chrono::system_clock::time_point> generate_api_token(const std::string &client_id) const;
    bool verify_api_token(const std::string &token, const std::string &client_id) const;

    static std::vector<unsigned char> calculate_auth_hash(int packet_id, int timestamp, const std::string &passphrase);
    static bool verify_auth_hash(int packet_id, int timestamp, const std::string &passphrase, const std::vector<unsigned char> &received_hash);

private:
    std::string secret_key_;
    std::chrono::seconds token_expiry_;
};

WIPAuth &get_default_auth();

