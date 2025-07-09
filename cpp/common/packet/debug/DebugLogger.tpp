#include "DebugLogger.hpp"

namespace packet {
namespace debug {

namespace detail {

// trait helpers

template <typename T, typename = void>
struct has_type : std::false_type {};

template <typename T>
struct has_type<T, std::void_t<decltype(std::declval<T>().type)>> : std::true_type {};

template <typename T, typename = void>
struct has_packet_id : std::false_type {};

template <typename T>
struct has_packet_id<T, std::void_t<decltype(std::declval<T>().packet_id)>> : std::true_type {};

template <typename T, typename = void>
struct has_area_code : std::false_type {};

template <typename T>
struct has_area_code<T, std::void_t<decltype(std::declval<T>().area_code)>> : std::true_type {};

template <typename T, typename = void>
struct has_is_success : std::false_type {};

template <typename T>
struct has_is_success<T, std::void_t<decltype(std::declval<T>().is_success())>> : std::true_type {};

template <typename T, typename = void>
struct has_is_valid : std::false_type {};

template <typename T>
struct has_is_valid<T, std::void_t<decltype(std::declval<T>().is_valid())>> : std::true_type {};

template <typename T, typename = void>
struct has_error_code : std::false_type {};

template <typename T>
struct has_error_code<T, std::void_t<decltype(std::declval<T>().error_code)>> : std::true_type {};

template <typename T, typename = void>
struct has_get_response_summary : std::false_type {};

template <typename T>
struct has_get_response_summary<T, std::void_t<decltype(std::declval<T>().get_response_summary())>> : std::true_type {};

template <typename T, typename = void>
struct has_get_weather_data : std::false_type {};

template <typename T>
struct has_get_weather_data<T, std::void_t<decltype(std::declval<T>().get_weather_data())>> : std::true_type {};

template <typename T, typename = void>
struct has_weather_flag : std::false_type {};

template <typename T>
struct has_weather_flag<T, std::void_t<decltype(std::declval<T>().weather_flag)>> : std::true_type {};

template <typename T, typename = void>
struct has_temperature_flag : std::false_type {};

template <typename T>
struct has_temperature_flag<T, std::void_t<decltype(std::declval<T>().temperature_flag)>> : std::true_type {};

template <typename T, typename = void>
struct has_pop_flag : std::false_type {};

template <typename T>
struct has_pop_flag<T, std::void_t<decltype(std::declval<T>().pop_flag)>> : std::true_type {};

template <typename T, typename = void>
struct has_alert_flag : std::false_type {};

template <typename T>
struct has_alert_flag<T, std::void_t<decltype(std::declval<T>().alert_flag)>> : std::true_type {};

template <typename T, typename = void>
struct has_disaster_flag : std::false_type {};

template <typename T>
struct has_disaster_flag<T, std::void_t<decltype(std::declval<T>().disaster_flag)>> : std::true_type {};

} // namespace detail

template <typename Packet>
std::vector<std::string> PacketDebugLogger::extractRequestFlags(const Packet& packet) const {
    std::vector<std::string> flags;
    if constexpr (detail::has_weather_flag<Packet>::value) {
        if (packet.weather_flag)
            flags.emplace_back("Weather");
    }
    if constexpr (detail::has_temperature_flag<Packet>::value) {
        if (packet.temperature_flag)
            flags.emplace_back("Temperature");
    }
    if constexpr (detail::has_pop_flag<Packet>::value) {
        if (packet.pop_flag)
            flags.emplace_back("Precipitation");
    }
    if constexpr (detail::has_alert_flag<Packet>::value) {
        if (packet.alert_flag)
            flags.emplace_back("Alert");
    }
    if constexpr (detail::has_disaster_flag<Packet>::value) {
        if (packet.disaster_flag)
            flags.emplace_back("Disaster");
    }
    return flags;
}

template <typename Packet>
void PacketDebugLogger::logRequest(const Packet& packet, const std::string& operationType) const {
    if (!debugEnabled_)
        return;
    std::string packetTypeName = "Unknown";
    if constexpr (detail::has_type<Packet>::value) {
        packetTypeName = getPacketTypeName(packet.type);
    }
    std::string packetId = "N/A";
    if constexpr (detail::has_packet_id<Packet>::value) {
        packetId = std::to_string(packet.packet_id);
    }
    std::string areaCode = "N/A";
    if constexpr (detail::has_area_code<Packet>::value) {
        areaCode = packet.area_code;
    }
    auto flags = extractRequestFlags(packet);
    std::string flagsStr = flags.empty() ? "None" : flags.front();
    for (size_t i = 1; i < flags.size(); ++i)
        flagsStr += ", " + flags[i];

    std::cout << operationType << ": " << packetTypeName
              << " | ID:" << packetId
              << " | Area:" << areaCode
              << " | Data:" << flagsStr << std::endl;
}

template <typename Packet>
void PacketDebugLogger::logResponse(const Packet& packet, const std::string& operationType) const {
    if (!debugEnabled_)
        return;
    std::string packetTypeName = "Unknown";
    if constexpr (detail::has_type<Packet>::value) {
        packetTypeName = getPacketTypeName(packet.type);
    }
    std::string status = "Unknown";
    if constexpr (detail::has_is_success<Packet>::value) {
        status = packet.is_success() ? "Success" : "Failed";
    } else if constexpr (detail::has_is_valid<Packet>::value) {
        status = packet.is_valid() ? "Valid" : "Invalid";
    } else if constexpr (detail::has_error_code<Packet>::value) {
        status = "Error:" + std::to_string(packet.error_code);
    }
    std::cout << operationType << ": " << packetTypeName << std::endl;
    std::string packetId = "N/A";
    if constexpr (detail::has_packet_id<Packet>::value) {
        packetId = std::to_string(packet.packet_id);
    }
    std::cout << "  Packet ID: " << packetId << std::endl;
    std::cout << "  Status: " << status << std::endl;

    if constexpr (detail::has_get_response_summary<Packet>::value) {
        auto summary = packet.get_response_summary();
        logSummary(summary);
    } else if constexpr (detail::has_get_weather_data<Packet>::value) {
        auto weatherData = packet.get_weather_data();
        if (!weatherData.empty()) {
            std::cout << "  Weather Data:" << std::endl;
            std::cout << "    " << formatWeatherData(weatherData) << std::endl;
        }
    }
}

} // namespace debug
} // namespace packet

