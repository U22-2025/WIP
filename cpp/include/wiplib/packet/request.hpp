#pragma once

#include <cstdint>
#include <vector>
#include <string>
#include <optional>
#include <unordered_map>
#include <span>
#include <chrono>
#include "wiplib/packet/packet.hpp"

namespace wiplib::packet {

/**
 * @brief リクエスト優先度
 */
enum class RequestPriority : uint8_t {
    Low = 0,
    Normal = 1,
    High = 2,
    Critical = 3
};

/**
 * @brief リクエスト処理オプション
 */
struct RequestOptions {
    RequestPriority priority = RequestPriority::Normal;
    std::chrono::milliseconds timeout{30000}; // 30秒デフォルト
    uint8_t max_retries = 3;
    bool require_acknowledgment = true;
    bool enable_compression = false;
    std::string correlation_id{};
};

/**
 * @brief 汎用リクエストモデル
 */
class GenericRequest {
public:
    GenericRequest() = default;
    explicit GenericRequest(proto::PacketType type);
    
    /**
     * @brief ヘッダーを設定
     * @param packet_id パケットID
     * @param type パケットタイプ
     * @param area_code エリアコード
     */
    void set_header(uint16_t packet_id, proto::PacketType type, uint32_t area_code = 0);
    
    /**
     * @brief フラグを設定
     * @param flags フラグ値
     */
    void set_flags(proto::Flags flags);
    
    /**
     * @brief 日付オフセットを設定
     * @param day 日付オフセット（0-7）
     */
    void set_day_offset(uint8_t day);
    
    /**
     * @brief タイムスタンプを設定（現在時刻を自動設定）
     */
    void set_current_timestamp();
    
    /**
     * @brief タイムスタンプを設定
     * @param timestamp UNIXタイムスタンプ
     */
    void set_timestamp(uint64_t timestamp);
    
    /**
     * @brief 拡張フィールドを追加
     * @param field 拡張フィールド
     */
    void add_extended_field(const proto::ExtendedField& field);
    
    /**
     * @brief リクエストオプションを設定
     * @param options オプション
     */
    void set_options(const RequestOptions& options);
    
    /**
     * @brief メタデータを追加
     * @param key キー
     * @param value 値
     */
    void add_metadata(const std::string& key, const std::string& value);
    
    /**
     * @brief チェックサムを自動計算して設定
     */
    void calculate_and_set_checksum();
    
    /**
     * @brief パケットをバイナリデータにエンコード
     * @return エンコードされたバイナリデータ
     */
    std::vector<uint8_t> encode() const;
    
    /**
     * @brief パケットを検証
     * @return 検証成功時true
     */
    bool validate() const;
    
    /**
     * @brief ヘッダーを取得
     * @return ヘッダー参照
     */
    const proto::Header& get_header() const { return packet_.header; }
    
    /**
     * @brief パケットを取得
     * @return パケット参照
     */
    const proto::Packet& get_packet() const { return packet_; }
    
    /**
     * @brief オプションを取得
     * @return オプション参照
     */
    const RequestOptions& get_options() const { return options_; }
    
    /**
     * @brief メタデータを取得
     * @return メタデータマップ参照
     */
    const std::unordered_map<std::string, std::string>& get_metadata() const { return metadata_; }
    
    /**
     * @brief リクエストがタイムアウトしているかチェック
     * @return タイムアウトしている場合true
     */
    bool is_timed_out() const;
    
    /**
     * @brief リクエスト作成からの経過時間を取得
     * @return 経過時間（ミリ秒）
     */
    std::chrono::milliseconds get_elapsed_time() const;

private:
    proto::Packet packet_{};
    RequestOptions options_{};
    std::unordered_map<std::string, std::string> metadata_{};
    std::chrono::steady_clock::time_point creation_time_{std::chrono::steady_clock::now()};
};

/**
 * @brief リクエスト共通処理ユーティリティ
 */
namespace request_utils {
    /**
     * @brief パケットIDを生成
     * @return 生成されたパケットID
     */
    uint16_t generate_packet_id();
    
    /**
     * @brief エリアコードを検証
     * @param area_code エリアコード
     * @return 有効な場合true
     */
    bool validate_area_code(uint32_t area_code);
    
    /**
     * @brief リクエストタイムアウトを計算
     * @param base_timeout ベースタイムアウト
     * @param retry_count リトライ回数
     * @return 調整されたタイムアウト
     */
    std::chrono::milliseconds calculate_timeout(std::chrono::milliseconds base_timeout, uint8_t retry_count);
    
    /**
     * @brief 相関IDを生成
     * @return 生成された相関ID
     */
    std::string generate_correlation_id();
    
    /**
     * @brief リクエストの重複をチェック
     * @param request1 リクエスト1
     * @param request2 リクエスト2
     * @return 重複している場合true
     */
    bool is_duplicate_request(const GenericRequest& request1, const GenericRequest& request2);
}

} // namespace wiplib::packet