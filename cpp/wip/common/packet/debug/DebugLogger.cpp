#include "DebugLogger.hpp"

namespace packet {
namespace debug {

PacketDebugLogger::PacketDebugLogger(const std::string& loggerName, bool debugEnabled)
    : loggerName_(loggerName), debugEnabled_(debugEnabled) {}

void PacketDebugLogger::setDebugEnabled(bool enabled) { debugEnabled_ = enabled; }

bool PacketDebugLogger::isDebugEnabled() const { return debugEnabled_; }

void PacketDebugLogger::logError(const std::string& errorMsg, const std::string& errorCode) const {
    if (!errorCode.empty()) {
        std::cerr << "[" << errorCode << "] " << errorMsg << std::endl;
    } else {
        std::cerr << errorMsg << std::endl;
    }
}

void PacketDebugLogger::debug(const std::string& message) const {
    if (debugEnabled_) {
        std::cout << message << std::endl;
    }
}

void PacketDebugLogger::info(const std::string& message) const { std::cout << message << std::endl; }

void PacketDebugLogger::warning(const std::string& message) const { std::cout << message << std::endl; }

void PacketDebugLogger::error(const std::string& message) const { std::cerr << message << std::endl; }

std::string PacketDebugLogger::getPacketTypeName(int type) const {
    switch (type) {
    case 0:
        return "Location Request";
    case 1:
        return "Location Response";
    case 2:
        return "Query Request";
    case 3:
        return "Query Response";
    case 4:
        return "Report Request";
    case 5:
        return "Report Response";
    case 7:
        return "Error Response";
    default:
        return "Unknown(" + std::to_string(type) + ")";
    }
}

std::string PacketDebugLogger::formatWeatherData(const std::unordered_map<std::string, std::string>& data) const {
    std::vector<std::string> parts;
    auto it = data.find("weather_code");
    if (it != data.end())
        parts.push_back("Weather: " + it->second);
    it = data.find("temperature");
    if (it != data.end())
        parts.push_back("Temp: " + it->second + "°C");
    it = data.find("precipitation_prob");
    if (it != data.end())
        parts.push_back("Precip: " + it->second + "%");
    it = data.find("alert");
    if (it != data.end() && !it->second.empty())
        parts.push_back("Alert: Yes");
    it = data.find("disaster");
    if (it != data.end() && !it->second.empty())
        parts.push_back("Disaster: Yes");
    std::string result;
    for (size_t i = 0; i < parts.size(); ++i) {
        if (i)
            result += ", ";
        result += parts[i];
    }
    return result.empty() ? "No data" : result;
}

void PacketDebugLogger::logSummary(const std::unordered_map<std::string, std::string>& summary) const {
    if (summary.empty())
        return;
    std::cout << "  Summary:" << std::endl;
    for (const auto& kv : summary) {
        std::cout << "    " << kv.first << ": " << kv.second << std::endl;
    }
}

void PacketDebugLogger::logSuccessResult(const std::unordered_map<std::string, std::string>& result,
                                         const std::string& operationType) const {
    std::cout << "\n\xE2\x9C\x93 " << operationType << " Success!" << std::endl;

    auto it = result.find("area_code");
    if (it != result.end() && !it->second.empty())
        std::cout << "Area Code: " << it->second << std::endl;

    it = result.find("timestamp");
    if (it != result.end() && !it->second.empty())
        std::cout << "Timestamp: " << it->second << std::endl;

    it = result.find("weather_code");
    if (it != result.end())
        std::cout << "Weather Code: " << it->second << std::endl;

    it = result.find("temperature");
    if (it != result.end())
        std::cout << "Temperature: " << it->second << "°C" << std::endl;

    it = result.find("precipitation_prob");
    if (it != result.end())
        std::cout << "Precipitation Probability: " << it->second << "%" << std::endl;

    it = result.find("alert");
    if (it != result.end() && !it->second.empty())
        std::cout << "Alert: " << it->second << std::endl;

    it = result.find("disaster");
    if (it != result.end() && !it->second.empty())
        std::cout << "Disaster Info: " << it->second << std::endl;

    it = result.find("cache_hit");
    if (it != result.end() && it->second == "1")
        std::cout << "Source: Cache" << std::endl;

    it = result.find("total_time");
    if (it != result.end())
        std::cout << "Response Time: " << it->second << "ms" << std::endl;
}

PacketDebugLogger create_debug_logger(const std::string& loggerName, bool debugEnabled) {
    return PacketDebugLogger(loggerName, debugEnabled);
}

} // namespace debug
} // namespace packet

