#pragma once

#include <cstdint>
#include <string>
#include <optional>
#include <unordered_map>
#include <span>
#include "wiplib/packet/packet.hpp"

namespace wiplib::packet {

/**
 * @brief エラーコード定義
 */
enum class ErrorCode : uint16_t {
    NoError = 0,
    
    // 基本的なエラー (1-99)
    InvalidRequest = 1,
    InvalidPacketFormat = 2,
    ChecksumMismatch = 3,
    UnsupportedVersion = 4,
    InvalidFieldValue = 5,
    
    // 認証・権限エラー (100-199)
    AuthenticationRequired = 100,
    AuthenticationFailed = 101,
    InsufficientPermissions = 102,
    TokenExpired = 103,
    
    // データエラー (200-299)
    InvalidAreaCode = 200,
    InvalidCoordinate = 201,
    InvalidWeatherCode = 202,
    InvalidTemperature = 203,
    InvalidPrecipitationProb = 204,
    DataNotFound = 205,
    DataExpired = 206,
    
    // サーバーエラー (300-399)
    InternalServerError = 300,
    ServiceUnavailable = 301,
    DatabaseError = 302,
    NetworkError = 303,
    TimeoutError = 304,
    ResourceExhausted = 305,
    
    // クライアントエラー (400-499)
    TooManyRequests = 400,
    RequestTooLarge = 401,
    InvalidContentType = 402,
    MalformedRequest = 403,
    
    // カスタムエラー (500-999)
    CustomError = 500
};

/**
 * @brief エラー応答パケット
 */
struct ErrorResponse {
    proto::Header header{};
    ErrorCode error_code = ErrorCode::NoError;
    uint8_t severity = 0;              // エラー重要度（0=情報, 1=警告, 2=エラー, 3=致命的）
    uint16_t sub_error_code = 0;       // サブエラーコード（詳細分類用）
    std::string error_message{};       // エラーメッセージ
    std::string debug_info{};          // デバッグ情報（開発用）
    uint64_t server_timestamp = 0;     // サーバータイムスタンプ
    
    /**
     * @brief パケットを作成
     * @param request_packet_id 対応するリクエストのパケットID
     * @param error_code エラーコード
     * @param message エラーメッセージ
     * @param severity 重要度
     * @return ErrorResponseパケット
     */
    static ErrorResponse create(uint16_t request_packet_id, ErrorCode error_code,
                              const std::string& message, uint8_t severity = 2);
    
    /**
     * @brief 詳細エラー情報付きでパケットを作成
     * @param request_packet_id 対応するリクエストのパケットID
     * @param error_code エラーコード
     * @param sub_error_code サブエラーコード
     * @param message エラーメッセージ
     * @param debug_info デバッグ情報
     * @param severity 重要度
     * @return ErrorResponseパケット
     */
    static ErrorResponse create_detailed(uint16_t request_packet_id, ErrorCode error_code,
                                       uint16_t sub_error_code, const std::string& message,
                                       const std::string& debug_info = "", uint8_t severity = 2);
    
    /**
     * @brief バイナリデータからパケットをデコード
     * @param data バイナリデータ
     * @return デコードされたパケット
     */
    static std::optional<ErrorResponse> decode(std::span<const uint8_t> data);
    
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
     * @brief エラーが致命的かどうか判定
     * @return 致命的エラーの場合true
     */
    bool is_fatal() const;
    
    /**
     * @brief エラー情報を文字列として取得
     * @return エラー情報文字列
     */
    std::string to_string() const;
};

/**
 * @brief エラーコード管理ユーティリティ
 */
namespace error_utils {
    /**
     * @brief エラーコードから文字列表現を取得
     * @param code エラーコード
     * @return エラーコード文字列
     */
    std::string error_code_to_string(ErrorCode code);
    
    /**
     * @brief エラーコードから標準メッセージを取得
     * @param code エラーコード
     * @return 標準エラーメッセージ
     */
    std::string get_default_message(ErrorCode code);
    
    /**
     * @brief エラーコードから推奨重要度を取得
     * @param code エラーコード
     * @return 推奨重要度
     */
    uint8_t get_default_severity(ErrorCode code);
    
    /**
     * @brief HTTPステータスコードに変換
     * @param code エラーコード
     * @return HTTPステータスコード
     */
    uint16_t to_http_status(ErrorCode code);
    
    /**
     * @brief エラーコードがリトライ可能かどうか判定
     * @param code エラーコード
     * @return リトライ可能な場合true
     */
    bool is_retryable(ErrorCode code);
}

} // namespace wiplib::packet