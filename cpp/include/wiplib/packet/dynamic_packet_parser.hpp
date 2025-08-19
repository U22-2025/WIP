#pragma once

#include <vector>
#include <string>
#include <unordered_map>
#include <optional>
#include <span>
#include <memory>
#include <functional>
#include <atomic>
#include <cstring>

#include "wiplib/packet/format_parser.hpp"
#include "wiplib/packet/types.hpp"

namespace wiplib::packet {

/**
 * @brief 動的パケット値
 */
struct DynamicFieldValue {
    std::string field_name;
    FieldType field_type;
    
    union {
        uint64_t uint_value;
        int64_t int_value;
        float float_value;
        double double_value;
    };
    
    std::string string_value;
    std::vector<uint8_t> binary_value;
    
    DynamicFieldValue() : field_name(""), field_type(FieldType::UInt), uint_value(0) {}
    
    DynamicFieldValue(const std::string& name, FieldType type) 
        : field_name(name), field_type(type), uint_value(0) {}
};

/**
 * @brief 動的パケット解析結果
 */
struct DynamicPacketResult {
    std::string packet_type;
    std::vector<DynamicFieldValue> fields;
    std::vector<DynamicFieldValue> extended_fields;
    bool is_valid = false;
    std::string error_message;
    
    /**
     * @brief フィールド値を取得
     * @param field_name フィールド名
     * @return フィールド値（見つからない場合nullopt）
     */
    std::optional<DynamicFieldValue> get_field(const std::string& field_name) const;
    
    /**
     * @brief 拡張フィールド値を取得
     * @param field_key フィールドキー
     * @return フィールド値（見つからない場合nullopt）
     */
    std::optional<DynamicFieldValue> get_extended_field(uint8_t field_key) const;
    
    /**
     * @brief すべてのフィールドを取得
     * @return フィールド名→値のマップ
     */
    std::unordered_map<std::string, DynamicFieldValue> get_all_fields() const;
};

/**
 * @brief JSON仕様ベースの動的パケット解析器
 */
class DynamicPacketParser {
public:
    /**
     * @brief コンストラクタ
     * @param spec_directory JSON仕様ファイルのディレクトリ
     */
    explicit DynamicPacketParser(const std::string& spec_directory = "src/packet/format_spec/");
    
    /**
     * @brief パケット仕様を読み込み
     * @param packet_type パケット種別（"request", "response", "extended"）
     * @return 成功時true
     */
    bool load_packet_spec(const std::string& packet_type);
    
    /**
     * @brief バイナリデータを動的解析
     * @param data パケットデータ
     * @param packet_type 解析に使用する仕様種別
     * @return 解析結果
     */
    DynamicPacketResult parse_packet(std::span<const uint8_t> data, const std::string& packet_type) const;
    
    /**
     * @brief 拡張フィールドを動的解析
     * @param data 拡張フィールドデータ
     * @param field_key フィールドキー
     * @return 解析されたフィールド値
     */
    std::optional<DynamicFieldValue> parse_extended_field(std::span<const uint8_t> data, uint8_t field_key) const;
    
    /**
     * @brief 動的パケット構築
     * @param packet_type パケット種別
     * @param field_values フィールド値マップ
     * @return 構築されたパケットデータ
     */
    std::vector<uint8_t> build_packet(const std::string& packet_type, 
                                     const std::unordered_map<std::string, DynamicFieldValue>& field_values) const;
    
    /**
     * @brief フィールド検証
     * @param packet_type パケット種別
     * @param field_values フィールド値
     * @return 検証結果
     */
    bool validate_fields(const std::string& packet_type, 
                        const std::unordered_map<std::string, DynamicFieldValue>& field_values) const;
    
    /**
     * @brief デバッグ用パケット情報表示
     * @param result 解析結果
     * @return 人間可読形式の文字列
     */
    std::string debug_dump(const DynamicPacketResult& result) const;
    
