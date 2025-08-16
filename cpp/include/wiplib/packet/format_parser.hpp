#pragma once

#include <string>
#include <memory>
#include <unordered_map>
#include "wiplib/packet/format_base.hpp"

namespace wiplib::packet {

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

private:
    static std::string read_file(const std::string& file_path);
    static FieldDefinition parse_field_definition(const std::unordered_map<std::string, std::string>& field_data);
};

} // namespace wiplib::packet