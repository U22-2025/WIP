#pragma once

#include <stdexcept>
#include <string>
#include <system_error>

namespace wiplib::compatibility {

/**
 * @brief Python互換エラーコード
 * Python版WIPClientPyと同一のエラーコード体系
 */
enum class PythonErrorCode {
    // ネットワークエラー
    CONNECTION_ERROR = 1001,
    TIMEOUT_ERROR = 1002,
    NETWORK_UNREACHABLE = 1003,
    
    // プロトコルエラー
    INVALID_PACKET = 2001,
    CHECKSUM_MISMATCH = 2002,
    PROTOCOL_VERSION_MISMATCH = 2003,
    
    // データエラー
    INVALID_COORDINATES = 3001,
    INVALID_AREA_CODE = 3002,
    INVALID_REQUEST_DATA = 3003,
    
    // サーバーエラー
    SERVER_ERROR = 4001,
    SERVICE_UNAVAILABLE = 4002,
    AUTHENTICATION_FAILED = 4003,
    
    // 設定エラー
    INVALID_CONFIGURATION = 5001,
    MISSING_CREDENTIALS = 5002,
    
    // 内部エラー
    INTERNAL_ERROR = 9001,
    NOT_IMPLEMENTED = 9002
};

/**
 * @brief Python互換例外基底クラス
 */
class PythonCompatibleError : public std::runtime_error {
public:
    PythonCompatibleError(PythonErrorCode code, const std::string& message)
        : std::runtime_error(message), error_code_(code) {}
    
    PythonErrorCode code() const noexcept { return error_code_; }
    int code_value() const noexcept { return static_cast<int>(error_code_); }
    
    // Python版と同じ形式のエラーメッセージ
    virtual std::string python_format() const {
        return "[" + std::to_string(code_value()) + "] " + what();
    }

private:
    PythonErrorCode error_code_;
};

/**
 * @brief 接続エラー（Python: ConnectionError）
 */
class ConnectionError : public PythonCompatibleError {
public:
    ConnectionError(const std::string& message = "接続エラーが発生しました")
        : PythonCompatibleError(PythonErrorCode::CONNECTION_ERROR, message) {}
};

/**
 * @brief タイムアウトエラー（Python: TimeoutError）
 */
class TimeoutError : public PythonCompatibleError {
public:
    TimeoutError(const std::string& message = "リクエストがタイムアウトしました")
        : PythonCompatibleError(PythonErrorCode::TIMEOUT_ERROR, message) {}
};

/**
 * @brief 無効な座標エラー（Python: InvalidCoordinatesError）
 */
class InvalidCoordinatesError : public PythonCompatibleError {
public:
    InvalidCoordinatesError(const std::string& message = "無効な座標が指定されました")
        : PythonCompatibleError(PythonErrorCode::INVALID_COORDINATES, message) {}
};

/**
 * @brief 無効なエリアコードエラー（Python: InvalidAreaCodeError）
 */
class InvalidAreaCodeError : public PythonCompatibleError {
public:
    InvalidAreaCodeError(const std::string& message = "無効なエリアコードが指定されました")
        : PythonCompatibleError(PythonErrorCode::INVALID_AREA_CODE, message) {}
};

/**
 * @brief サーバーエラー（Python: ServerError）
 */
class ServerError : public PythonCompatibleError {
public:
    ServerError(const std::string& message = "サーバーエラーが発生しました")
        : PythonCompatibleError(PythonErrorCode::SERVER_ERROR, message) {}
};

/**
 * @brief エラーコードから適切な例外を生成するファクトリ関数
 */
std::unique_ptr<PythonCompatibleError> create_python_error(
    PythonErrorCode code, 
    const std::string& message = ""
);

/**
 * @brief std::error_codeからPython互換エラーに変換
 */
std::unique_ptr<PythonCompatibleError> convert_system_error(
    const std::error_code& ec,
    const std::string& context = ""
);

/**
 * @brief Python形式のエラー文字列を生成
 */
std::string format_python_error(
    PythonErrorCode code,
    const std::string& message,
    const std::string& context = ""
);

} // namespace wiplib::compatibility