#pragma once

#include <cstdint>
#include <vector>
#include <string>
#include <variant>
#include <optional>
#include <span>
#include <unordered_map>
#include <array>
#include "wiplib/packet/packet.hpp"

namespace wiplib::packet {

/**
 * @brief 拡張フィールドのキータイプ定義
 */
enum class ExtendedFieldKey : uint8_t {
    Alert = 1,
    Disaster = 2,
    Coordinate = 3,
    AuthHash = 4,
    CustomData = 5,
    SensorReading = 6,
    Metadata = 7,
    SourceInfo = 40,
    // 8-39 and 41-63 are reserved for future use
};

/**
 * @brief 拡張フィールドのデータタイプ
 */
enum class ExtendedDataType : uint8_t {
    StringList = 0,
    Coordinate = 1,
    Source = 2,
    Binary = 3,
    Float32 = 4,
    Json = 5,
    Integer = 6,
    Boolean = 7
};

/**
 * @brief 座標データ構造体（拡張フィールド用）
 */
struct ExtendedCoordinate {
    float latitude = 0.0f;
    float longitude = 0.0f;
    
    std::vector<uint8_t> pack() const;
    static std::optional<ExtendedCoordinate> unpack(std::span<const uint8_t> data);
};

/**
 * @brief ソース情報構造体
 */
struct SourceInfo {
    uint8_t source_id = 0;
    uint32_t timestamp = 0;
    uint8_t quality = 255;
    
    std::vector<uint8_t> pack() const;
    static std::optional<SourceInfo> unpack(std::span<const uint8_t> data);
};

/**
 * @brief 拡張フィールド値の型バリアント
 */
using ExtendedFieldValue = std::variant<
    std::vector<std::string>,  // StringList
    ExtendedCoordinate,        // Coordinate
    SourceInfo,                // Source
    std::vector<uint8_t>,      // Binary
    float,                     // Float32
    std::string,               // Json
    int64_t,                   // Integer
    bool                       // Boolean
>;

/**
 * @brief 拡張フィールドヘッダー構造体（16bit: 10bit length + 6bit key）
 * Note: on-wire encoding uses little-endian for the 16-bit header to match codec.
 */
struct ExtendedFieldHeader {
    unsigned length : 10;  // データ長（0-1023）
    unsigned key    : 6;   // キー（0-63）
    
    ExtendedFieldHeader() : length(0u), key(0u) {}
    ExtendedFieldHeader(unsigned len, unsigned k) : length(len), key(k) {}
    
    /**
     * @brief ヘッダーをバイト配列にパック（little-endian）
     * @return パックされたヘッダー（2バイト）
     */
    std::array<uint8_t, 2> pack() const;
    
    /**
     * @brief バイト配列からヘッダーをアンパック（little-endian）
     * @param data バイト配列（最低2バイト）
     * @return アンパックされたヘッダー
     */
    static ExtendedFieldHeader unpack(std::span<const uint8_t> data);
};

/**
 * @brief 拡張フィールド処理クラス
 */
class ExtendedFieldProcessor {
public:
    /**
     * @brief 拡張フィールドを作成
     * @param key フィールドキー
     * @param value フィールド値
     * @return 作成された拡張フィールド
     */
    static proto::ExtendedField create_field(ExtendedFieldKey key, const ExtendedFieldValue& value);
    
    /**
     * @brief 拡張フィールドからヘッダーを抽出
     * @param field 拡張フィールド
     * @return ヘッダー情報
     */
    static ExtendedFieldHeader extract_header(const proto::ExtendedField& field);
    
    /**
     * @brief 拡張フィールドから値を抽出
     * @param field 拡張フィールド
     * @return 抽出された値
     */
    static std::optional<ExtendedFieldValue> extract_value(const proto::ExtendedField& field);
    
    /**
     * @brief 値をバイナリデータにパック
     * @param type データタイプ
     * @param value 値
     * @return パックされたバイナリデータ
     */
    static std::vector<uint8_t> pack_value(ExtendedDataType type, const ExtendedFieldValue& value);
    
    /**
     * @brief バイナリデータから値をアンパック
     * @param type データタイプ
     * @param data バイナリデータ
     * @return アンパックされた値
     */
    static std::optional<ExtendedFieldValue> unpack_value(ExtendedDataType type, std::span<const uint8_t> data);
    
    /**
     * @brief 拡張フィールドを検証
     * @param field 拡張フィールド
     * @return 検証成功時true
     */
    static bool validate_field(const proto::ExtendedField& field);
    
    /**
     * @brief パケットの拡張フィールドサイズを計算
     * @param fields 拡張フィールドリスト
     * @return 総サイズ（バイト）
     */
    static size_t calculate_extensions_size(const std::vector<proto::ExtendedField>& fields);

private:
    static ExtendedDataType key_to_data_type(ExtendedFieldKey key);
    static std::vector<uint8_t> pack_string_list(const std::vector<std::string>& strings);
    static std::optional<std::vector<std::string>> unpack_string_list(std::span<const uint8_t> data);
    static std::vector<uint8_t> pack_float32(float value);
    static std::optional<float> unpack_float32(std::span<const uint8_t> data);
    static std::vector<uint8_t> pack_integer(int64_t value);
    static std::optional<int64_t> unpack_integer(std::span<const uint8_t> data);
    static std::vector<uint8_t> pack_boolean(bool value);
    static std::optional<bool> unpack_boolean(std::span<const uint8_t> data);
};

/**
 * @brief 拡張フィールドマネージャークラス
 */
class ExtendedFieldManager {
public:
    /**
     * @brief パケットに拡張フィールドを追加
     * @param packet パケット
     * @param key フィールドキー
     * @param value フィールド値
     */
    static void add_field(proto::Packet& packet, ExtendedFieldKey key, const ExtendedFieldValue& value);
    
    /**
     * @brief パケットから拡張フィールドを取得
     * @param packet パケット
     * @param key フィールドキー
     * @return フィールド値（見つからない場合nullopt）
     */
    static std::optional<ExtendedFieldValue> get_field(const proto::Packet& packet, ExtendedFieldKey key);
    
    /**
     * @brief パケットから指定キーの拡張フィールドを削除
     * @param packet パケット
     * @param key フィールドキー
     * @return 削除された場合true
     */
    static bool remove_field(proto::Packet& packet, ExtendedFieldKey key);
    
    /**
     * @brief パケットのすべての拡張フィールドを取得
     * @param packet パケット
     * @return フィールドマップ
     */
    static std::unordered_map<ExtendedFieldKey, ExtendedFieldValue> get_all_fields(const proto::Packet& packet);
    
    /**
     * @brief パケットに特定のキーが存在するかチェック
     * @param packet パケット
     * @param key フィールドキー
     * @return 存在する場合true
     */
    static bool has_field(const proto::Packet& packet, ExtendedFieldKey key);
    
    /**
     * @brief パケットの拡張フィールド数を取得
     * @param packet パケット
     * @return フィールド数
     */
    static size_t get_field_count(const proto::Packet& packet);
    
    /**
     * @brief パケットの拡張フィールドを検証
     * @param packet パケット
     * @return 検証成功時true
     */
    static bool validate_extensions(const proto::Packet& packet);
};

} // namespace wiplib::packet
