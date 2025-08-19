#pragma once

#include <string>
#include <memory>
#include <unordered_map>
#include <vector>
#include <optional>
#include <cstdint>
#include <mutex>
#include "wiplib/packet/format_base.hpp"

namespace wiplib::packet {

/**
 * @brief フィールド型
 */
enum class FieldType {
    UInt,
    Int,
    Enum,
    Flags,
    Reserved,
    Timestamp,
    Checksum,
    StringList,
    Coordinate,
    Source,
    Binary,
    Float32,
    Json
};

/**
 * @brief 拡張フィールド定義
 */
struct ExtendedFieldDefinition {
    uint8_t key;
    std::string name;
    FieldType type;
    std::string description;
    std::string encoding;
    
    // 座標用フォーマット
    struct CoordinateFormat {
        uint8_t latitude_bits = 32;
        uint8_t longitude_bits = 32;
        std::string precision = "float32";
    };
    std::optional<CoordinateFormat> coordinate_format;
    
    // ソース情報用フォーマット
    struct SourceFormat {
        uint8_t source_id_bits = 8;
        uint8_t timestamp_bits = 32;
        uint8_t quality_bits = 8;
    };
    std::optional<SourceFormat> source_format;
};

/**
 * @brief パケット仕様
 */
struct PacketSpecification {
    std::string packet_type;
    uint16_t total_size_bytes;
    std::vector<FieldDefinition> fields;
    std::string description;
    
    // 拡張フィールド用
    std::vector<ExtendedFieldDefinition> extended_fields;
    
    struct ExtendedFormat {
        uint8_t header_bits = 16;
        uint8_t length_bits = 10;
        uint8_t key_bits = 6;
    };
    std::optional<ExtendedFormat> extended_format;
    
    // バリデーション設定
    struct ValidationConfig {
        uint8_t max_extended_fields = 16;
        uint16_t max_field_length = 1023;
        std::vector<std::string> supported_types;
    };
    std::optional<ValidationConfig> validation;
};

/**
 * @brief JSON設定ファイルからパケット仕様を解析するクラス
 */
class FormatParser {
public:
    /**
     * @brief JSONファイルからパケットフォーマットを読み込み
     * @param json_file_path JSONファイルパス
     * @return パケットフォーマットオブジェクト
     */
    static std::unique_ptr<PacketFormatBase> load_from_json(const std::string& json_file_path);

    /**
     * @brief JSON文字列からパケットフォーマットを読み込み
     * @param json_content JSON文字列
     * @return パケットフォーマットオブジェクト
     */
    static std::unique_ptr<PacketFormatBase> parse_from_string(const std::string& json_content);

    /**
     * @brief デフォルトのリクエストフォーマットを取得
     * @return リクエストパケットフォーマット
     */
    static std::unique_ptr<RequestPacketFormat> get_default_request_format();

    /**
     * @brief デフォルトのレスポンスフォーマットを取得
     * @return レスポンスパケットフォーマット
     */
    static std::unique_ptr<ResponsePacketFormat> get_default_response_format();
    
    /**
     * @brief リクエスト仕様を読み込み
     * @param json_file JSONファイルパス
     * @return パケット仕様
     */
    static std::optional<PacketSpecification> load_request_spec(const std::string& json_file);
    
    /**
     * @brief レスポンス仕様を読み込み
     * @param json_file JSONファイルパス
     * @return パケット仕様
     */
    static std::optional<PacketSpecification> load_response_spec(const std::string& json_file);
    
    /**
     * @brief 拡張フィールド仕様を読み込み
     * @param json_file JSONファイルパス
     * @return パケット仕様
     */
    static std::optional<PacketSpecification> load_extended_spec(const std::string& json_file);
    
    /**
     * @brief JSON文字列から仕様を解析
     * @param json_content JSON文字列
     * @return パケット仕様
     */
    static std::optional<PacketSpecification> parse_spec_from_string(const std::string& json_content);
    
