#include <gtest/gtest.h>
#include "wiplib/packet/extended_field.hpp"

using namespace wiplib::proto;

class ExtendedFieldTest : public ::testing::Test {
protected:
    void SetUp() override {}
    void TearDown() override {}
};

// 基本的な拡張フィールドのテスト
TEST_F(ExtendedFieldTest, BasicExtendedField) {
    ExtendedField field;
    field.data_type = 0b100001;  // 6ビットタイプ
    field.data = {0x01, 0x02, 0x03};
    
    EXPECT_EQ(field.data_type, 0b100001);
    EXPECT_EQ(field.data.size(), 3);
    EXPECT_EQ(field.data[0], 0x01);
    EXPECT_EQ(field.data[1], 0x02);
    EXPECT_EQ(field.data[2], 0x03);
}

// pack/unpack テスト
TEST_F(ExtendedFieldTest, PackUnpack) {
    ExtendedField original;
    original.data_type = 0b110010;
    original.data = {0xAA, 0xBB, 0xCC, 0xDD};
    
    auto packed = original.pack();
    ASSERT_TRUE(packed.has_value());
    
    auto unpacked = ExtendedField::unpack(*packed);
    ASSERT_TRUE(unpacked.has_value());
    
    EXPECT_EQ(unpacked->data_type, original.data_type);
    EXPECT_EQ(unpacked->data, original.data);
}

// 空データのテスト
TEST_F(ExtendedFieldTest, EmptyData) {
    ExtendedField field;
    field.data_type = 0b101010;
    field.data = {};  // 空データ
    
    auto packed = field.pack();
    ASSERT_TRUE(packed.has_value());
    
    auto unpacked = ExtendedField::unpack(*packed);
    ASSERT_TRUE(unpacked.has_value());
    
    EXPECT_EQ(unpacked->data_type, field.data_type);
    EXPECT_TRUE(unpacked->data.empty());
}

// 最大サイズのデータテスト (10ビット長なので最大1023バイト)
TEST_F(ExtendedFieldTest, MaxSizeData) {
    ExtendedField field;
    field.data_type = 0b111111;  // 最大6ビット値
    field.data.resize(1023);  // 最大サイズ
    
    // データを埋める
    for (size_t i = 0; i < field.data.size(); ++i) {
        field.data[i] = static_cast<uint8_t>(i & 0xFF);
    }
    
    auto packed = field.pack();
    ASSERT_TRUE(packed.has_value());
    
    auto unpacked = ExtendedField::unpack(*packed);
    ASSERT_TRUE(unpacked.has_value());
    
    EXPECT_EQ(unpacked->data_type, field.data_type);
    EXPECT_EQ(unpacked->data.size(), field.data.size());
    
    // データの内容も確認
    for (size_t i = 0; i < field.data.size(); ++i) {
        EXPECT_EQ(unpacked->data[i], field.data[i]);
    }
}

// ヘッダフォーマットテスト (10bit length + 6bit key)
TEST_F(ExtendedFieldTest, HeaderFormat) {
    ExtendedField field;
    field.data_type = 0b100110;  // 6ビットキー
    field.data = {0x11, 0x22, 0x33, 0x44, 0x55};  // 5バイト
    
    auto packed = field.pack();
    ASSERT_TRUE(packed.has_value());
    ASSERT_GE(packed->size(), 2);  // ヘッダー2バイト + データ
    
    // ヘッダー解析
    uint16_t header = (static_cast<uint16_t>((*packed)[0]) << 8) | (*packed)[1];
    uint16_t length = (header >> 6) & 0x3FF;  // 上位10ビット
    uint8_t key = header & 0x3F;              // 下位6ビット
    
    EXPECT_EQ(length, 5);          // データ長
    EXPECT_EQ(key, 0b100110);      // キー
}

// 型別エンコーディングテスト - 文字列
TEST_F(ExtendedFieldTest, StringEncoding) {
    ExtendedField field;
    field.data_type = 0b000001;  // string type
    std::string test_str = "Hello, World!";
    field.data = std::vector<uint8_t>(test_str.begin(), test_str.end());
    
    auto packed = field.pack();
    ASSERT_TRUE(packed.has_value());
    
    auto unpacked = ExtendedField::unpack(*packed);
    ASSERT_TRUE(unpacked.has_value());
    
    std::string result_str(unpacked->data.begin(), unpacked->data.end());
    EXPECT_EQ(result_str, test_str);
}

