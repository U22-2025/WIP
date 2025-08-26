#include "wiplib/packet/report_packet.hpp"
#include "wiplib/packet/bit_utils.hpp"
#include "wiplib/packet/checksum.hpp"
#include "wiplib/packet/extended_field.hpp"
#include <cstring>
#include <algorithm>
#include <numeric>

namespace wiplib::packet {

ReportRequest ReportRequest::create(uint16_t packet_id, const SensorData& sensor_data,
                                   const std::vector<uint8_t>& binary_data) {
    ReportRequest request;
    
    // ヘッダー設定
    request.header.version = 1;
    request.header.packet_id = packet_id;
    request.header.type = proto::PacketType::DataReport;
    request.header.flags = binary_data.empty() ? 0 : 1; // バイナリデータ有無をフラグで表現
    request.header.day = 0;
    request.header.timestamp = sensor_data.measurement_time ? sensor_data.measurement_time : std::time(nullptr);
    request.header.area_code = sensor_data.area_code;
    
    // センサーデータ設定
    request.sensor_data = sensor_data;
    request.binary_data = binary_data;
    request.compression_type = 0; // デフォルトは無圧縮
    
    // データハッシュ計算
    request.data_hash = request.calculate_data_hash();
    
    return request;
}

std::optional<ReportRequest> ReportRequest::decode(std::span<const uint8_t> data) {
    if (data.size() < 32) { // 最小サイズチェック
        return std::nullopt;
    }
    
    ReportRequest request;
    
    try {
        // ヘッダーデコード（16バイト）
        request.header.version = extract_bits(data, 0, 4);
        request.header.packet_id = extract_bits(data, 4, 12);
        request.header.type = static_cast<proto::PacketType>(extract_bits(data, 16, 3));
        request.header.flags = extract_bits(data, 19, 8);
        request.header.day = extract_bits(data, 27, 3);
        
        uint64_t timestamp = extract_bits(data, 32, 64);
        request.header.timestamp = timestamp;
        
        request.header.area_code = extract_bits(data, 96, 20);
        request.header.checksum = extract_bits(data, 116, 12);
        
        // センサーデータデコード（16バイト）
        request.sensor_data.area_code = request.header.area_code;
        request.sensor_data.weather_code = extract_bits(data, 128, 16);
        
        // 温度デコード（オフセット+100のsigned値）
        uint8_t temp_raw = extract_bits(data, 144, 8);
        request.sensor_data.temperature = static_cast<int8_t>(temp_raw) - 100.0f;
        
        request.sensor_data.precipitation_prob = extract_bits(data, 152, 8);
        request.sensor_data.measurement_time = extract_bits(data, 160, 64);
        request.sensor_data.data_quality = extract_bits(data, 224, 8);
        
        // データハッシュと圧縮情報
        request.compression_type = extract_bits(data, 232, 8);
        request.data_hash = extract_bits(data, 240, 16);
        
        // バイナリデータサイズチェック
        if (data.size() > 32) {
            uint16_t binary_size = data.size() - 32;
            request.binary_data.resize(binary_size);
            std::memcpy(request.binary_data.data(), data.data() + 32, binary_size);
        }
        
        // チェックサム検証
        std::vector<uint8_t> checksum_data(data.begin(), data.begin() + 14);
        if (!verify_checksum12(checksum_data, request.header.checksum)) {
            return std::nullopt;
        }
        
        // データハッシュ検証
        if (request.data_hash != request.calculate_data_hash()) {
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

std::vector<uint8_t> ReportRequest::encode() const {
    std::vector<uint8_t> data(32 + binary_data.size(), 0);
    
    // ヘッダーエンコード
    set_bits(data, 0, 4, header.version);
    set_bits(data, 4, 12, header.packet_id);
    set_bits(data, 16, 3, static_cast<uint64_t>(header.type));
    set_bits(data, 19, 8, header.flags);
    set_bits(data, 27, 3, header.day);
    set_bits(data, 32, 64, header.timestamp);
    set_bits(data, 96, 20, header.area_code);
    
    // センサーデータエンコード
    set_bits(data, 128, 16, sensor_data.weather_code);
    
    // 温度エンコード（+100オフセット）
    uint8_t temp_encoded = static_cast<uint8_t>(sensor_data.temperature + 100.0f);
    set_bits(data, 144, 8, temp_encoded);
    
    set_bits(data, 152, 8, sensor_data.precipitation_prob);
    set_bits(data, 160, 64, sensor_data.measurement_time);
    set_bits(data, 224, 8, sensor_data.data_quality);
    
    // データハッシュと圧縮情報
    set_bits(data, 232, 8, compression_type);
    set_bits(data, 240, 16, data_hash);
    
    // バイナリデータ追加
    if (!binary_data.empty()) {
        std::memcpy(data.data() + 32, binary_data.data(), binary_data.size());
    }
    
    // チェックサム計算
    std::vector<uint8_t> checksum_data(data.begin(), data.begin() + 14);
    uint16_t checksum = calc_checksum12(checksum_data);
    set_bits(data, 116, 12, checksum);
    
    return data;
}

bool ReportRequest::validate() const {
    // パケットタイプチェック
    if (header.type != proto::PacketType::DataReport) {
        return false;
    }
    
    // エリアコードの一貫性チェック
    if (header.area_code != sensor_data.area_code) {
        return false;
    }
    
    // 降水確率範囲チェック（0-100%）
    if (sensor_data.precipitation_prob > 100) {
        return false;
    }
    
    // 温度範囲チェック（-150〜+150度）
    if (sensor_data.temperature < -150.0f || sensor_data.temperature > 150.0f) {
        return false;
    }
    
    // データ品質範囲チェック（0-255）
    // （uint8_tなので自動的に範囲内）
    
    // タイムスタンプ妥当性チェック（過去100年以内）
    uint64_t current_time = std::time(nullptr);
    uint64_t min_time = current_time - (100 * 365 * 24 * 3600); // 100年前
    uint64_t max_time = current_time + (24 * 3600); // 1日先まで許可
    
    if (sensor_data.measurement_time < min_time || sensor_data.measurement_time > max_time) {
        return false;
    }
    
    return true;
}

uint16_t ReportRequest::calculate_data_hash() const {
    std::vector<uint8_t> hash_data;
    
    // センサーデータをハッシュ計算に含める
    hash_data.resize(sizeof(SensorData));
    
    // 基本的なデータフィールドを連結
    auto append_value = [&hash_data](const auto& value) {
        const uint8_t* bytes = reinterpret_cast<const uint8_t*>(&value);
        hash_data.insert(hash_data.end(), bytes, bytes + sizeof(value));
    };
    
    append_value(sensor_data.area_code);
    append_value(sensor_data.weather_code);
    append_value(sensor_data.temperature);
    append_value(sensor_data.precipitation_prob);
    append_value(sensor_data.measurement_time);
    append_value(sensor_data.data_quality);
    
    // バイナリデータも含める
    hash_data.insert(hash_data.end(), binary_data.begin(), binary_data.end());
    
    return binary_utils::calculate_hash(hash_data);
}

ReportResponse ReportResponse::create(uint16_t request_packet_id, uint8_t status_code,
                                    uint16_t processed_count, const std::string& message) {
    ReportResponse response;
    
    // ヘッダー設定
    response.header.version = 1;
    response.header.packet_id = request_packet_id;
    response.header.type = proto::PacketType::DataResponse;
    response.header.flags = message.empty() ? 0 : 1; // メッセージ有無をフラグで表現
    response.header.day = 0;
    response.header.timestamp = std::time(nullptr);
    response.header.area_code = 0; // レスポンスではエリアコードは未使用
    
    // レスポンスフィールド設定（ダミー値）
    response.response_fields.weather_code = 0;
    response.response_fields.temperature = 0;
    response.response_fields.precipitation_prob = 0;
    
    // レポートレスポンス専用データ
    response.status_code = status_code;
    response.processed_data_count = processed_count;
    response.server_timestamp = std::time(nullptr);
    response.message = message;
    
    return response;
}

std::optional<ReportResponse> ReportResponse::decode(std::span<const uint8_t> data) {
    if (data.size() < 32) { // 最小サイズチェック
        return std::nullopt;
    }
    
    ReportResponse response;
    
    try {
        // ヘッダーデコード（16バイト）
        response.header.version = extract_bits(data, 0, 4);
        response.header.packet_id = extract_bits(data, 4, 12);
        response.header.type = static_cast<proto::PacketType>(extract_bits(data, 16, 3));
        response.header.flags = extract_bits(data, 19, 8);
        response.header.day = extract_bits(data, 27, 3);
        
        uint64_t timestamp = extract_bits(data, 32, 64);
        response.header.timestamp = timestamp;
        
        response.header.area_code = extract_bits(data, 96, 20);
        response.header.checksum = extract_bits(data, 116, 12);
        
        // レスポンスフィールドデコード（6バイト）
        response.response_fields.weather_code = extract_bits(data, 128, 16);
        response.response_fields.temperature = extract_bits(data, 144, 8);
        response.response_fields.precipitation_prob = extract_bits(data, 152, 8);
        
        // レポートレスポンス専用データ（11バイト）
        response.status_code = extract_bits(data, 160, 8);
        response.processed_data_count = extract_bits(data, 168, 16);
        response.server_timestamp = extract_bits(data, 184, 64);
        
        // メッセージデコード（残りのデータ）
        if (data.size() > 32) {
            uint16_t message_size = data.size() - 32;
            response.message.resize(message_size);
            std::memcpy(response.message.data(), data.data() + 32, message_size);
        }
        
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

std::vector<uint8_t> ReportResponse::encode() const {
    std::vector<uint8_t> data(32 + message.size(), 0);
    
    // ヘッダーエンコード
    set_bits(data, 0, 4, header.version);
    set_bits(data, 4, 12, header.packet_id);
    set_bits(data, 16, 3, static_cast<uint64_t>(header.type));
    set_bits(data, 19, 8, header.flags);
    set_bits(data, 27, 3, header.day);
    set_bits(data, 32, 64, header.timestamp);
    set_bits(data, 96, 20, header.area_code);
    
    // レスポンスフィールドエンコード
    set_bits(data, 128, 16, response_fields.weather_code);
    set_bits(data, 144, 8, response_fields.temperature);
    set_bits(data, 152, 8, response_fields.precipitation_prob);
    
    // レポートレスポンス専用データエンコード
    set_bits(data, 160, 8, status_code);
    set_bits(data, 168, 16, processed_data_count);
    set_bits(data, 184, 64, server_timestamp);
    
    // メッセージ追加
    if (!message.empty()) {
        std::memcpy(data.data() + 32, message.data(), message.size());
    }
    
    // チェックサム計算
    std::vector<uint8_t> checksum_data(data.begin(), data.begin() + 14);
    uint16_t checksum = calc_checksum12(checksum_data);
    set_bits(data, 116, 12, checksum);
    
    return data;
}

bool ReportResponse::validate() const {
    // パケットタイプチェック
    if (header.type != proto::PacketType::DataResponse) {
        return false;
    }
    
    // ステータスコード範囲チェック（0-255、255は未定義エラー）
    // （uint8_tなので自動的に範囲内）
    
    // 処理データ数の妥当性チェック
    // （特に制限なし、uint16_tの範囲内）
    
    // サーバータイムスタンプの妥当性チェック
    uint64_t current_time = std::time(nullptr);
    uint64_t min_time = current_time - (24 * 3600); // 1日前
    uint64_t max_time = current_time + (3600); // 1時間先まで許可
    
    if (server_timestamp < min_time || server_timestamp > max_time) {
        return false;
    }
    
    return true;
}

bool ReportResponse::is_success() const {
    // ステータスコード0が成功
    return status_code == 0;
}

// binary_utils名前空間の実装
namespace binary_utils {
    std::vector<uint8_t> compress_data(const std::vector<uint8_t>& data, uint8_t compression_type) {
        // 現在は圧縮未実装、そのまま返す
        if (compression_type == 0) {
            return data; // 無圧縮
        }
        
        // TODO: 実際の圧縮アルゴリズム実装（zlib, lz4など）
        return data;
    }
    
    std::vector<uint8_t> decompress_data(const std::vector<uint8_t>& compressed_data, uint8_t compression_type) {
        // 現在は展開未実装、そのまま返す
        if (compression_type == 0) {
            return compressed_data; // 無圧縮
        }
        
        // TODO: 実際の展開アルゴリズム実装
        return compressed_data;
    }
    
    bool verify_data_integrity(const std::vector<uint8_t>& data, uint16_t expected_hash) {
        uint16_t calculated_hash = calculate_hash(data);
        return calculated_hash == expected_hash;
    }
    
    uint16_t calculate_hash(const std::vector<uint8_t>& data) {
        // 簡易CRC16計算
        uint16_t crc = 0xFFFF;
        
        for (uint8_t byte : data) {
            crc ^= byte;
            for (int i = 0; i < 8; i++) {
                if (crc & 1) {
                    crc = (crc >> 1) ^ 0xA001;
                } else {
                    crc >>= 1;
                }
            }
        }
        
        return crc;
    }
}

} // namespace wiplib::packet