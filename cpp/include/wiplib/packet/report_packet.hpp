#pragma once

#include <cstdint>
#include <vector>
#include <string>
#include <optional>
#include <span>
#include "wiplib/packet/packet.hpp"

namespace wiplib::packet {

/**
 * @brief センサーデータ構造体
 */
struct SensorData {
    uint32_t area_code = 0;
    uint16_t weather_code = 0;
    float temperature = 0.0f;
    uint8_t precipitation_prob = 0;
    std::vector<std::string> alerts{};
    std::vector<std::string> disasters{};
    uint64_t measurement_time = 0; // UNIX timestamp
    uint8_t data_quality = 255;    // データ品質（0-255）
};

/**
 * @brief データ送信要求パケット
 */
struct ReportRequest {
    proto::Header header{};
    SensorData sensor_data{};
    std::vector<uint8_t> binary_data{}; // バイナリデータ（オプション）
    uint8_t compression_type = 0;       // 圧縮タイプ（0=無圧縮）
    uint16_t data_hash = 0;            // データハッシュ（整合性チェック用）
    
    /**
     * @brief パケットを作成
     * @param packet_id パケットID
     * @param sensor_data センサーデータ
     * @param binary_data バイナリデータ（オプション）
     * @return ReportRequestパケット
     */
    static ReportRequest create(uint16_t packet_id, const SensorData& sensor_data,
                               const std::vector<uint8_t>& binary_data = {});
    
    /**
     * @brief バイナリデータからパケットをデコード
     * @param data バイナリデータ
     * @return デコードされたパケット
     */
    static std::optional<ReportRequest> decode(std::span<const uint8_t> data);
    
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
     * @brief データハッシュを計算
     * @return 計算されたハッシュ値
     */
    uint16_t calculate_data_hash() const;
};

/**
 * @brief 送信結果応答パケット
 */
struct ReportResponse {
    proto::Header header{};
    proto::ResponseFields response_fields{};
    uint8_t status_code = 0;           // ステータスコード（0=成功）
    uint16_t processed_data_count = 0; // 処理されたデータ数
    uint64_t server_timestamp = 0;     // サーバータイムスタンプ
    std::string message{};             // メッセージ（オプション）
    
    /**
     * @brief パケットを作成
     * @param request_packet_id 対応するリクエストのパケットID
     * @param status_code ステータスコード
     * @param processed_count 処理されたデータ数
     * @param message メッセージ（オプション）
     * @return ReportResponseパケット
     */
    static ReportResponse create(uint16_t request_packet_id, uint8_t status_code,
                               uint16_t processed_count, const std::string& message = "");
    
    /**
     * @brief バイナリデータからパケットをデコード
     * @param data バイナリデータ
     * @return デコードされたパケット
     */
    static std::optional<ReportResponse> decode(std::span<const uint8_t> data);
    
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
     * @brief ステータスコードから成功/失敗を判定
     * @return 成功の場合true
     */
    bool is_success() const;
};

/**
 * @brief バイナリデータ処理ユーティリティ
 */
namespace binary_utils {
    /**
     * @brief バイナリデータを圧縮
     * @param data 元データ
     * @param compression_type 圧縮タイプ
     * @return 圧縮されたデータ
     */
    std::vector<uint8_t> compress_data(const std::vector<uint8_t>& data, uint8_t compression_type);
    
    /**
     * @brief バイナリデータを展開
     * @param compressed_data 圧縮データ
     * @param compression_type 圧縮タイプ
     * @return 展開されたデータ
     */
    std::vector<uint8_t> decompress_data(const std::vector<uint8_t>& compressed_data, uint8_t compression_type);
    
    /**
     * @brief データの整合性をチェック
     * @param data データ
     * @param expected_hash 期待されるハッシュ値
     * @return 整合性が確認できた場合true
     */
    bool verify_data_integrity(const std::vector<uint8_t>& data, uint16_t expected_hash);
    
    /**
     * @brief データハッシュを計算
     * @param data データ
     * @return ハッシュ値
     */
    uint16_t calculate_hash(const std::vector<uint8_t>& data);
}

} // namespace wiplib::packet