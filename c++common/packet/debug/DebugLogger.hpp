#ifndef PACKET_DEBUG_LOGGER_HPP
#define PACKET_DEBUG_LOGGER_HPP

#include <string>
#include <vector>
#include <unordered_map>
#include <iostream>
#include <type_traits>

namespace packet {
namespace debug {

class PacketDebugLogger {
public:
    PacketDebugLogger(const std::string& loggerName, bool debugEnabled = false);

    void setDebugEnabled(bool enabled);
    bool isDebugEnabled() const;

    template <typename Packet>
    void logRequest(const Packet& packet, const std::string& operationType = "REQUEST") const;

    template <typename Packet>
    void logResponse(const Packet& packet, const std::string& operationType = "RESPONSE") const;

    void logError(const std::string& errorMsg, const std::string& errorCode = std::string()) const;
    void debug(const std::string& message) const;
    void info(const std::string& message) const;
    void warning(const std::string& message) const;
    void error(const std::string& message) const;

    void logSuccessResult(const std::unordered_map<std::string, std::string>& result,
                          const std::string& operationType = "OPERATION") const;

private:
    std::string loggerName_;
    bool debugEnabled_;

    std::string getPacketTypeName(int type) const;

    template <typename Packet>
    std::vector<std::string> extractRequestFlags(const Packet& packet) const;

    std::string formatWeatherData(const std::unordered_map<std::string, std::string>& data) const;
    void logSummary(const std::unordered_map<std::string, std::string>& summary) const;
};

PacketDebugLogger create_debug_logger(const std::string& loggerName,
                                      bool debugEnabled = false);

} // namespace debug
} // namespace packet

#include "DebugLogger.tpp"

#endif // PACKET_DEBUG_LOGGER_HPP