    /**
     * @brief カスタムフィールドハンドラーを設定
     * @param field_type フィールド型
     * @param parser_func パーサー関数
     * @param builder_func ビルダー関数
     */
    void set_custom_field_handler(FieldType field_type,
                                 std::function<DynamicFieldValue(std::span<const uint8_t>)> parser_func,
                                 std::function<std::vector<uint8_t>(const DynamicFieldValue&)> builder_func);
    
    /**
     * @brief パフォーマンス統計を取得
     * @return 統計情報
     */
    std::unordered_map<std::string, uint64_t> get_performance_stats() const;
    
    /**
     * @brief 統計をリセット
     */
    void reset_performance_stats();

private:
    std::string spec_directory_;
    std::unordered_map<std::string, PacketSpecification> loaded_specs_;
    
    // カスタムハンドラー
    std::unordered_map<FieldType, std::function<DynamicFieldValue(std::span<const uint8_t>)>> custom_parsers_;
    std::unordered_map<FieldType, std::function<std::vector<uint8_t>(const DynamicFieldValue&)>> custom_builders_;
    
    // パフォーマンス統計
    mutable std::atomic<uint64_t> total_parsed_packets_{0};
    mutable std::atomic<uint64_t> total_built_packets_{0};
    mutable std::atomic<uint64_t> parsing_errors_{0};
    mutable std::atomic<uint64_t> validation_errors_{0};
    
    // プライベートメソッド
    DynamicFieldValue parse_field_value(const FieldDefinition& field_def, std::span<const uint8_t> data) const;
    DynamicFieldValue parse_extended_field_value(const ExtendedFieldDefinition& field_def, std::span<const uint8_t> data) const;
    
    void write_field_value(const FieldDefinition& field_def, const DynamicFieldValue& value, std::span<uint8_t> data) const;
    std::vector<uint8_t> build_extended_field_value(const ExtendedFieldDefinition& field_def, const DynamicFieldValue& value) const;
    
    uint64_t extract_bits(std::span<const uint8_t> data, uint32_t bit_offset, uint8_t bit_length) const;
    void insert_bits(std::span<uint8_t> data, uint32_t bit_offset, uint8_t bit_length, uint64_t value) const;
    
    std::string get_spec_file_path(const std::string& packet_type) const;
    bool ensure_spec_loaded(const std::string& packet_type) const;
    
    void record_parsing_error(const std::string& error_message) const;
    void record_validation_error(const std::string& error_message) const;
};

/**
 * @brief 動的パケット解析ファクトリー
 */
class DynamicPacketParserFactory {
public:
    /**
     * @brief 標準設定のパーサーを作成
     */
    static std::unique_ptr<DynamicPacketParser> create_standard();
    
    /**
     * @brief 高速パーサーを作成（検証スキップ）
     */
    static std::unique_ptr<DynamicPacketParser> create_fast();
    
    /**
     * @brief デバッグ用パーサーを作成（詳細ログ付き）
     */
    static std::unique_ptr<DynamicPacketParser> create_debug();
    
    /**
     * @brief カスタム仕様ディレクトリでパーサーを作成
     */
    static std::unique_ptr<DynamicPacketParser> create_with_specs(const std::string& spec_directory);
};

/**
 * @brief 動的パケット解析ユーティリティ
 */
namespace dynamic_utils {
    /**
     * @brief フィールド値を文字列に変換
     */
    std::string field_value_to_string(const DynamicFieldValue& value);
    
    /**
     * @brief 文字列からフィールド値を作成
     */
    DynamicFieldValue string_to_field_value(const std::string& str_value, FieldType field_type, const std::string& field_name);
    
    /**
     * @brief バイナリデータをヘキサダンプ
     */
    std::string hex_dump(std::span<const uint8_t> data, size_t bytes_per_line = 16);
    
    /**
     * @brief パケット解析結果をJSON形式で出力
     */
    std::string result_to_json(const DynamicPacketResult& result);
    
    /**
     * @brief JSON文字列から解析結果を復元
     */
    std::optional<DynamicPacketResult> json_to_result(const std::string& json_str);
}

} // namespace wiplib::packet