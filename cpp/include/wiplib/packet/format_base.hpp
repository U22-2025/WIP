#pragma once

#include <cstdint>
#include <vector>
#include <span>
#include <string>
#include <unordered_map>
#include <memory>
#include "wiplib/packet/types.hpp"
#include "wiplib/packet/exceptions.hpp"

namespace wiplib::packet {

/**
 * @brief フィールド定義構造体
 */
struct FieldDefinition {
    enum class FieldType {
        UInt,
        Int,
        Enum,
        Flags,
        Reserved,
        Timestamp,
        Checksum
    };
    
    std::string name;
    uint32_t bit_offset;
    uint8_t bit_length;
    FieldType type = FieldType::UInt;
    std::string description;
    bool is_optional = false;
    uint64_t default_value = 0;
};

/**
 * @brief パケットフォーマット基盤クラス
 */
class PacketFormatBase {
public:
    PacketFormatBase() = default;
    virtual ~PacketFormatBase() = default;

    /**
     * @brief フィールド定義を追加
     * @param field フィールド定義
     */
    void add_field(const FieldDefinition& field);

    /**
     * @brief フィールド値を取得
     * @param field_name フィールド名
     * @param data データバイト配列
     * @return フィールド値
     */
    uint64_t get_field_value(const std::string& field_name, std::span<const uint8_t> data) const;

    /**
     * @brief フィールド値を設定
     * @param field_name フィールド名
     * @param value 設定する値
     * @param data データバイト配列
     */
    void set_field_value(const std::string& field_name, uint64_t value, std::span<uint8_t> data) const;

    /**
     * @brief パケットを検証
     * @param data データバイト配列
     * @return 検証成功時true
     */
    virtual bool validate(std::span<const uint8_t> data) const;

    /**
     * @brief チェックサムを自動計算
     * @param data データバイト配列
     * @return 計算されたチェックサム
     */
    virtual uint16_t calculate_checksum(std::span<const uint8_t> data) const;

    /**
     * @brief パケットサイズを取得
     * @return 最小パケットサイズ（バイト）
     */
    size_t get_packet_size() const;

    /**
     * @brief フィールド定義を取得
     * @param field_name フィールド名
     * @return フィールド定義（見つからない場合nullptr）
     */
    const FieldDefinition* get_field_definition(const std::string& field_name) const;

protected:
    std::unordered_map<std::string, FieldDefinition> fields_;
    size_t packet_size_ = 0;
};

/**
 * @brief リクエストパケットフォーマット
 */
class RequestPacketFormat : public PacketFormatBase {
public:
    RequestPacketFormat();
    
    bool validate(std::span<const uint8_t> data) const override;
};

/**
 * @brief レスポンスパケットフォーマット
 */
class ResponsePacketFormat : public PacketFormatBase {
public:
    ResponsePacketFormat();
    
    bool validate(std::span<const uint8_t> data) const override;
};

} // namespace wiplib::packet