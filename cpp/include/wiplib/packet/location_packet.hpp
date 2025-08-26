#pragma once

#include <cstdint>
#include <array>
#include <optional>
#include <span>
#include "wiplib/packet/packet.hpp"

namespace wiplib::packet {

/**
 * @brief 座標データ構造体
 */
struct Coordinate {
    float latitude = 0.0f;   // 緯度
    float longitude = 0.0f;  // 経度
    uint8_t precision = 6;   // 精度（小数点以下桁数）
};

/**
 * @brief 座標→エリアコード変換要求パケット
 */
struct LocationRequest {
    proto::Header header{};
    Coordinate coordinate{};
    
    /**
     * @brief パケットを作成
     * @param packet_id パケットID
     * @param latitude 緯度
     * @param longitude 経度
     * @return LocationRequestパケット
     */
    static LocationRequest create(uint16_t packet_id, float latitude, float longitude);
    
    /**
     * @brief バイナリデータからパケットをデコード
     * @param data バイナリデータ
     * @return デコードされたパケット
     */
    static std::optional<LocationRequest> decode(std::span<const uint8_t> data);
    
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
};

/**
 * @brief 座標解決結果応答パケット  
 */
struct LocationResponse {
    proto::Header header{};
    proto::ResponseFields response_fields{};
    uint32_t resolved_area_code = 0;
    Coordinate original_coordinate{};
    uint8_t resolution_quality = 0; // 解決品質（0-255）
    
    /**
     * @brief パケットを作成
     * @param request_packet_id 対応するリクエストのパケットID
     * @param area_code 解決されたエリアコード
     * @param original_coord 元の座標
     * @param quality 解決品質
     * @return LocationResponseパケット
     */
    static LocationResponse create(uint16_t request_packet_id, uint32_t area_code, 
                                 const Coordinate& original_coord, uint8_t quality = 255);
    
    /**
     * @brief バイナリデータからパケットをデコード
     * @param data バイナリデータ
     * @return デコードされたパケット
     */
    static std::optional<LocationResponse> decode(std::span<const uint8_t> data);
    
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
};

/**
 * @brief 座標データの精度管理ユーティリティ
 */
namespace coordinate_utils {
    /**
     * @brief 座標の精度を検証
     * @param coord 座標データ
     * @return 有効な座標の場合true
     */
    bool is_valid_coordinate(const Coordinate& coord);
    
    /**
     * @brief 座標を指定精度に丸める
     * @param coord 座標データ
     * @param precision 精度（小数点以下桁数）
     * @return 丸められた座標
     */
    Coordinate round_to_precision(const Coordinate& coord, uint8_t precision);
    
    /**
     * @brief 座標の地理的境界をチェック
     * @param coord 座標データ
     * @return 有効な地理的範囲内の場合true
     */
    bool is_within_geographic_bounds(const Coordinate& coord);
}

} // namespace wiplib::packet
