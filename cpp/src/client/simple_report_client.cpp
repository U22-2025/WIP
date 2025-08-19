#include "wiplib/client/simple_report_client.hpp"

#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <netdb.h>
#include <unistd.h>
#include <chrono>
#include <cstring>
#include <cstdlib>
#include <stdexcept>
#include <algorithm>
#include <vector>
#include <future>
#include <iostream>
#include <thread>
#include <span>

#include "wiplib/packet/types.hpp"
#include "wiplib/packet/codec.hpp"
#include "wiplib/utils/auth.hpp"
#include "wiplib/error.hpp"

namespace wiplib::client {

// SimpleReportClient implementation

SimpleReportClient::SimpleReportClient(std::string host, uint16_t port, bool debug)
    : host_(std::move(host))
    , port_(port)
    , debug_(debug)
    , socket_fd_(-1)
    , socket_closed_(false)
    , auth_enabled_(false)
{
    // Python版と同様の環境変数からの初期化
    if (host_ == "localhost") {
        const char* env_host = std::getenv("REPORT_SERVER_HOST");
        if (env_host) {
            host_ = env_host;
        }
    }
    
    if (port_ == 4112) {
        const char* env_port = std::getenv("REPORT_SERVER_PORT");
        if (env_port) {
            port_ = static_cast<uint16_t>(std::atoi(env_port));
        }
    }
    
    // IPv4アドレス解決（Python版resolve_ipv4互換）
    if (host_ == "localhost") {
        host_ = "127.0.0.1";
    }
    
    // デバッグロガー初期化（現在は未使用、将来の拡張用）
    // debug_logger_ = std::make_unique<packet::debug::PacketDebugLogger>("SimpleReportClient", debug_);
    
    // パケットIDジェネレーター初期化
    pid_generator_ = std::make_unique<packet::compat::PyPacketIDGenerator>();
    
    // 認証設定を初期化
    init_auth_config();
    
    // ソケット初期化
    if (!init_socket()) {
        throw std::runtime_error("Failed to initialize UDP socket");
    }
}

SimpleReportClient::~SimpleReportClient() {
    close();
}

void SimpleReportClient::init_auth_config() {
    // Python版_init_auth_config()互換
    const char* auth_enabled_env = std::getenv("REPORT_SERVER_REQUEST_AUTH_ENABLED");
    auth_enabled_ = (auth_enabled_env && std::string(auth_enabled_env) == "true");
    
    const char* auth_passphrase_env = std::getenv("REPORT_SERVER_PASSPHRASE");
    auth_passphrase_ = auth_passphrase_env ? auth_passphrase_env : "";
}

bool SimpleReportClient::init_socket() {
    socket_fd_ = socket(AF_INET, SOCK_DGRAM, 0);
    if (socket_fd_ < 0) {
        return false;
    }
    
    // タイムアウト設定（Python版と同様に10秒）
    struct timeval timeout;
    timeout.tv_sec = 10;
    timeout.tv_usec = 0;
    
    if (setsockopt(socket_fd_, SOL_SOCKET, SO_RCVTIMEO, &timeout, sizeof(timeout)) < 0) {
        ::close(socket_fd_);
        socket_fd_ = -1;
        return false;
    }
    
    socket_closed_ = false;

    // 送信先アドレスを解決
    // すでにIPならそのまま、ホスト名ならDNS解決
    struct sockaddr_in addr;
    memset(&addr, 0, sizeof(addr));
    addr.sin_family = AF_INET;
    addr.sin_port = htons(port_);

    // まずはIPv4文字列として解釈を試みる
    if (inet_pton(AF_INET, host_.c_str(), &addr.sin_addr) != 1) {
        // ホスト名解決
        struct addrinfo hints{};
        struct addrinfo* res = nullptr;
        hints.ai_family = AF_INET;     // IPv4のみ
        hints.ai_socktype = SOCK_DGRAM;
        int rc = getaddrinfo(host_.c_str(), nullptr, &hints, &res);
        if (rc != 0 || !res) {
            ::close(socket_fd_);
            socket_fd_ = -1;
            return false;
        }
        auto* ipv4 = reinterpret_cast<struct sockaddr_in*>(res->ai_addr);
        addr.sin_addr = ipv4->sin_addr;
        freeaddrinfo(res);
    }

    // 以後のsendtoで使うため、解決済みアドレスをメンバに保持
    // メンバがないためここでは毎回構築する方式を維持し、send側で再利用
    // （send側で同じ手順を踏むのはコスト小のため妥当）
    return true;
}

void SimpleReportClient::set_sensor_data(
    const std::string& area_code,
    std::optional<int> weather_code,
    std::optional<float> temperature,
    std::optional<int> precipitation_prob,
    std::optional<std::vector<std::string>> alert,
    std::optional<std::vector<std::string>> disaster
) {
    area_code_ = area_code;
    weather_code_ = weather_code;
    temperature_ = temperature;
    precipitation_prob_ = precipitation_prob;
    alert_ = alert;
    disaster_ = disaster;
    
    // デバッグ情報の出力（コンソール出力に変更）
    if (debug_) {
        std::cout << "センサーデータを設定: エリア=" << area_code
                  << ", 天気=" << (weather_code ? std::to_string(*weather_code) : "null")
                  << ", 気温=" << (temperature ? std::to_string(*temperature) + "℃" : "null")
                  << ", 降水確率=" << (precipitation_prob ? std::to_string(*precipitation_prob) + "%" : "null")
                  << ", 警報="
                  << (alert ? std::to_string(alert->size()) : std::string("null"))
                  << ", 災害="
                  << (disaster ? std::to_string(disaster->size()) : std::string("null"))
                  << std::endl;
    }
}

void SimpleReportClient::set_area_code(const std::string& area_code) {
    area_code_ = area_code;
}

void SimpleReportClient::set_weather_code(int weather_code) {
    weather_code_ = weather_code;
}

void SimpleReportClient::set_temperature(float temperature) {
    temperature_ = temperature;
}

void SimpleReportClient::set_precipitation_prob(int precipitation_prob) {
    precipitation_prob_ = precipitation_prob;
}

void SimpleReportClient::set_alert(const std::vector<std::string>& alert) {
    alert_ = alert;
}

void SimpleReportClient::set_disaster(const std::vector<std::string>& disaster) {
    disaster_ = disaster;
}

Result<ReportResult> SimpleReportClient::send_report_data() {
    if (!area_code_.has_value()) {
        return make_error_code(WipErrc::invalid_packet);
    }
    
    if (socket_closed_) {
        return make_error_code(WipErrc::io_error);
    }
    
    auto start_time = std::chrono::high_resolution_clock::now();
    
    // リクエスト作成
    auto request_result = create_request();
    if (!request_result.has_value()) {
        return request_result.error();
    }
    
    auto request = request_result.value();
    
    // デバッグログ
    if (debug_) {
        std::cout << "Sending SENSOR REPORT REQUEST" << std::endl;
    }
    
    // パケット送信
    auto packet_data = request.to_bytes();

    // 送信先アドレスの準備
    struct sockaddr_in server_addr;
    memset(&server_addr, 0, sizeof(server_addr));
    server_addr.sin_family = AF_INET;
    server_addr.sin_port = htons(port_);
    if (inet_pton(AF_INET, host_.c_str(), &server_addr.sin_addr) != 1) {
        // ホスト名解決を実施
        struct addrinfo hints{};
        struct addrinfo* res = nullptr;
        hints.ai_family = AF_INET;
        hints.ai_socktype = SOCK_DGRAM;
        int rc = getaddrinfo(host_.c_str(), nullptr, &hints, &res);
        if (rc != 0 || !res) {
            return make_error_code(WipErrc::io_error);
        }
        auto* ipv4 = reinterpret_cast<struct sockaddr_in*>(res->ai_addr);
        server_addr.sin_addr = ipv4->sin_addr;
        freeaddrinfo(res);
    }

    ssize_t sent_bytes = sendto(socket_fd_, packet_data.data(), packet_data.size(), 0,
                               reinterpret_cast<struct sockaddr*>(&server_addr), sizeof(server_addr));
    
    if (sent_bytes < 0) {
        return make_error_code(WipErrc::io_error);
    }
    
    // レスポンス受信
    auto response_result = receive_response(request.header.packet_id, 10000);
    if (!response_result.has_value()) {
        return response_result;
    }
    
    auto result = response_result.value();
    
    // レスポンス時間計算
    auto end_time = std::chrono::high_resolution_clock::now();
    auto duration = std::chrono::duration_cast<std::chrono::milliseconds>(end_time - start_time);
    result.response_time_ms = duration.count();
    
    // 統一フォーマットでの成功ログ出力（Python版互換）
    if (result.success && debug_) {
        std::unordered_map<std::string, std::string> report_data;
        report_data["area_code"] = *area_code_;
        if (result.timestamp) {
            report_data["timestamp"] = std::to_string(*result.timestamp);
        }
        if (weather_code_) {
            report_data["weather_code"] = std::to_string(*weather_code_);
        }
        if (temperature_) {
            report_data["temperature"] = std::to_string(*temperature_);
        }
        if (precipitation_prob_) {
            report_data["precipitation_prob"] = std::to_string(*precipitation_prob_);
        }
        
        std::cout << "Direct request completed successfully" << std::endl;
    }
    
    return result;
}

std::future<Result<ReportResult>> SimpleReportClient::send_report_data_async() {
    return std::async(std::launch::async, [this]() {
        return send_report_data();
    });
}

Result<ReportResult> SimpleReportClient::send_data_simple() {
    return send_report_data();
}

std::unordered_map<std::string, std::any> SimpleReportClient::get_current_data() const {
    std::unordered_map<std::string, std::any> data;
    
    if (area_code_) data["area_code"] = *area_code_;
    if (weather_code_) data["weather_code"] = *weather_code_;
    if (temperature_) data["temperature"] = *temperature_;
    if (precipitation_prob_) data["precipitation_prob"] = *precipitation_prob_;
    if (alert_) data["alert"] = *alert_;
    if (disaster_) data["disaster"] = *disaster_;
    
    return data;
}

void SimpleReportClient::clear_data() {
    area_code_.reset();
    weather_code_.reset();
    temperature_.reset();
    precipitation_prob_.reset();
    alert_.reset();
    disaster_.reset();
    
    if (debug_) {
        std::cout << "センサーデータをクリアしました" << std::endl;
    }
}

void SimpleReportClient::close() {
    if (socket_fd_ >= 0 && !socket_closed_) {
        ::close(socket_fd_);
        socket_fd_ = -1;
        socket_closed_ = true;
    }
}

Result<ReportResult> SimpleReportClient::send_report() {
    return send_report_data();
}

Result<ReportResult> SimpleReportClient::send_current_data() {
    return send_data_simple();
}

Result<packet::compat::PyReportRequest> SimpleReportClient::create_request() {
    if (!area_code_) {
        return make_error_code(WipErrc::invalid_packet);
    }
    
    // Python版create_sensor_data_report()互換
    auto request = packet::compat::PyReportRequest::create_sensor_data_report(
        *area_code_,
        weather_code_,
        temperature_,
        precipitation_prob_,
        alert_,
        disaster_,
        1  // version
    );
    
    // パケットIDを割り当て
    if (pid_generator_) {
        request.header.packet_id = pid_generator_->next_id();
    }

    // 認証設定を適用（Python版と同様）
    if (auth_enabled_ && !auth_passphrase_.empty()) {
        request.enable_auth(auth_passphrase_);
        request.set_auth_flags();
    }
    
    return request;
}

Result<ReportResult> SimpleReportClient::receive_response(uint16_t packet_id, int timeout_ms) {
    std::vector<uint8_t> buffer(2048);
    struct sockaddr_in sender_addr;
    socklen_t sender_len = sizeof(sender_addr);
    
    // Python版receive_with_id互換の受信ループ
    auto timeout_start = std::chrono::steady_clock::now();
    auto timeout_duration = std::chrono::milliseconds(timeout_ms);
    
    while (true) {
        auto now = std::chrono::steady_clock::now();
        if (now - timeout_start >= timeout_duration) {
            return make_error_code(WipErrc::timeout);
        }
        
        ssize_t received_bytes = recvfrom(socket_fd_, buffer.data(), buffer.size(), 0,
                                         reinterpret_cast<struct sockaddr*>(&sender_addr), &sender_len);
        
        if (received_bytes < 0) {
            if (errno == EAGAIN || errno == EWOULDBLOCK) {
                // CPU過負荷を避けるため少し待機
                std::this_thread::sleep_for(std::chrono::milliseconds(2));
                continue;  // タイムアウト、再試行
            }
            return make_error_code(WipErrc::io_error);
        }
        
        if (received_bytes < 3) {
            continue;  // パケットが小さすぎる
        }
        
        buffer.resize(received_bytes);
        
        // パケットIDチェック（Python版と同様: 先頭2バイトの下位12ビット, 上位4ビットはversion）
        uint16_t first16 = static_cast<uint16_t>(buffer[0]) | (static_cast<uint16_t>(buffer[1]) << 8);
        uint16_t received_packet_id = static_cast<uint16_t>((first16 >> 4) & 0x0FFFu);
        if (received_packet_id != packet_id) {
            continue;  // 異なるパケットID、無視
        }
        
        // パケットタイプ取得
        uint8_t packet_type = get_packet_type(buffer);
        
        if (packet_type == 5) {  // ReportResponse
            auto response_result = packet::compat::PyReportResponse::from_bytes(buffer);
            if (!response_result.has_value()) {
                return response_result.error();
            }
            
            auto response = response_result.value();
            if (debug_) {
                std::cout << "Received SENSOR REPORT RESPONSE" << std::endl;
            }
            
            if (response.is_success()) {
                ReportResult result;
                result.type = "report_ack";
                result.success = true;
                result.packet_id = response.header.packet_id;
                result.timestamp = response.header.timestamp;
                
                // レスポンス要約を取得（Python版get_response_summary()互換）
                result.summary = response.get_response_summary();
                
                return result;
            } else {
                return make_error_code(WipErrc::invalid_packet);
            }
        }
        else if (packet_type == 7) {  // ErrorResponse
            return handle_error_response(buffer);
        }
        else {
            // 不明なパケットタイプは無視して継続
            continue;
        }
    }
}

ReportResult SimpleReportClient::handle_error_response(const std::vector<uint8_t>& data) {
    ReportResult result;
    result.type = "error";
    result.success = false;

    // ErrorResponse でも Python 互換では固定長フィールド(weather_code)にエラーコードが入る。
    // ヘッダー(16B)直後の2バイトがエラーコードに相当する。
    if (data.size() >= wiplib::proto::kFixedHeaderSize + 2) {
        size_t off = wiplib::proto::kFixedHeaderSize;
        result.error_code = static_cast<uint16_t>(data[off]) | (static_cast<uint16_t>(data[off + 1]) << 8);
    }
    
    if (debug_) {
        std::cout << "Received ERROR RESPONSE" << std::endl;
    }
    
    return result;
}

uint8_t SimpleReportClient::get_packet_type(const std::vector<uint8_t>& data) {
    if (data.size() < wiplib::proto::kFixedHeaderSize) {
        return 0;
    }
    auto h = wiplib::proto::decode_header(std::span<const uint8_t>(data.data(), wiplib::proto::kFixedHeaderSize));
    if (!h.has_value()) {
        return 0;
    }
    return static_cast<uint8_t>(h.value().type);
}

} // namespace wiplib::client

// Python版互換の便利関数

namespace wiplib::client::utils {

std::unique_ptr<SimpleReportClient> create_report_client(
    const std::string& host, 
    uint16_t port, 
    bool debug
) {
    return std::make_unique<SimpleReportClient>(host, port, debug);
}

Result<ReportResult> send_sensor_report(
    const std::string& area_code,
    std::optional<int> weather_code,
    std::optional<float> temperature,
    std::optional<int> precipitation_prob,
    std::optional<std::vector<std::string>> alert,
    std::optional<std::vector<std::string>> disaster,
    const std::string& host,
    uint16_t port,
    bool debug
) {
    try {
        auto client = SimpleReportClient(host, port, debug);
        
        client.set_sensor_data(
            area_code,
            weather_code,
            temperature,
            precipitation_prob,
            alert,
            disaster
        );
        
        return client.send_report_data();
    }
    catch (const std::exception& e) {
        return make_error_code(WipErrc::io_error);
    }
}

} // namespace wiplib::client::utils
