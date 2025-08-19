#include <gtest/gtest.h>
#include <string>
#include <vector>
#include <cctype>

#include "wiplib/utils/auth.hpp"
#include "wiplib/packet/packet.hpp"
#include "wiplib/packet/extended_field.hpp"

using namespace wiplib;
using namespace wiplib::utils;
using namespace wiplib::proto;
using namespace wiplib::packet;

namespace {
// simple hex utils for tests
bool is_hex_lower(const std::vector<uint8_t>& v){
    for (auto c : v) {
        if (!std::isdigit(c) && !(c>='a' && c<='f')) return false;
    }
    return true;
}

std::vector<uint8_t> hex_to_bytes(const std::vector<uint8_t>& hex){
    auto hexval = [](uint8_t c)->int { if (c>='0'&&c<='9') return c-'0'; if (c>='a'&&c<='f') return c-'a'+10; if (c>='A'&&c<='F') return c-'A'+10; return -1; };
    std::vector<uint8_t> out; out.reserve(hex.size()/2);
    for (size_t i=0;i+1<hex.size(); i+=2){ int hi=hexval(hex[i]); int lo=hexval(hex[i+1]); if (hi<0||lo<0) return {}; out.push_back(static_cast<uint8_t>((hi<<4)|lo)); }
    return out;
}
}

TEST(AuthCompat, AttachAddsExtAndFlags){
    Packet p{};
    p.header.version = 1;
    p.header.packet_id = 10; // 12-bit id
    p.header.type = PacketType::WeatherRequest;
    p.header.timestamp = 123456;

    bool ok = WIPAuth::attach_auth_hash(p, "pass");
    ASSERT_TRUE(ok);
    ASSERT_TRUE(p.header.flags.extended);
    ASSERT_TRUE(p.header.flags.request_auth);

    // find ext id=AuthHash
    const ExtendedField* ext = nullptr;
    for (const auto& ef : p.extensions)
        if (ef.data_type == static_cast<uint8_t>(ExtendedFieldKey::AuthHash)) { ext = &ef; break; }
    ASSERT_NE(ext, nullptr);
    ASSERT_EQ(ext->data.size(), 64u);
    EXPECT_TRUE(is_hex_lower(ext->data));
}

TEST(AuthCompat, VerifyUsingExtension){
    Packet p{}; p.header.version=1; p.header.packet_id=10; p.header.type=PacketType::WeatherRequest; p.header.timestamp=123456;
    ASSERT_TRUE(WIPAuth::attach_auth_hash(p, "pass"));
    const ExtendedField* ext = nullptr; for (const auto& ef : p.extensions)
        if (ef.data_type==static_cast<uint8_t>(ExtendedFieldKey::AuthHash)){ ext=&ef; break; }
    ASSERT_NE(ext, nullptr);
    auto mac = hex_to_bytes(ext->data);
    ASSERT_EQ(mac.size(), 32u);
    EXPECT_TRUE(WIPAuth::verify_auth_hash(p.header.packet_id, p.header.timestamp, std::string("pass"), mac));
    // wrong passphrase should not verify
    EXPECT_FALSE(WIPAuth::verify_auth_hash(p.header.packet_id, p.header.timestamp, std::string("wrong"), mac));
}

TEST(AuthCompat, DifferentInputsProduceDifferentHMAC){
    Packet p1{}; p1.header.version=1; p1.header.packet_id=10; p1.header.type=PacketType::WeatherRequest; p1.header.timestamp=123456; ASSERT_TRUE(WIPAuth::attach_auth_hash(p1, "pass"));
    Packet p2{}; p2.header.version=1; p2.header.packet_id=10; p2.header.type=PacketType::WeatherRequest; p2.header.timestamp=123456; ASSERT_TRUE(WIPAuth::attach_auth_hash(p2, "pass2"));
    const ExtendedField *e1=nullptr,*e2=nullptr; for (const auto& ef : p1.extensions)
        if (ef.data_type==static_cast<uint8_t>(ExtendedFieldKey::AuthHash)){ e1=&ef; break; }
    for (const auto& ef : p2.extensions)
        if (ef.data_type==static_cast<uint8_t>(ExtendedFieldKey::AuthHash)){ e2=&ef; break; }
    ASSERT_NE(e1, nullptr); ASSERT_NE(e2, nullptr);
    EXPECT_NE(e1->data, e2->data);

    // Also timestamp difference should yield different MAC
    Packet p3{}; p3.header.version=1; p3.header.packet_id=10; p3.header.type=PacketType::WeatherRequest; p3.header.timestamp=123457; ASSERT_TRUE(WIPAuth::attach_auth_hash(p3, "pass"));
    const ExtendedField* e3=nullptr; for (const auto& ef : p3.extensions)
        if (ef.data_type==static_cast<uint8_t>(ExtendedFieldKey::AuthHash)){ e3=&ef; break; }
    ASSERT_NE(e3, nullptr);
    EXPECT_NE(e1->data, e3->data);
}

