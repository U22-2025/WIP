#include "wiplib/packet/error_response.hpp"
#include "wiplib/packet/bit_utils.hpp"
#include "wiplib/packet/checksum.hpp"
#include <sstream>
#include <cstring>
#include <algorithm>

namespace wiplib::packet {

ErrorResponse ErrorResponse::create(uint16_t request_packet_id, ErrorCode error_code,
                                  const std::string& message, uint8_t severity) {
    ErrorResponse response;
    
    // ヘッダー設定
    response.header.version = 1;
    response.header.packet_id = request_packet_id;
    response.header.type = proto::PacketType::ErrorResponse;
    response.header.flags = message.empty() ? 0 : 1; // メッセージ有無をフラグで表現
    response.header.day = 0;
    response.header.timestamp = std::time(nullptr);
    response.header.area_code = 0; // エラーレスポンスではエリアコードは未使用
    
    // エラー情報設定
    response.error_code = error_code;
    response.severity = severity;
    response.sub_error_code = 0;
    response.error_message = message.empty() ? error_utils::get_default_message(error_code) : message;
    response.debug_info = "";
    response.server_timestamp = std::time(nullptr);
    
    return response;
}

ErrorResponse ErrorResponse::create_detailed(uint16_t request_packet_id, ErrorCode error_code,
                                           uint16_t sub_error_code, const std::string& message,
                                           const std::string& debug_info, uint8_t severity) {
    ErrorResponse response = create(request_packet_id, error_code, message, severity);
    
    response.sub_error_code = sub_error_code;
    response.debug_info = debug_info;
    
    return response;
}

std::optional<ErrorResponse> ErrorResponse::decode(std::span<const uint8_t> data) {
    if (data.size() < 32) { // 最小サイズチェック
        return std::nullopt;
    }
    
    ErrorResponse response;
    
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
        
        // エラー情報デコード（16バイト）
        response.error_code = static_cast<ErrorCode>(extract_bits(data, 128, 16));
        response.severity = extract_bits(data, 144, 8);
        response.sub_error_code = extract_bits(data, 152, 16);
        response.server_timestamp = extract_bits(data, 168, 64);
        
        // メッセージとデバッグ情報のデコード
        if (data.size() > 32) {
            size_t remaining_size = data.size() - 32;
            
            // メッセージ長を読み取り（2バイト）
            if (remaining_size >= 2) {
                uint16_t message_len = extract_bits(data, 256, 16);
                
                if (remaining_size >= 2 + message_len) {
                    // メッセージ読み取り
                    if (message_len > 0) {
                        response.error_message.resize(message_len);
                        std::memcpy(response.error_message.data(), data.data() + 34, message_len);
                    }
                    
                    // デバッグ情報長を読み取り（残りのデータ）
                    size_t debug_start = 34 + message_len;
                    if (debug_start + 2 <= data.size()) {
                        uint16_t debug_len = *reinterpret_cast<const uint16_t*>(data.data() + debug_start);
                        
                        if (debug_start + 2 + debug_len <= data.size() && debug_len > 0) {
                            response.debug_info.resize(debug_len);
                            std::memcpy(response.debug_info.data(), data.data() + debug_start + 2, debug_len);
                        }
                    }
                }
            }
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

std::vector<uint8_t> ErrorResponse::encode() const {
    // 可変長データのサイズを計算
    uint16_t message_len = error_message.size();
    uint16_t debug_len = debug_info.size();
    
    size_t total_size = 32 + // 基本サイズ
                       2 + message_len + // メッセージ長 + メッセージ
                       2 + debug_len;    // デバッグ情報長 + デバッグ情報
    
    std::vector<uint8_t> data(total_size, 0);
    
    // ヘッダーエンコード
    set_bits(data, 0, 4, header.version);
    set_bits(data, 4, 12, header.packet_id);
    set_bits(data, 16, 3, static_cast<uint64_t>(header.type));
    set_bits(data, 19, 8, header.flags);
    set_bits(data, 27, 3, header.day);
    set_bits(data, 32, 64, header.timestamp);
    set_bits(data, 96, 20, header.area_code);
    
    // エラー情報エンコード
    set_bits(data, 128, 16, static_cast<uint16_t>(error_code));
    set_bits(data, 144, 8, severity);
    set_bits(data, 152, 16, sub_error_code);
    set_bits(data, 168, 64, server_timestamp);
    
    // メッセージエンコード
    set_bits(data, 256, 16, message_len);
    if (message_len > 0) {
        std::memcpy(data.data() + 34, error_message.data(), message_len);
    }
    
    // デバッグ情報エンコード
    size_t debug_offset = 34 + message_len;
    *reinterpret_cast<uint16_t*>(data.data() + debug_offset) = debug_len;
    if (debug_len > 0) {
        std::memcpy(data.data() + debug_offset + 2, debug_info.data(), debug_len);
    }
    
    // チェックサム計算
    std::vector<uint8_t> checksum_data(data.begin(), data.begin() + 14);
    uint16_t checksum = calc_checksum12(checksum_data);
    set_bits(data, 116, 12, checksum);
    
    return data;
}

bool ErrorResponse::validate() const {
    // パケットタイプチェック
    if (header.type != proto::PacketType::ErrorResponse) {
        return false;
    }
    
    // 重要度範囲チェック（0-3）
    if (severity > 3) {
        return false;
    }
    
    // エラーコード範囲チェック
    uint16_t error_value = static_cast<uint16_t>(error_code);
    if (error_value > 999) {
        return false;
    }
    
    // サーバータイムスタンプの妥当性チェック
    uint64_t current_time = std::time(nullptr);
    uint64_t min_time = current_time - (24 * 3600); // 1日前
    uint64_t max_time = current_time + (3600); // 1時間先まで許可
    
    if (server_timestamp < min_time || server_timestamp > max_time) {
        return false;
    }
    
    // メッセージサイズチェック
    if (error_message.size() > 1024) { // 最大1KB
        return false;
    }
    
    // デバッグ情報サイズチェック
    if (debug_info.size() > 2048) { // 最大2KB
        return false;
    }
    
    return true;
}

bool ErrorResponse::is_fatal() const {
    return severity >= 3 || 
           error_code == ErrorCode::InternalServerError ||
           error_code == ErrorCode::DatabaseError ||
           error_code == ErrorCode::UnsupportedVersion;
}

std::string ErrorResponse::to_string() const {
    std::ostringstream oss;
    
    oss << "[" << error_utils::error_code_to_string(error_code) << "]";
    
    if (sub_error_code != 0) {
        oss << "(" << sub_error_code << ")";
    }
    
    oss << " - " << error_message;
    
    if (severity >= 2) {
        oss << " [SEVERITY:" << static_cast<int>(severity) << "]";
    }
    
    if (!debug_info.empty()) {
        oss << " (Debug: " << debug_info << ")";
    }
    
    return oss.str();
}

// error_utils名前空間の実装
namespace error_utils {
    std::string error_code_to_string(ErrorCode code) {
        switch (code) {
            case ErrorCode::NoError: return "NO_ERROR";
            
            // 基本的なエラー (1-99)
            case ErrorCode::InvalidRequest: return "INVALID_REQUEST";
            case ErrorCode::InvalidPacketFormat: return "INVALID_PACKET_FORMAT";
            case ErrorCode::ChecksumMismatch: return "CHECKSUM_MISMATCH";
            case ErrorCode::UnsupportedVersion: return "UNSUPPORTED_VERSION";
            case ErrorCode::InvalidFieldValue: return "INVALID_FIELD_VALUE";
            
            // 認証・権限エラー (100-199)
            case ErrorCode::AuthenticationRequired: return "AUTHENTICATION_REQUIRED";
            case ErrorCode::AuthenticationFailed: return "AUTHENTICATION_FAILED";
            case ErrorCode::InsufficientPermissions: return "INSUFFICIENT_PERMISSIONS";
            case ErrorCode::TokenExpired: return "TOKEN_EXPIRED";
            
            // データエラー (200-299)
            case ErrorCode::InvalidAreaCode: return "INVALID_AREA_CODE";
            case ErrorCode::InvalidCoordinate: return "INVALID_COORDINATE";
            case ErrorCode::InvalidWeatherCode: return "INVALID_WEATHER_CODE";
            case ErrorCode::InvalidTemperature: return "INVALID_TEMPERATURE";
            case ErrorCode::InvalidPrecipitationProb: return "INVALID_PRECIPITATION_PROB";
            case ErrorCode::DataNotFound: return "DATA_NOT_FOUND";
            case ErrorCode::DataExpired: return "DATA_EXPIRED";
            
            // サーバーエラー (300-399)
            case ErrorCode::InternalServerError: return "INTERNAL_SERVER_ERROR";
            case ErrorCode::ServiceUnavailable: return "SERVICE_UNAVAILABLE";
            case ErrorCode::DatabaseError: return "DATABASE_ERROR";
            case ErrorCode::NetworkError: return "NETWORK_ERROR";
            case ErrorCode::TimeoutError: return "TIMEOUT_ERROR";
            case ErrorCode::ResourceExhausted: return "RESOURCE_EXHAUSTED";
            
            // クライアントエラー (400-499)
            case ErrorCode::TooManyRequests: return "TOO_MANY_REQUESTS";
            case ErrorCode::RequestTooLarge: return "REQUEST_TOO_LARGE";
            case ErrorCode::InvalidContentType: return "INVALID_CONTENT_TYPE";
            case ErrorCode::MalformedRequest: return "MALFORMED_REQUEST";
            
            // カスタムエラー (500-999)
            case ErrorCode::CustomError: return "CUSTOM_ERROR";
            
            default: return "UNKNOWN_ERROR";
        }
    }
    
    std::string get_default_message(ErrorCode code) {
        switch (code) {
            case ErrorCode::NoError: return "No error";
            
            // 基本的なエラー
            case ErrorCode::InvalidRequest: return "Invalid request format or content";
            case ErrorCode::InvalidPacketFormat: return "Packet format is invalid or corrupted";
            case ErrorCode::ChecksumMismatch: return "Packet checksum verification failed";
            case ErrorCode::UnsupportedVersion: return "Protocol version is not supported";
            case ErrorCode::InvalidFieldValue: return "One or more field values are invalid";
            
            // 認証・権限エラー
            case ErrorCode::AuthenticationRequired: return "Authentication is required";
            case ErrorCode::AuthenticationFailed: return "Authentication credentials are invalid";
            case ErrorCode::InsufficientPermissions: return "Insufficient permissions for this operation";
            case ErrorCode::TokenExpired: return "Authentication token has expired";
            
            // データエラー
            case ErrorCode::InvalidAreaCode: return "Area code is invalid or out of range";
            case ErrorCode::InvalidCoordinate: return "Geographic coordinates are invalid";
            case ErrorCode::InvalidWeatherCode: return "Weather code is invalid or unsupported";
            case ErrorCode::InvalidTemperature: return "Temperature value is out of valid range";
            case ErrorCode::InvalidPrecipitationProb: return "Precipitation probability is out of valid range";
            case ErrorCode::DataNotFound: return "Requested data not found";
            case ErrorCode::DataExpired: return "Requested data has expired";
            
            // サーバーエラー
            case ErrorCode::InternalServerError: return "An internal server error occurred";
            case ErrorCode::ServiceUnavailable: return "Service is temporarily unavailable";
            case ErrorCode::DatabaseError: return "Database operation failed";
            case ErrorCode::NetworkError: return "Network communication error";
            case ErrorCode::TimeoutError: return "Operation timed out";
            case ErrorCode::ResourceExhausted: return "Server resources are exhausted";
            
            // クライアントエラー
            case ErrorCode::TooManyRequests: return "Too many requests - rate limit exceeded";
            case ErrorCode::RequestTooLarge: return "Request payload is too large";
            case ErrorCode::InvalidContentType: return "Content type is not supported";
            case ErrorCode::MalformedRequest: return "Request is malformed or incomplete";
            
            // カスタムエラー
            case ErrorCode::CustomError: return "Custom application error";
            
            default: return "Unknown error occurred";
        }
    }
    
    uint8_t get_default_severity(ErrorCode code) {
        switch (code) {
            case ErrorCode::NoError:
                return 0; // 情報
                
            // 警告レベル
            case ErrorCode::DataExpired:
            case ErrorCode::TokenExpired:
                return 1; // 警告
                
            // 致命的エラー
            case ErrorCode::InternalServerError:
            case ErrorCode::DatabaseError:
            case ErrorCode::UnsupportedVersion:
                return 3; // 致命的
                
            // その他は一般エラー
            default:
                return 2; // エラー
        }
    }
    
    uint16_t to_http_status(ErrorCode code) {
        switch (code) {
            case ErrorCode::NoError: return 200;
            
            // 基本的なエラー → 400 Bad Request
            case ErrorCode::InvalidRequest:
            case ErrorCode::InvalidPacketFormat:
            case ErrorCode::InvalidFieldValue:
            case ErrorCode::MalformedRequest:
                return 400;
                
            case ErrorCode::ChecksumMismatch: return 422; // Unprocessable Entity
            case ErrorCode::UnsupportedVersion: return 505; // HTTP Version Not Supported
            
            // 認証・権限エラー
            case ErrorCode::AuthenticationRequired: return 401; // Unauthorized
            case ErrorCode::AuthenticationFailed: return 401; // Unauthorized
            case ErrorCode::InsufficientPermissions: return 403; // Forbidden
            case ErrorCode::TokenExpired: return 401; // Unauthorized
            
            // データエラー
            case ErrorCode::InvalidAreaCode:
            case ErrorCode::InvalidCoordinate:
            case ErrorCode::InvalidWeatherCode:
            case ErrorCode::InvalidTemperature:
            case ErrorCode::InvalidPrecipitationProb:
                return 400; // Bad Request
                
            case ErrorCode::DataNotFound: return 404; // Not Found
            case ErrorCode::DataExpired: return 410; // Gone
            
            // サーバーエラー
            case ErrorCode::InternalServerError: return 500; // Internal Server Error
            case ErrorCode::ServiceUnavailable: return 503; // Service Unavailable
            case ErrorCode::DatabaseError: return 500; // Internal Server Error
            case ErrorCode::NetworkError: return 502; // Bad Gateway
            case ErrorCode::TimeoutError: return 504; // Gateway Timeout
            case ErrorCode::ResourceExhausted: return 507; // Insufficient Storage
            
            // クライアントエラー
            case ErrorCode::TooManyRequests: return 429; // Too Many Requests
            case ErrorCode::RequestTooLarge: return 413; // Payload Too Large
            case ErrorCode::InvalidContentType: return 415; // Unsupported Media Type
            
            // カスタムエラー
            case ErrorCode::CustomError: return 500; // Internal Server Error
            
            default: return 500; // Internal Server Error
        }
    }
    
    bool is_retryable(ErrorCode code) {
        switch (code) {
            // リトライ可能なエラー
            case ErrorCode::NetworkError:
            case ErrorCode::TimeoutError:
            case ErrorCode::ServiceUnavailable:
            case ErrorCode::ResourceExhausted:
            case ErrorCode::TooManyRequests:
                return true;
                
            // リトライ不可能なエラー
            case ErrorCode::InvalidRequest:
            case ErrorCode::InvalidPacketFormat:
            case ErrorCode::ChecksumMismatch:
            case ErrorCode::UnsupportedVersion:
            case ErrorCode::InvalidFieldValue:
            case ErrorCode::AuthenticationFailed:
            case ErrorCode::InsufficientPermissions:
            case ErrorCode::InvalidAreaCode:
            case ErrorCode::InvalidCoordinate:
            case ErrorCode::InvalidWeatherCode:
            case ErrorCode::InvalidTemperature:
            case ErrorCode::InvalidPrecipitationProb:
            case ErrorCode::DataNotFound:
            case ErrorCode::DataExpired:
            case ErrorCode::RequestTooLarge:
            case ErrorCode::InvalidContentType:
            case ErrorCode::MalformedRequest:
                return false;
                
            // 一時的な認証エラーはリトライ可能な場合がある
            case ErrorCode::AuthenticationRequired:
            case ErrorCode::TokenExpired:
                return true;
                
            // サーバーエラーは基本的にリトライ可能
            case ErrorCode::InternalServerError:
            case ErrorCode::DatabaseError:
                return true;
                
            default:
                return false; // 安全のためデフォルトはリトライ不可
        }
    }
}

} // namespace wiplib::packet