#pragma once

#include <vector>
#include <string>
#include <cstdint>
#include <map>
#include "wiplib/packet/packet.hpp"
#include "wiplib/expected.hpp"

namespace wiplib::compatibility {

/**
 * @brief Python版WIPClientPyとの通信プロトコル互換性を保証するクラス
 */
class PythonProtocolAdapter {
public:
    /**
     * @brief Python版と同一のパケットフォーマットでエンコード
     */
    static wiplib::Result<std::vector<uint8_t>> encode_python_packet(
        const wiplib::proto::Packet& packet
    );
    
    /**
     * @brief Python版と同一のパケットフォーマットでデコード
     */
    static wiplib::Result<wiplib::proto::Packet> decode_python_packet(
        const std::vector<uint8_t>& data
    );
    
    /**
     * @brief Python版と同一のチェックサム計算アルゴリズム
     */
    static uint16_t calculate_python_checksum(const std::vector<uint8_t>& data);
    
    /**
     * @brief Python版と同一のエラーコードマッピング
     */
    static int map_error_to_python_code(const std::error_code& ec);
    
    /**
     * @brief Python版互換のタイムスタンプ生成
     */
    static uint64_t generate_python_timestamp();
    
    /**
     * @brief Python版と同一のパケットID生成アルゴリズム
     */
    static uint16_t generate_python_packet_id();

    /**
     * @brief Python版互換のエリアコード検証
     */
    static bool validate_python_area_code(const std::string& area_code);
    
    /**
     * @brief Python版互換の座標検証
     */
    static bool validate_python_coordinates(double latitude, double longitude);
    
    /**
     * @brief Python版と同一のUser-Agent文字列生成
     */
    static std::string generate_python_user_agent();
    
    /**
     * @brief Python版と同一のリクエストヘッダー生成
     */
    static std::map<std::string, std::string> generate_python_headers();

private:
    static uint16_t packet_id_counter_;
    static const uint8_t PYTHON_PROTOCOL_VERSION = 1;
    static const char* PYTHON_USER_AGENT_BASE;
};

/**
 * @brief Python版互換のデータフォーマット変換ユーティリティ
 */
class PythonDataConverter {
public:
    /**
     * @brief C++の天気データをPython形式のJSONに変換
     */
    static std::string weather_data_to_python_json(
        const wiplib::client::WeatherData& data
    );
    
    /**
     * @brief Python形式のJSONをC++の天気データに変換
     */
    static wiplib::Result<wiplib::client::WeatherData> python_json_to_weather_data(
        const std::string& json
    );
    
    /**
     * @brief Python版と同一の日時フォーマット
     */
    static std::string format_python_datetime(uint64_t timestamp);
    
    /**
     * @brief Python版と同一の日時パース
     */
    static uint64_t parse_python_datetime(const std::string& datetime_str);
    
    /**
     * @brief Python版互換の座標フォーマット
     */
    static std::string format_python_coordinates(double latitude, double longitude);
    
    /**
     * @brief Python版互換のエラーレスポンス生成
     */
    static std::string generate_python_error_response(
        int error_code,
        const std::string& message,
        const std::string& details = ""
    );

private:
    static const char* PYTHON_DATETIME_FORMAT;
};

/**
 * @brief Python版互換の通信設定
 */
class PythonNetworkConfig {
public:
    static constexpr int PYTHON_DEFAULT_TIMEOUT_MS = 5000;
    static constexpr int PYTHON_DEFAULT_RETRY_COUNT = 3;
    static constexpr uint16_t PYTHON_DEFAULT_PORT = 4110;
    static constexpr size_t PYTHON_MAX_PACKET_SIZE = 65536;
    static constexpr size_t PYTHON_BUFFER_SIZE = 8192;
    
    /**
     * @brief Python版と同一のソケットオプション設定
     */
    static void configure_python_socket_options(int socket_fd);
    
    /**
     * @brief Python版と同一のタイムアウト設定
     */
    static void set_python_socket_timeout(int socket_fd, int timeout_ms);
    
    /**
     * @brief Python版互換のキープアライブ設定
     */
    static void configure_python_keepalive(int socket_fd, bool enable = true);
};

/**
 * @brief Python版互換性チェック機能
 */
class PythonCompatibilityChecker {
public:
    /**
     * @brief プロトコルバージョンの互換性チェック
     */
    static bool check_protocol_compatibility(uint8_t version);
    
    /**
     * @brief パケットフォーマットの互換性チェック
     */
    static bool check_packet_format_compatibility(
        const std::vector<uint8_t>& packet_data
    );
    
    /**
     * @brief API互換性の完全チェック
     */
    static std::vector<std::string> perform_full_compatibility_check();
    
    /**
     * @brief 互換性レポート生成
     */
    static std::string generate_compatibility_report();
};

} // namespace wiplib::compatibility