    /**
     * @brief フィールド定義を検索
     * @param spec パケット仕様
     * @param field_name フィールド名
     * @return フィールド定義
     */
    static std::optional<FieldDefinition> find_field(const PacketSpecification& spec, const std::string& field_name);
    
    /**
     * @brief 拡張フィールド定義をキーで検索
     * @param spec パケット仕様
     * @param key フィールドキー
     * @return 拡張フィールド定義
     */
    static std::optional<ExtendedFieldDefinition> find_extended_field_by_key(const PacketSpecification& spec, uint8_t key);
    
    /**
     * @brief 仕様の妥当性をチェック
     * @param spec パケット仕様
     * @return 妥当性チェック結果
     */
    static bool validate_specification(const PacketSpecification& spec);
    
    /**
     * @brief フィールド型を文字列から変換
     * @param type_str 型文字列
     * @return フィールド型
     */
    static FieldType string_to_field_type(const std::string& type_str);
    
    /**
     * @brief フィールド型を文字列に変換
     * @param type フィールド型
     * @return 型文字列
     */
    static std::string field_type_to_string(FieldType type);
    
    /**
     * @brief 最後のエラーメッセージを取得
     */
    static std::string get_last_error();

private:
    static std::string last_error_;
    static std::mutex error_mutex_;
    
    static std::string read_file(const std::string& file_path);
    static FieldDefinition parse_field_definition(const std::unordered_map<std::string, std::string>& field_data);
    static void set_error(const std::string& error);
    
    // JSON解析用プライベートメソッド
    static bool parse_basic_field(const std::string& json_field, FieldDefinition& field);
    static bool parse_extended_field(const std::string& json_field, ExtendedFieldDefinition& field);
    static bool parse_coordinate_format(const std::string& json_format, ExtendedFieldDefinition::CoordinateFormat& format);
    static bool parse_source_format(const std::string& json_format, ExtendedFieldDefinition::SourceFormat& format);
    static bool parse_extended_format(const std::string& json_format, PacketSpecification::ExtendedFormat& format);
    static bool parse_validation_config(const std::string& json_validation, PacketSpecification::ValidationConfig& config);
    
    // バリデーション用メソッド
    static bool validate_field_definition(const FieldDefinition& field);
    static bool validate_extended_field_definition(const ExtendedFieldDefinition& field);
    static bool validate_bit_layout(const std::vector<FieldDefinition>& fields);
};

/**
 * @brief グローバル仕様パーサー
 */
class GlobalFormatSpecParser {
public:
    /**
     * @brief シングルトンインスタンスを取得
     */
    static FormatParser& instance();
    
    /**
     * @brief デフォルト仕様ディレクトリを設定
     * @param directory ディレクトリパス
     */
    static void set_spec_directory(const std::string& directory);
    
    /**
     * @brief 仕様キャッシュをクリア
     */
    static void clear_cache();

private:
    static std::unique_ptr<FormatParser> instance_;
    static std::mutex instance_mutex_;
    static std::string spec_directory_;
    static std::unordered_map<std::string, PacketSpecification> spec_cache_;
};

/**
 * @brief 仕様パーサーユーティリティ
 */
namespace spec_utils {
    /**
     * @brief ビット範囲が重複していないかチェック
     * @param fields フィールド定義一覧
     * @return 重複なしの場合true
     */
    bool check_bit_overlap(const std::vector<FieldDefinition>& fields);
    
    /**
     * @brief フィールドのビット範囲を取得
     * @param field フィールド定義
     * @return ビット範囲（開始、終了）
     */
    std::pair<uint32_t, uint32_t> get_bit_range(const FieldDefinition& field);
    
    /**
     * @brief 必須フィールドがすべて定義されているかチェック
     * @param spec パケット仕様
     * @param required_fields 必須フィールド名一覧
     * @return すべて定義されている場合true
     */
    bool check_required_fields(const PacketSpecification& spec, const std::vector<std::string>& required_fields);
    
    /**
     * @brief 仕様を人間可読形式でダンプ
     * @param spec パケット仕様
     * @return ダンプ文字列
     */
    std::string dump_specification(const PacketSpecification& spec);
}

} // namespace wiplib::packet