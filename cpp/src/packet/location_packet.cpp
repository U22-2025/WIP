#include "wiplib/packet/location_packet.hpp"
#include "wiplib/packet/bit_utils.hpp"
#include "wiplib/packet/checksum.hpp"
#include "wiplib/packet/extended_field.hpp"
#include <cmath>
#include <algorithm>
#include <ctime>

namespace wiplib::packet {

LocationRequest LocationRequest::create(uint16_t packet_id, float latitude, float longitude) {
    LocationRequest request;
    
    // ヘッダー設定
    request.header.version = 1;
    request.header.packet_id = packet_id;
    request.header.type = proto::PacketType::CoordinateRequest;
    request.header.flags = proto::Flags{};
    request.header.day = 0;
    request.header.timestamp = std::time(nullptr);
    request.header.area_code = 0; // リクエスト時は未設定
    
    // 座標設定
    request.coordinate.latitude = latitude;
    request.coordinate.longitude = longitude;
    request.coordinate.precision = 6; // デフォルト精度
    
    return request;
}

std::optional<LocationRequest> LocationRequest::decode(std::span<const uint8_t> data) {
    if (data.size() < 24) { // 最小サイズチェック
        return std::nullopt;
    }
    
    LocationRequest request;
    
    try {
        // ヘッダーデコード（16バイト）
        request.header.version = extract_bits(data, 0, 4);
        request.header.packet_id = extract_bits(data, 4, 12);
        request.header.type = static_cast<proto::PacketType>(extract_bits(data, 16, 3));
        request.header.flags = proto::Flags::from_byte(extract_bits(data, 19, 8));
        request.header.day = extract_bits(data, 27, 3);
        
        uint64_t timestamp = extract_bits(data, 32, 64);
        request.header.timestamp = timestamp;
        
        request.header.area_code = extract_bits(data, 96, 20);
        request.header.checksum = extract_bits(data, 116, 12);
        
        // 座標データデコード（8バイト）
        uint32_t lat_bits = extract_bits(data, 128, 32);
        uint32_t lon_bits = extract_bits(data, 160, 32);
        
        // float変換（IEEE 754）
        request.coordinate.latitude = *reinterpret_cast<float*>(&lat_bits);
        request.coordinate.longitude = *reinterpret_cast<float*>(&lon_bits);
        request.coordinate.precision = 6;
        
        // チェックサム検証
        std::vector<uint8_t> checksum_data(data.begin(), data.begin() + 14);
        if (!verify_checksum12(checksum_data, request.header.checksum)) {
            return std::nullopt;
        }
        
        if (!request.validate()) {
            return std::nullopt;
        }
        
        return request;
        
    } catch (const std::exception&) {
        return std::nullopt;
    }
}

std::vector<uint8_t> LocationRequest::encode() const {
    std::vector<uint8_t> data(24, 0); // 16バイト（ヘッダー）+ 8バイト（座標）
    
    // ヘッダーエンコード
    set_bits(data, 0, 4, header.version);
    set_bits(data, 4, 12, header.packet_id);
    set_bits(data, 16, 3, static_cast<uint64_t>(header.type));
    set_bits(data, 19, 8, header.flags.to_byte());
    set_bits(data, 27, 3, header.day);
    set_bits(data, 32, 64, header.timestamp);
    set_bits(data, 96, 20, header.area_code);
    
    // 座標エンコード
    uint32_t lat_bits = *reinterpret_cast<const uint32_t*>(&coordinate.latitude);
    uint32_t lon_bits = *reinterpret_cast<const uint32_t*>(&coordinate.longitude);
    
    set_bits(data, 128, 32, lat_bits);
    set_bits(data, 160, 32, lon_bits);
    
    // チェックサム計算（ヘッダーの最初の14バイト）
    std::vector<uint8_t> checksum_data(data.begin(), data.begin() + 14);
    uint16_t checksum = calc_checksum12(checksum_data);
    set_bits(data, 116, 12, checksum);
    
    return data;
}

bool LocationRequest::validate() const {
    // パケットタイプチェック
    if (header.type != proto::PacketType::CoordinateRequest) {
        return false;
    }
    
    // 座標の有効性チェック
    if (!coordinate_utils::is_valid_coordinate(coordinate)) {
        return false;
    }
    
    return true;
}

LocationResponse LocationResponse::create(uint16_t request_packet_id, uint32_t area_code,
                                        const Coordinate& original_coord, uint8_t quality) {
    LocationResponse response;
    
    // ヘッダー設定
    response.header.version = 1;
    response.header.packet_id = request_packet_id; // レスポンスは同じパケットIDを使用
    response.header.type = proto::PacketType::CoordinateResponse;
    response.header.flags = proto::Flags{};
    response.header.day = 0;
    response.header.timestamp = std::time(nullptr);
    response.header.area_code = area_code;
    
    // レスポンスフィールド設定
    response.response_fields.weather_code = 0; // 座標解決では気象コードは設定しない
    response.response_fields.temperature = 0;
    response.response_fields.precipitation_prob = 0;
    
    // 座標レスポンス専用データ
    response.resolved_area_code = area_code;
    response.original_coordinate = original_coord;
    response.resolution_quality = quality;
    
    return response;
}

std::optional<LocationResponse> LocationResponse::decode(std::span<const uint8_t> data) {
    if (data.size() < 32) { // 最小サイズチェック
        return std::nullopt;
    }
    
    LocationResponse response;
    
    try {
        // ヘッダーデコード（16バイト）
        response.header.version = extract_bits(data, 0, 4);
        response.header.packet_id = extract_bits(data, 4, 12);
        response.header.type = static_cast<proto::PacketType>(extract_bits(data, 16, 3));
        response.header.flags = proto::Flags::from_byte(extract_bits(data, 19, 8));
        response.header.day = extract_bits(data, 27, 3);
        
        uint64_t timestamp = extract_bits(data, 32, 64);
        response.header.timestamp = timestamp;
        
        response.header.area_code = extract_bits(data, 96, 20);
        response.header.checksum = extract_bits(data, 116, 12);
        
        // レスポンスフィールドデコード（6バイト）
        response.response_fields.weather_code = extract_bits(data, 128, 16);
        response.response_fields.temperature = extract_bits(data, 144, 8);
        response.response_fields.precipitation_prob = extract_bits(data, 152, 8);
        
        // 座標レスポンス専用データデコード（13バイト）
        response.resolved_area_code = extract_bits(data, 160, 32);
        
        uint32_t lat_bits = extract_bits(data, 192, 32);
        uint32_t lon_bits = extract_bits(data, 224, 32);
        
        response.original_coordinate.latitude = *reinterpret_cast<float*>(&lat_bits);
        response.original_coordinate.longitude = *reinterpret_cast<float*>(&lon_bits);
        response.original_coordinate.precision = 6;
        
        response.resolution_quality = extract_bits(data, 256, 8);
        
        // チェックサム検証
        std::vector<uint8_t> checksum_data(data.begin(), data.begin() + 14);
        if (!verify_checksum12(checksum_data, response.header.checksum)) {
            return std::nullopt;
        }
        
        if (!response.validate()) {
            return std::nullopt;
        }
        
        return response;
        
    } catch (const std::exception&) {
        return std::nullopt;
    }
}

std::vector<uint8_t> LocationResponse::encode() const {
    std::vector<uint8_t> data(33, 0); // 16バイト（ヘッダー）+ 6バイト（レスポンス）+ 13バイト（座標レスポンス）
    
    // ヘッダーエンコード
    set_bits(data, 0, 4, header.version);
    set_bits(data, 4, 12, header.packet_id);
    set_bits(data, 16, 3, static_cast<uint64_t>(header.type));
    set_bits(data, 19, 8, header.flags.to_byte());
    set_bits(data, 27, 3, header.day);
    set_bits(data, 32, 64, header.timestamp);
    set_bits(data, 96, 20, header.area_code);
    
    // レスポンスフィールドエンコード
    set_bits(data, 128, 16, response_fields.weather_code);
    set_bits(data, 144, 8, response_fields.temperature);
    set_bits(data, 152, 8, response_fields.precipitation_prob);
    
    // 座標レスポンス専用データエンコード
    set_bits(data, 160, 32, resolved_area_code);
    
    uint32_t lat_bits = *reinterpret_cast<const uint32_t*>(&original_coordinate.latitude);
    uint32_t lon_bits = *reinterpret_cast<const uint32_t*>(&original_coordinate.longitude);
    
    set_bits(data, 192, 32, lat_bits);
    set_bits(data, 224, 32, lon_bits);
    set_bits(data, 256, 8, resolution_quality);
    
    // チェックサム計算
    std::vector<uint8_t> checksum_data(data.begin(), data.begin() + 14);
    uint16_t checksum = calc_checksum12(checksum_data);
    set_bits(data, 116, 12, checksum);
    
    return data;
}

bool LocationResponse::validate() const {
    // パケットタイプチェック
    if (header.type != proto::PacketType::CoordinateResponse) {
        return false;
    }
    
    // 座標の有効性チェック
    if (!coordinate_utils::is_valid_coordinate(original_coordinate)) {
        return false;
    }
    
    // エリアコードの一貫性チェック
    if (header.area_code != resolved_area_code) {
        return false;
    }
    
    return true;
}

// coordinate_utils名前空間の実装
namespace coordinate_utils {
    bool is_valid_coordinate(const Coordinate& coord) {
        // 緯度範囲チェック（-90度〜+90度）
        if (coord.latitude < -90.0f || coord.latitude > 90.0f) {
            return false;
        }
        
        // 経度範囲チェック（-180度〜+180度）
        if (coord.longitude < -180.0f || coord.longitude > 180.0f) {
            return false;
        }
        
        // 精度チェック（0〜10桁）
        if (coord.precision > 10) {
            return false;
        }
        
        // NaN/Infinityチェック
        if (std::isnan(coord.latitude) || std::isnan(coord.longitude) ||
            std::isinf(coord.latitude) || std::isinf(coord.longitude)) {
            return false;
        }
        
        return true;
    }
    
    Coordinate round_to_precision(const Coordinate& coord, uint8_t precision) {
        Coordinate rounded = coord;
        
        if (precision > 10) precision = 10; // 最大精度制限
        
        double multiplier = std::pow(10.0, precision);
        
        rounded.latitude = std::round(coord.latitude * multiplier) / multiplier;
        rounded.longitude = std::round(coord.longitude * multiplier) / multiplier;
        rounded.precision = precision;
        
        return rounded;
    }
    
    bool is_within_geographic_bounds(const Coordinate& coord) {
        // 基本的な地理的境界チェック
        return is_valid_coordinate(coord);
    }
}

} // namespace wiplib::packet