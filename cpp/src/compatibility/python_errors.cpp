#include "wiplib/compatibility/python_errors.hpp"
#include <sstream>

namespace wiplib::compatibility {

std::unique_ptr<PythonCompatibleError> create_python_error(
    PythonErrorCode code, 
    const std::string& message
) {
    std::string error_msg = message.empty() ? "エラーが発生しました" : message;
    
    switch (code) {
        case PythonErrorCode::CONNECTION_ERROR:
        case PythonErrorCode::NETWORK_UNREACHABLE:
            return std::make_unique<ConnectionError>(error_msg);
            
        case PythonErrorCode::TIMEOUT_ERROR:
            return std::make_unique<TimeoutError>(error_msg);
            
        case PythonErrorCode::INVALID_COORDINATES:
            return std::make_unique<InvalidCoordinatesError>(error_msg);
            
        case PythonErrorCode::INVALID_AREA_CODE:
            return std::make_unique<InvalidAreaCodeError>(error_msg);
            
        case PythonErrorCode::SERVER_ERROR:
        case PythonErrorCode::SERVICE_UNAVAILABLE:
        case PythonErrorCode::AUTHENTICATION_FAILED:
            return std::make_unique<ServerError>(error_msg);
            
        default:
            return std::make_unique<PythonCompatibleError>(code, error_msg);
    }
}

std::unique_ptr<PythonCompatibleError> convert_system_error(
    const std::error_code& ec,
    const std::string& context
) {
    std::string message = ec.message();
    if (!context.empty()) {
        message = context + ": " + message;
    }
    
    // システムエラーをPython互換エラーにマッピング
    PythonErrorCode python_code;
    
    if (ec.category() == std::system_category()) {
        switch (ec.value()) {
            case 10060: // WSAETIMEDOUT
            case 110:   // ETIMEDOUT
                python_code = PythonErrorCode::TIMEOUT_ERROR;
                break;
                
            case 10061: // WSAECONNREFUSED
            case 111:   // ECONNREFUSED
                python_code = PythonErrorCode::CONNECTION_ERROR;
                break;
                
            case 10051: // WSAENETUNREACH
            case 101:   // ENETUNREACH
                python_code = PythonErrorCode::NETWORK_UNREACHABLE;
                break;
                
            default:
                python_code = PythonErrorCode::INTERNAL_ERROR;
                break;
        }
    } else {
        python_code = PythonErrorCode::INTERNAL_ERROR;
    }
    
    return create_python_error(python_code, message);
}

std::string format_python_error(
    PythonErrorCode code,
    const std::string& message,
    const std::string& context
) {
    std::ostringstream oss;
    oss << "[" << static_cast<int>(code) << "]";
    
    if (!context.empty()) {
        oss << " " << context << ":";
    }
    
    oss << " " << message;
    return oss.str();
}

} // namespace wiplib::compatibility