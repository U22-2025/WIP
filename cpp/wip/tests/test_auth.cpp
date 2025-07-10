#include "utils/Auth.hpp"
#include <catch2/catch_test_macros.hpp>

TEST_CASE("Packet signature", "[auth]") {
    WIPAuth auth("secret");
    std::vector<unsigned char> data{1,2,3,4};
    auto sig = auth.generate_packet_signature(data);
    REQUIRE(auth.verify_packet_signature(data, sig));
    std::vector<unsigned char> wrong{1,2,3};
    REQUIRE_FALSE(auth.verify_packet_signature(wrong, sig));
}

TEST_CASE("API token", "[auth]") {
    WIPAuth auth("secret");
    auto pair = auth.generate_api_token("client1");
    REQUIRE(auth.verify_api_token(pair.first, "client1"));
    REQUIRE_FALSE(auth.verify_api_token(pair.first, "client2"));
}

TEST_CASE("Auth hash", "[auth]") {
    int packet_id = 10;
    int timestamp = 12345;
    std::string passphrase = "pass";
    auto hash = WIPAuth::calculate_auth_hash(packet_id, timestamp, passphrase);
    REQUIRE(WIPAuth::verify_auth_hash(packet_id, timestamp, passphrase, hash));
    auto wrong = hash;
    wrong[0] ^= 0xFF;
    REQUIRE_FALSE(WIPAuth::verify_auth_hash(packet_id, timestamp, passphrase, wrong));
}
