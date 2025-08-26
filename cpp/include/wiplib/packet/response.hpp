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
 * @brief レスポンスステータス
 */
enum class ResponseStatus : uint8_t {
    Success = 0,
    PartialSuccess = 1,
    Warning = 2,
    Error = 3,
    Timeout = 4,
    Retry = 5
};

/**
 * @brief レスポンス処理情報
 */
struct ResponseInfo {
    ResponseStatus status = ResponseStatus::Success;
    uint64_t processing_time_us = 0;  // 処理時間（マイクロ秒）
    uint16_t server_load = 0;         // サーバー負荷（0-65535）
    std::string server_version{};     // サーバーバージョン
    std::string processing_node{};    // 処理ノード識別子
};

/**
 * @brief データ品質情報
 */
struct DataQuality {
    uint8_t accuracy = 255;           // 精度（0-255）
    uint8_t freshness = 255;          // 新鮮度（0-255）
    uint8_t completeness = 255;       // 完全性（0-255）
    uint64_t source_timestamp = 0;    // ソースデータタイムスタンプ
    std::string data_source{};        // データソース識別子
};

/**
 * @brief 汎用レスポンスモデル
 */
class GenericResponse {
public:
    GenericResponse() = default;
    explicit GenericResponse(uint16_t request_packet_id);
    
    /**
     * @brief リクエストパケットIDを設定
     * @param request_packet_id 対応するリクエストのパケットID
     */
    void set_request_packet_id(uint16_t request_packet_id);
    
    /**
     * @brief ヘッダーを設定
     * @param type パケットタイプ
     * @param area_code エリアコード
     */
    void set_header(proto::PacketType type, uint32_t area_code = 0);
    
    /**
     * @brief レスポンスフィールドを設定
     * @param fields レスポンスフィールド
     */
    void set_response_fields(const proto::ResponseFields& fields);
    
    /**
     * @brief フラグを設定
     * @param flags フラグ値
     */
    void set_flags(proto::Flags flags);
    
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
     * @brief レスポンス情報を設定
     * @param info レスポンス情報
     */
    void set_response_info(const ResponseInfo& info);
    
    /**
     * @brief データ品質情報を設定
     * @param quality データ品質情報
     */
    void set_data_quality(const DataQuality& quality);
    
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
     * @brief バイナリデータからレスポンスをデコード
     * @param data バイナリデータ
     * @return デコードされたレスポンス
     */
    static std::optional<GenericResponse> decode(std::span<const uint8_t> data);
    
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
     * @brief レスポンスフィールドを取得
     * @return レスポンスフィールド参照
     */
    const std::optional<proto::ResponseFields>& get_response_fields() const { return packet_.response_fields; }
    
    /**
     * @brief パケットを取得
     * @return パケット参照
     */
    const proto::Packet& get_packet() const { return packet_; }
    
    /**
     * @brief レスポンス情報を取得
     * @return レスポンス情報参照
     */
    const ResponseInfo& get_response_info() const { return response_info_; }
    
    /**
     * @brief データ品質情報を取得
     * @return データ品質情報参照
     */
    const DataQuality& get_data_quality() const { return data_quality_; }
    
    /**
     * @brief メタデータを取得
     * @return メタデータマップ参照
     */
    const std::unordered_map<std::string, std::string>& get_metadata() const { return metadata_; }
    
    /**
     * @brief レスポンスが成功かどうか判定
     * @return 成功の場合true
     */
    bool is_success() const;
    
    /**
     * @brief レスポンスにエラーが含まれているか判定
     * @return エラーがある場合true
     */
    bool has_error() const;
    
    /**
     * @brief レスポンス作成からの経過時間を取得
     * @return 経過時間（ミリ秒）
     */
    std::chrono::milliseconds get_age() const;

private:
    proto::Packet packet_{};
    ResponseInfo response_info_{};
    DataQuality data_quality_{};
    std::unordered_map<std::string, std::string> metadata_{};
    std::chrono::steady_clock::time_point creation_time_{std::chrono::steady_clock::now()};
};

/**
 * @brief レスポンス共通処理ユーティリティ
 */
namespace response_utils {
    /**
     * @brief レスポンスステータスを文字列に変換
     * @param status レスポンスステータス
     * @return ステータス文字列
     */
    std::string status_to_string(ResponseStatus status);
    
    /**
     * @brief データ品質スコアを計算
     * @param quality データ品質情報
     * @return 品質スコア（0.0-1.0）
     */
    double calculate_quality_score(const DataQuality& quality);
    
    /**
     * @brief レスポンス時間からパフォーマンス評価を取得
     * @param processing_time_us 処理時間（マイクロ秒）
     * @return パフォーマンス評価（0=悪い, 100=優秀）
     */
    uint8_t evaluate_performance(uint64_t processing_time_us);
    
    /**
     * @brief サーバー負荷状態を文字列に変換
     * @param load サーバー負荷値
     * @return 負荷状態文字列
     */
    std::string load_to_string(uint16_t load);
    
    /**
     * @brief レスポンスがキャッシュ可能かどうか判定
     * @param response レスポンス
     * @return キャッシュ可能な場合true
     */
    bool is_cacheable(const GenericResponse& response);
    
    /**
     * @brief レスポンスのTTL（Time To Live）を計算
     * @param response レスポンス
     * @return TTL（秒）
     */
    std::chrono::seconds calculate_ttl(const GenericResponse& response);
}

} // namespace wiplib::packet