// 型別エンコーディングテスト - 座標データ
TEST_F(ExtendedFieldTest, CoordinateEncoding) {
    ExtendedField field;
    field.data_type = 0b000100;  // coordinate type
    
    // 座標データ（例：緯度35.6762、経度139.6503を整数で表現）
    uint32_t lat = 356762;  // 35.6762 * 10000
    uint32_t lon = 1396503; // 139.6503 * 10000
    
    field.data.resize(8);
    // リトルエンディアンで格納
    field.data[0] = lat & 0xFF;
    field.data[1] = (lat >> 8) & 0xFF;
    field.data[2] = (lat >> 16) & 0xFF;
    field.data[3] = (lat >> 24) & 0xFF;
    field.data[4] = lon & 0xFF;
    field.data[5] = (lon >> 8) & 0xFF;
    field.data[6] = (lon >> 16) & 0xFF;
    field.data[7] = (lon >> 24) & 0xFF;
    
    auto packed = field.pack();
    ASSERT_TRUE(packed.has_value());
    
    auto unpacked = ExtendedField::unpack(*packed);
    ASSERT_TRUE(unpacked.has_value());
    
    // 座標データを復元
    uint32_t result_lat = unpacked->data[0] | 
                         (unpacked->data[1] << 8) |
                         (unpacked->data[2] << 16) |
                         (unpacked->data[3] << 24);
    uint32_t result_lon = unpacked->data[4] | 
                         (unpacked->data[5] << 8) |
                         (unpacked->data[6] << 16) |
                         (unpacked->data[7] << 24);
    
    EXPECT_EQ(result_lat, lat);
    EXPECT_EQ(result_lon, lon);
}

// リスト型エンコーディングテスト
TEST_F(ExtendedFieldTest, ListEncoding) {
    ExtendedField field;
    field.data_type = 0b000010;  // list type
    
    // 数値のリスト [1, 2, 3, 4, 5] を1バイトずつ格納
    field.data = {0x01, 0x02, 0x03, 0x04, 0x05};
    
    auto packed = field.pack();
    ASSERT_TRUE(packed.has_value());
    
    auto unpacked = ExtendedField::unpack(*packed);
    ASSERT_TRUE(unpacked.has_value());
    
    EXPECT_EQ(unpacked->data_type, 0b000010);
    EXPECT_EQ(unpacked->data.size(), 5);
    for (size_t i = 0; i < 5; ++i) {
        EXPECT_EQ(unpacked->data[i], i + 1);
    }
}

// 無効なデータのテスト
TEST_F(ExtendedFieldTest, InvalidData) {
    // 空のパックデータ
    std::vector<uint8_t> empty_data;
    auto unpacked_empty = ExtendedField::unpack(empty_data);
    EXPECT_FALSE(unpacked_empty.has_value());
    
    // 不十分なヘッダーサイズ
    std::vector<uint8_t> insufficient_header = {0x01};
    auto unpacked_insufficient = ExtendedField::unpack(insufficient_header);
    EXPECT_FALSE(unpacked_insufficient.has_value());
    
    // ヘッダーで示されたサイズとデータサイズの不一致
    std::vector<uint8_t> size_mismatch = {0x00, 0x05, 0x01, 0x02};  // 5バイト宣言だが2バイトしかない
    auto unpacked_mismatch = ExtendedField::unpack(size_mismatch);
    EXPECT_FALSE(unpacked_mismatch.has_value());
}

// 境界値テスト
TEST_F(ExtendedFieldTest, BoundaryValues) {
    // 最小値
    ExtendedField min_field;
    min_field.data_type = 0;
    min_field.data = {};
    
    auto packed_min = min_field.pack();
    ASSERT_TRUE(packed_min.has_value());
    auto unpacked_min = ExtendedField::unpack(*packed_min);
    ASSERT_TRUE(unpacked_min.has_value());
    EXPECT_EQ(unpacked_min->data_type, 0);
    EXPECT_TRUE(unpacked_min->data.empty());
    
    // 最大キー値
    ExtendedField max_key_field;
    max_key_field.data_type = 0x3F;  // 6ビット最大値
    max_key_field.data = {0xFF};
    
    auto packed_max_key = max_key_field.pack();
    ASSERT_TRUE(packed_max_key.has_value());
    auto unpacked_max_key = ExtendedField::unpack(*packed_max_key);
    ASSERT_TRUE(unpacked_max_key.has_value());
    EXPECT_EQ(unpacked_max_key->data_type, 0x3F);
}

// 連続フィールドのテスト
TEST_F(ExtendedFieldTest, MultipleFields) {
    std::vector<ExtendedField> fields;
    
    // 複数のフィールドを作成
    for (int i = 0; i < 5; ++i) {
        ExtendedField field;
        field.data_type = i + 1;
        field.data = {static_cast<uint8_t>(0x10 + i), static_cast<uint8_t>(0x20 + i)};
        fields.push_back(field);
    }
    
    // 各フィールドをパック
    std::vector<std::vector<uint8_t>> packed_fields;
    for (const auto& field : fields) {
        auto packed = field.pack();
        ASSERT_TRUE(packed.has_value());
        packed_fields.push_back(*packed);
    }
    
    // 各フィールドをアンパック
    for (size_t i = 0; i < packed_fields.size(); ++i) {
        auto unpacked = ExtendedField::unpack(packed_fields[i]);
        ASSERT_TRUE(unpacked.has_value());
        EXPECT_EQ(unpacked->data_type, fields[i].data_type);
        EXPECT_EQ(unpacked->data, fields[i].data);
    }
}