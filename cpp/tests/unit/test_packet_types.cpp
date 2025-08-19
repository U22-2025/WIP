#include <gtest/gtest.h>
#include "wiplib/packet/codec.hpp"
#include "wiplib/packet/request.hpp"
#include "wiplib/packet/response.hpp"

using namespace wiplib::proto;

class PacketTypesTest : public ::testing::Test {
protected:
    void SetUp() override {}
    void TearDown() override {}
    
    Header createTestHeader() {
        Header h{};
        h.version = 1;
        h.packet_id = 0x123;
        h.type = PacketType::WeatherRequest;
        h.flags.weather = true;
        h.flags.temperature = true;
        h.day = 2;
        h.timestamp = 0x0123456789ABCDEFULL;
        h.area_code = 130010;
        return h;
    }
};

// Header エンコード/デコードテスト
TEST_F(PacketTypesTest, HeaderEncodeDecode) {
    Header original = createTestHeader();
    
    auto encoded = encode_header(original);
    ASSERT_TRUE(encoded.has_value());
    EXPECT_EQ(encoded.value().size(), 16);  // Fixed header size
    
    auto decoded = decode_header(encoded.value());
    ASSERT_TRUE(decoded.has_value());
    
    auto& h = decoded.value();
    EXPECT_EQ(h.version, original.version);
    EXPECT_EQ(h.packet_id, original.packet_id);
    EXPECT_EQ(h.type, original.type);
    EXPECT_EQ(h.day, original.day);
    EXPECT_EQ(h.timestamp, original.timestamp);
    EXPECT_EQ(h.area_code, original.area_code);
    EXPECT_EQ(h.flags.weather, original.flags.weather);
    EXPECT_EQ(h.flags.temperature, original.flags.temperature);
}

// 基本的なパケットエンコード/デコードテスト
TEST_F(PacketTypesTest, BasicPacketEncodeDecode) {
    Packet original;
    original.header = createTestHeader();
    
    auto encoded = encode_packet(original);
    ASSERT_TRUE(encoded.has_value());
    
    auto decoded = decode_packet(encoded.value());
    ASSERT_TRUE(decoded.has_value());
    
    auto& packet = decoded.value();
    EXPECT_EQ(packet.header.version, original.header.version);
    EXPECT_EQ(packet.header.packet_id, original.header.packet_id);
    EXPECT_EQ(packet.header.type, original.header.type);
}

// パケットタイプのテスト
TEST_F(PacketTypesTest, PacketTypeValues) {
    Header h = createTestHeader();
    
    // 天気リクエスト
    h.type = PacketType::WeatherRequest;
    auto encoded1 = encode_header(h);
    ASSERT_TRUE(encoded1.has_value());
    auto decoded1 = decode_header(encoded1.value());
    ASSERT_TRUE(decoded1.has_value());
    EXPECT_EQ(decoded1.value().type, PacketType::WeatherRequest);
    
    // 天気レスポンス
    h.type = PacketType::WeatherResponse;
    auto encoded2 = encode_header(h);
    ASSERT_TRUE(encoded2.has_value());
    auto decoded2 = decode_header(encoded2.value());
    ASSERT_TRUE(decoded2.has_value());
    EXPECT_EQ(decoded2.value().type, PacketType::WeatherResponse);
}

// フラグフィールドのテスト
TEST_F(PacketTypesTest, FlagsField) {
    Header h = createTestHeader();
    h.flags.weather = true;
    h.flags.temperature = false;
    
    auto encoded = encode_header(h);
    ASSERT_TRUE(encoded.has_value());
    auto decoded = decode_header(encoded.value());
    ASSERT_TRUE(decoded.has_value());
    
    auto& flags = decoded.value().flags;
    EXPECT_TRUE(flags.weather);
    EXPECT_FALSE(flags.temperature);
}

// 境界値テスト
TEST_F(PacketTypesTest, BoundaryValues) {
    Header h = createTestHeader();
    
    // 最小値
    h.version = 0;
    h.packet_id = 0;
    h.day = 0;
    h.timestamp = 0;
    h.area_code = 0;
    
    auto encoded = encode_header(h);
    ASSERT_TRUE(encoded.has_value());
    auto decoded = decode_header(encoded.value());
    ASSERT_TRUE(decoded.has_value());
    
    auto& result = decoded.value();
    EXPECT_EQ(result.version, 0);
    EXPECT_EQ(result.packet_id, 0);
    EXPECT_EQ(result.day, 0);
    EXPECT_EQ(result.timestamp, 0);
    EXPECT_EQ(result.area_code, 0);
}

// 無効なデータのテスト
TEST_F(PacketTypesTest, InvalidData) {
    // 短すぎるデータ
    std::vector<uint8_t> short_data = {0x01, 0x02, 0x03};
    auto result = decode_header(short_data);
    EXPECT_FALSE(result.has_value());
    
    // 空のデータ
    std::vector<uint8_t> empty_data;
    auto result2 = decode_header(empty_data);
    EXPECT_FALSE(result2.has_value());
}