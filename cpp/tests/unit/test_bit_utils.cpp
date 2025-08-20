#include <gtest/gtest.h>
#include "wiplib/packet/bit_utils.hpp"

using namespace wiplib::packet;

class BitUtilsTest : public ::testing::Test {
protected:
    void SetUp() override {}
    void TearDown() override {}
};

// extract_bits テスト
TEST_F(BitUtilsTest, ExtractBitsBasic) {
    uint32_t value = 0b11010110101001010011001100110011;
    
    // 最下位4ビット抽出
    EXPECT_EQ(extract_bits(value, 0, 4), 0b0011);
    
    // 中間の8ビット抽出 (ビット4-11)
    EXPECT_EQ(extract_bits(value, 4, 8), 0b10011001);
    
    // 最上位4ビット抽出 (ビット28-31)
    EXPECT_EQ(extract_bits(value, 28, 4), 0b1101);
}

// extract_bits 境界値テスト
TEST_F(BitUtilsTest, ExtractBitsBoundary) {
    uint32_t value = 0xFFFFFFFF;
    
    // 1ビット抽出
    EXPECT_EQ(extract_bits(value, 0, 1), 1);
    EXPECT_EQ(extract_bits(value, 31, 1), 1);
    
    // 全32ビット抽出
    EXPECT_EQ(extract_bits(value, 0, 32), 0xFFFFFFFF);
    
    // 0ビット抽出（無効だが安全に処理すべき）
    EXPECT_EQ(extract_bits(value, 0, 0), 0);
}

// set_bits テスト
TEST_F(BitUtilsTest, SetBitsBasic) {
    uint32_t value = 0;
    
    // 最下位4ビットに値を設定
    value = set_bits(value, 0, 4, 0b1010);
    EXPECT_EQ(value, 0b1010);
    
    // ビット4-7に値を設定
    value = set_bits(value, 4, 4, 0b1100);
    EXPECT_EQ(value, 0b11001010);
    
    // 既存ビットを上書き
    value = set_bits(value, 0, 4, 0b0101);
    EXPECT_EQ(value, 0b11000101);
}

// set_bits 複数フィールドテスト
TEST_F(BitUtilsTest, SetBitsMultipleFields) {
    uint32_t value = 0;
    
    // 複数のフィールドを設定
    value = set_bits(value, 0, 8, 0xFF);    // ビット0-7: 0xFF
    value = set_bits(value, 8, 8, 0xAA);    // ビット8-15: 0xAA
    value = set_bits(value, 16, 8, 0x55);   // ビット16-23: 0x55
    value = set_bits(value, 24, 8, 0x33);   // ビット24-31: 0x33
    
    EXPECT_EQ(value, 0x3355AAFF);
    
    // 各フィールドを個別に検証
    EXPECT_EQ(extract_bits(value, 0, 8), 0xFF);
    EXPECT_EQ(extract_bits(value, 8, 8), 0xAA);
    EXPECT_EQ(extract_bits(value, 16, 8), 0x55);
    EXPECT_EQ(extract_bits(value, 24, 8), 0x33);
}

// 往復テスト (set → extract)
TEST_F(BitUtilsTest, RoundTripTest) {
    uint32_t original = 0;
    
    // 様々なパターンでセット/抽出
    original = set_bits(original, 3, 5, 0b10110);
    EXPECT_EQ(extract_bits(original, 3, 5), 0b10110);
    
    original = set_bits(original, 12, 8, 0xAB);
    EXPECT_EQ(extract_bits(original, 12, 8), 0xAB);
    
    // 先に設定した値が保持されているか確認
    EXPECT_EQ(extract_bits(original, 3, 5), 0b10110);
}

// マスク操作テスト
TEST_F(BitUtilsTest, MaskOperations) {
    uint32_t value = 0xDEADBEEF;
    
    // 中間ビットのクリア
    value = set_bits(value, 8, 8, 0x00);
    EXPECT_EQ(extract_bits(value, 8, 8), 0x00);
    
    // 他のビットが影響を受けていないか確認
    EXPECT_EQ(extract_bits(value, 0, 8), 0xEF);
    EXPECT_EQ(extract_bits(value, 16, 8), 0xAD);
    EXPECT_EQ(extract_bits(value, 24, 8), 0xDE);
}

// LSB (Least Significant Bit) 関連テスト
TEST_F(BitUtilsTest, LSBOperations) {
    // 最下位ビットの設定と抽出
    uint32_t value = 0;
    
    value = set_bits(value, 0, 1, 1);
    EXPECT_EQ(extract_bits(value, 0, 1), 1);
    EXPECT_TRUE(value & 1);
    
    value = set_bits(value, 0, 1, 0);
    EXPECT_EQ(extract_bits(value, 0, 1), 0);
    EXPECT_FALSE(value & 1);
}

// エンディアン関連テスト
TEST_F(BitUtilsTest, EndiannessConsistency) {
    uint32_t value = 0x12345678;
    
    // バイト単位での抽出
    EXPECT_EQ(extract_bits(value, 0, 8), 0x78);   // 最下位バイト
    EXPECT_EQ(extract_bits(value, 8, 8), 0x56);   
    EXPECT_EQ(extract_bits(value, 16, 8), 0x34);  
    EXPECT_EQ(extract_bits(value, 24, 8), 0x12);  // 最上位バイト
}

// オーバーフローテスト
TEST_F(BitUtilsTest, OverflowHandling) {
    uint32_t value = 0;
    
    // 範囲を超える値を設定した場合の動作
    value = set_bits(value, 0, 4, 0xFF);  // 4ビットフィールドに8ビット値
    EXPECT_EQ(extract_bits(value, 0, 4), 0x0F);  // 下位4ビットのみ設定される
}

// 複雑なビットパターンテスト
TEST_F(BitUtilsTest, ComplexBitPatterns) {
    uint32_t value = 0;
    
    // 交互のビットパターン
    value = set_bits(value, 0, 16, 0xAAAA);  // 1010...パターン
    EXPECT_EQ(extract_bits(value, 0, 16), 0xAAAA);
    
    value = set_bits(value, 16, 16, 0x5555); // 0101...パターン
    EXPECT_EQ(extract_bits(value, 16, 16), 0x5555);
    
    // 全体の値を確認
    EXPECT_EQ(value, 0x5555AAAA);
}