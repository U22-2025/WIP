#include <gtest/gtest.h>
#include "wiplib/packet/checksum.hpp"

using namespace wiplib::packet;

class ChecksumTest : public ::testing::Test {
protected:
    void SetUp() override {}
    void TearDown() override {}
};

// 基本的なチェックサム計算テスト
TEST_F(ChecksumTest, BasicChecksumCalculation) {
    std::vector<uint8_t> data = {0x01, 0x02, 0x03, 0x04};
    uint16_t checksum = calc_checksum12(data);
    
    // 12ビットチェックサムは0-4095の範囲
    EXPECT_LE(checksum, 0x0FFF);
}

// 空データのテスト
TEST_F(ChecksumTest, EmptyDataChecksum) {
    std::vector<uint8_t> empty_data;
    uint16_t checksum = calc_checksum12(empty_data);
    EXPECT_EQ(checksum, 0);
}

// 単一バイトのテスト
TEST_F(ChecksumTest, SingleByteChecksum) {
    std::vector<uint8_t> data = {0xFF};
    uint16_t checksum = calc_checksum12(data);
    EXPECT_LE(checksum, 0x0FFF);
    EXPECT_GT(checksum, 0);
}

// チェックサム検証テスト
TEST_F(ChecksumTest, ChecksumVerification) {
    std::vector<uint8_t> data = {0x12, 0x34, 0x56, 0x78};
    uint16_t checksum = calc_checksum12(data);
    
    // 正しいチェックサムでの検証
    EXPECT_TRUE(verify_checksum12(data, checksum));
    
    // 間違ったチェックサムでの検証
    EXPECT_FALSE(verify_checksum12(data, checksum + 1));
}

// 大きなデータでのテスト
TEST_F(ChecksumTest, LargeDataChecksum) {
    std::vector<uint8_t> large_data(1024);
    for (size_t i = 0; i < large_data.size(); ++i) {
        large_data[i] = static_cast<uint8_t>(i & 0xFF);
    }
    
    uint16_t checksum = calc_checksum12(large_data);
    EXPECT_LE(checksum, 0x0FFF);
    EXPECT_TRUE(verify_checksum12(large_data, checksum));
}

// キャリーフォールドのテスト
TEST_F(ChecksumTest, CarryFoldHandling) {
    // キャリーが発生するデータパターン
    std::vector<uint8_t> data = {0xFF, 0xFF, 0xFF, 0xFF};
    uint16_t checksum = calc_checksum12(data);
    
    EXPECT_LE(checksum, 0x0FFF);
    EXPECT_TRUE(verify_checksum12(data, checksum));
}

// 境界値テスト
TEST_F(ChecksumTest, BoundaryValues) {
    // 最小値
    std::vector<uint8_t> min_data = {0x00};
    uint16_t min_checksum = calc_checksum12(min_data);
    EXPECT_EQ(min_checksum, 0);
    
    // 最大値
    std::vector<uint8_t> max_data = {0xFF};
    uint16_t max_checksum = calc_checksum12(max_data);
    EXPECT_LE(max_checksum, 0x0FFF);
}

// 同じデータは同じチェックサムを生成するテスト
TEST_F(ChecksumTest, Deterministic) {
    std::vector<uint8_t> data = {0xAB, 0xCD, 0xEF};
    uint16_t checksum1 = calc_checksum12(data);
    uint16_t checksum2 = calc_checksum12(data);
    
    EXPECT_EQ(checksum1, checksum2);
}

// 異なるデータは異なるチェックサムを生成する可能性が高いテスト
TEST_F(ChecksumTest, DifferentDataDifferentChecksum) {
    std::vector<uint8_t> data1 = {0x01, 0x02, 0x03};
    std::vector<uint8_t> data2 = {0x03, 0x02, 0x01};
    
    uint16_t checksum1 = calc_checksum12(data1);
    uint16_t checksum2 = calc_checksum12(data2);
    
    // 必ずしも異なるとは限らないが、通常は異なるはず
    EXPECT_NE(checksum1, checksum2);
}