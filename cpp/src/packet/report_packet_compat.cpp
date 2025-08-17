#include "wiplib/packet/report_packet_compat.hpp"
#include "wiplib/packet/bit_utils.hpp"
#include "wiplib/packet/checksum.hpp"
#include "wiplib/utils/auth.hpp"

#include <random>
#include <iomanip>
#include <sstream>
#include <ctime>
#include <mutex>

namespace wiplib::packet::compat {

// PySensorData implementation
std::string PySensorData::normalize_area_code(const std::string& area_code) {
    if (area_code.length() >= 6) {
        return area_code.substr(0, 6);
    }
    // 6桁に0埋め
    std::string padded = area_code;
    while (padded.length() < 6) {
        padded = "0" + padded;
    }
    return padded;
}

std::string PySensorData::normalize_area_code(int area_code) {
    std::ostringstream oss;
    oss << std::setw(6) << std::setfill('0') << area_code;
    return oss.str();
}

std::unordered_map<std::string, std::string> PySensorData::to_dict() const {
    std::unordered_map<std::string, std::string> result;
    
    if (area_code) {
        result["area_code"] = *area_code;
    }
    if (weather_code) {
        result["weather_code"] = std::to_string(*weather_code);
    }
    if (temperature) {
        result["temperature"] = std::to_string(*temperature);
    }
    if (precipitation_prob) {
        result["precipitation_prob"] = std::to_string(*precipitation_prob);
    }
    
    // alert と disaster は配列なので特別処理
    if (alert && !alert->empty()) {
        std::ostringstream oss;
        for (size_t i = 0; i < alert->size(); ++i) {
            if (i > 0) oss << ",";
            oss << (*alert)[i];
        }
        result["alert"] = oss.str();
    }
    
    if (disaster && !disaster->empty()) {
        std::ostringstream oss;
        for (size_t i = 0; i < disaster->size(); ++i) {
            if (i > 0) oss << ",";
            oss << (*disaster)[i];
        }
        result["disaster"] = oss.str();
    }
    
    return result;
}

bool PySensorData::is_empty() const {
    return !area_code && !weather_code && !temperature && 
           !precipitation_prob && !alert && !disaster;
}

void PySensorData::clear() {
    area_code.reset();
    weather_code.reset();
    temperature.reset();
    precipitation_prob.reset();
    alert.reset();
    disaster.reset();
}

// PyReportRequest implementation
PyReportRequest PyReportRequest::create_sensor_data_report(
    const std::string& area_code,
    std::optional<int> weather_code,
    std::optional<float> temperature,
    std::optional<int> precipitation_prob,
    std::optional<std::vector<std::string>> alert,
    std::optional<std::vector<std::string>> disaster,
    uint8_t version
) {
    PyReportRequest request;
    
    // ヘッダー設定
    request.header.version = version;
    request.header.packet_id = 0; // 後でパケットIDジェネレーターで設定
    request.header.type = proto::PacketType::ReportRequest; // Type 4
    request.header.day = 0; // リアルタイムデータ
    request.header.timestamp = py_utils::current_unix_timestamp();
    
    // エリアコードを正規化して数値に変換
    std::string normalized_area = PySensorData::normalize_area_code(area_code);
    request.header.area_code = static_cast<uint32_t>(std::stoul(normalized_area));
    
    // センサーデータ設定
    request.sensor_data.area_code = normalized_area;
    request.sensor_data.weather_code = weather_code;
    request.sensor_data.temperature = temperature;
    request.sensor_data.precipitation_prob = precipitation_prob;
    request.sensor_data.alert = alert;
    request.sensor_data.disaster = disaster;
    
    // フラグを計算
    request.calculate_flags();
    
    return request;
}

void PyReportRequest::enable_auth(const std::string& passphrase) {
    auth_enabled = true;
    auth_passphrase = passphrase;
}

void PyReportRequest::set_auth_flags() {
    if (auth_enabled) {
        // 認証フラグを設定（具体的なビット位置は既存の認証実装に合わせる）
        header.flags.auth_enabled = true;
    }
}

void PyReportRequest::calculate_flags() {
    // データが設定されているかでフラグを決定（Python版と同様）
    header.flags.weather = sensor_data.weather_code.has_value();
    header.flags.temperature = sensor_data.temperature.has_value();
    header.flags.precipitation = sensor_data.precipitation_prob.has_value();
    header.flags.alert = sensor_data.alert.has_value() && !sensor_data.alert->empty();
    header.flags.disaster = sensor_data.disaster.has_value() && !sensor_data.disaster->empty();
    header.flags.extended = header.flags.alert || header.flags.disaster;
}

std::vector<proto::ExtendedField> PyReportRequest::build_extended_fields() const {
    std::vector<proto::ExtendedField> fields;
    
    // alert情報
    if (sensor_data.alert && !sensor_data.alert->empty()) {
        proto::ExtendedField alert_field;
        alert_field.data_type = 0x10; // alert type
        
        // 文字列リストをバイト列に変換
        std::ostringstream oss;
        for (size_t i = 0; i < sensor_data.alert->size(); ++i) {
            if (i > 0) oss << "\n";
            oss << (*sensor_data.alert)[i];
        }
        std::string alert_str = oss.str();
        alert_field.data.assign(alert_str.begin(), alert_str.end());
        
        fields.push_back(alert_field);
    }
    
    // disaster情報
    if (sensor_data.disaster && !sensor_data.disaster->empty()) {
        proto::ExtendedField disaster_field;
        disaster_field.data_type = 0x11; // disaster type
        
        // 文字列リストをバイト列に変換
        std::ostringstream oss;
        for (size_t i = 0; i < sensor_data.disaster->size(); ++i) {
            if (i > 0) oss << "\n";
            oss << (*sensor_data.disaster)[i];
        }
        std::string disaster_str = oss.str();
        disaster_field.data.assign(disaster_str.begin(), disaster_str.end());
        
        fields.push_back(disaster_field);
    }
    
    return fields;
}

std::vector<uint8_t> PyReportRequest::to_bytes() const {
    // パケットを proto::Packet 形式に変換してエンコード
    proto::Packet packet;
    packet.header = header;
    
    // レスポンスフィールドは Type 4 では不要
    
    // 拡張フィールドを設定
    packet.extensions = build_extended_fields();
    
    // 既存のcodec実装を使用してエンコード
    // TODO: codec実装との統合が必要
    std::vector<uint8_t> result;
    // 仮実装：基本的なヘッダーのみエンコード
    result.resize(16); // 基本ヘッダーサイズ
    
    // ヘッダーフィールドの設定（ビット操作）
    result[0] = (header.version & 0x0F) | ((header.packet_id & 0x0F) << 4);
    result[1] = (header.packet_id >> 4) & 0xFF;
    result[2] = (static_cast<uint8_t>(header.type) & 0x07) | 
                (header.flags.weather ? 0x08 : 0) |
                (header.flags.temperature ? 0x10 : 0) |
                (header.flags.precipitation ? 0x20 : 0) |
                (header.flags.alert ? 0x40 : 0) |
                (header.flags.disaster ? 0x80 : 0);
    
    // タイムスタンプ（8バイト、リトルエンディアン）
    for (int i = 0; i < 8; ++i) {
        result[4 + i] = static_cast<uint8_t>((header.timestamp >> (i * 8)) & 0xFF);
    }
    
    // エリアコード（4バイト、リトルエンディアン）
    for (int i = 0; i < 4; ++i) {
        result[12 + i] = static_cast<uint8_t>((header.area_code >> (i * 8)) & 0xFF);
    }
    
    // チェックサムを計算して設定（最後の2バイト）
    uint16_t checksum = calc_checksum12(std::span<const uint8_t>(result.data(), 14));
    result[14] = checksum & 0xFF;
    result[15] = (checksum >> 8) & 0xFF;
    
    return result;
}

wiplib::Result<PyReportRequest> PyReportRequest::from_bytes(std::span<const uint8_t> data) {
    if (data.size() < 16) {
        return std::make_error_code(std::errc::invalid_argument);
    }
    
    PyReportRequest request;
    
    // ヘッダーのデコード
    request.header.version = data[0] & 0x0F;
    request.header.packet_id = ((data[0] >> 4) & 0x0F) | (data[1] << 4);
    request.header.type = static_cast<proto::PacketType>(data[2] & 0x07);
    
    // フラグのデコード
    request.header.flags.weather = (data[2] & 0x08) != 0;
    request.header.flags.temperature = (data[2] & 0x10) != 0;
    request.header.flags.precipitation = (data[2] & 0x20) != 0;
    request.header.flags.alert = (data[2] & 0x40) != 0;
    request.header.flags.disaster = (data[2] & 0x80) != 0;
    
    // タイムスタンプのデコード
    uint64_t timestamp = 0;
    for (int i = 0; i < 8; ++i) {
        timestamp |= static_cast<uint64_t>(data[4 + i]) << (i * 8);
    }
    request.header.timestamp = timestamp;
    
    // エリアコードのデコード
    uint32_t area_code = 0;
    for (int i = 0; i < 4; ++i) {
        area_code |= static_cast<uint32_t>(data[12 + i]) << (i * 8);
    }
    request.header.area_code = area_code;
    request.sensor_data.area_code = PySensorData::normalize_area_code(static_cast<int>(area_code));
    
    // チェックサムのデコード
    request.header.checksum = data[14] | (data[15] << 8);
    
    // チェックサムの検証
    uint16_t calculated_checksum = calc_checksum12(std::span<const uint8_t>(data.data(), 14));
    if (calculated_checksum != request.header.checksum) {
        return std::make_error_code(std::errc::bad_message);
    }
    
    // TODO: 拡張フィールドのデコード実装
    
    return request;
}

bool PyReportRequest::validate() const {
    // 基本的な検証
    if (header.version == 0 || header.version > 15) {
        return false;
    }
    
    if (header.type != proto::PacketType::ReportRequest) {
        return false;
    }
    
    if (!sensor_data.area_code || sensor_data.area_code->length() != 6) {
        return false;
    }
    
    // 気温の範囲チェック（-100℃ 〜 +100℃）
    if (sensor_data.temperature && 
        (*sensor_data.temperature < -100.0f || *sensor_data.temperature > 100.0f)) {
        return false;
    }
    
    // 降水確率の範囲チェック（0-100%）
    if (sensor_data.precipitation_prob && 
        (*sensor_data.precipitation_prob < 0 || *sensor_data.precipitation_prob > 100)) {
        return false;
    }
    
    return true;
}

// PyReportResponse implementation
PyReportResponse PyReportResponse::create_ack_response(
    const PyReportRequest& request,
    uint8_t version
) {
    PyReportResponse response;
    
    // ヘッダー設定
    response.header.version = version;
    response.header.packet_id = request.header.packet_id; // 同じパケットID
    response.header.type = proto::PacketType::ReportResponse; // Type 5
    response.header.day = request.header.day;
    response.header.timestamp = py_utils::current_unix_timestamp();
    response.header.area_code = request.header.area_code;
    
    // リクエストのフラグを反映
    response.header.flags = request.header.flags;
    
    // レスポンスフィールド（通常は空）
    response.response_fields.weather_code = 0;
    response.response_fields.temperature = 0; // 0℃相当
    response.response_fields.precipitation_prob = 0;
    
    return response;
}

PyReportResponse PyReportResponse::create_data_response(
    const PyReportRequest& request,
    const std::unordered_map<std::string, std::string>& sensor_data,
    uint8_t version
) {
    PyReportResponse response = create_ack_response(request, version);
    
    // センサーデータを設定
    if (request.header.flags.weather && sensor_data.count("weather_code")) {
        response.response_fields.weather_code = static_cast<uint16_t>(
            std::stoi(sensor_data.at("weather_code"))
        );
    }
    
    if (request.header.flags.temperature && sensor_data.count("temperature")) {
        float temp_celsius = std::stof(sensor_data.at("temperature"));
        response.response_fields.temperature = py_utils::celsius_to_internal(temp_celsius);
    }
    
    if (request.header.flags.precipitation && sensor_data.count("precipitation_prob")) {
        response.response_fields.precipitation_prob = static_cast<uint8_t>(
            std::stoi(sensor_data.at("precipitation_prob"))
        );
    }
    
    return response;
}

std::vector<uint8_t> PyReportResponse::to_bytes() const {
    // PyReportRequestと同様の実装
    // TODO: 完全な実装が必要
    std::vector<uint8_t> result(16);
    
    // 基本ヘッダーのエンコード（仮実装）
    result[0] = (header.version & 0x0F) | ((header.packet_id & 0x0F) << 4);
    result[1] = (header.packet_id >> 4) & 0xFF;
    result[2] = (static_cast<uint8_t>(header.type) & 0x07) | 
                (header.flags.weather ? 0x08 : 0) |
                (header.flags.temperature ? 0x10 : 0) |
                (header.flags.precipitation ? 0x20 : 0) |
                (header.flags.alert ? 0x40 : 0) |
                (header.flags.disaster ? 0x80 : 0);
    
    // タイムスタンプとエリアコードの設定
    for (int i = 0; i < 8; ++i) {
        result[4 + i] = static_cast<uint8_t>((header.timestamp >> (i * 8)) & 0xFF);
    }
    
    for (int i = 0; i < 4; ++i) {
        result[12 + i] = static_cast<uint8_t>((header.area_code >> (i * 8)) & 0xFF);
    }
    
    // チェックサム計算
    uint16_t checksum = calc_checksum12(std::span<const uint8_t>(result.data(), 14));
    result[14] = checksum & 0xFF;
    result[15] = (checksum >> 8) & 0xFF;
    
    return result;
}

wiplib::Result<PyReportResponse> PyReportResponse::from_bytes(std::span<const uint8_t> data) {
    if (data.size() < 16) {
        return std::make_error_code(std::errc::invalid_argument);
    }
    
    PyReportResponse response;
    
    // ヘッダーのデコード（PyReportRequestと同様）
    response.header.version = data[0] & 0x0F;
    response.header.packet_id = ((data[0] >> 4) & 0x0F) | (data[1] << 4);
    response.header.type = static_cast<proto::PacketType>(data[2] & 0x07);
    
    // フラグとタイムスタンプ、エリアコードのデコード
    response.header.flags.weather = (data[2] & 0x08) != 0;
    response.header.flags.temperature = (data[2] & 0x10) != 0;
    response.header.flags.precipitation = (data[2] & 0x20) != 0;
    response.header.flags.alert = (data[2] & 0x40) != 0;
    response.header.flags.disaster = (data[2] & 0x80) != 0;
    
    uint64_t timestamp = 0;
    for (int i = 0; i < 8; ++i) {
        timestamp |= static_cast<uint64_t>(data[4 + i]) << (i * 8);
    }
    response.header.timestamp = timestamp;
    
    uint32_t area_code = 0;
    for (int i = 0; i < 4; ++i) {
        area_code |= static_cast<uint32_t>(data[12 + i]) << (i * 8);
    }
    response.header.area_code = area_code;
    
    response.header.checksum = data[14] | (data[15] << 8);
    
    // チェックサム検証
    uint16_t calculated_checksum = calc_checksum12(std::span<const uint8_t>(data.data(), 14));
    if (calculated_checksum != response.header.checksum) {
        return std::make_error_code(std::errc::bad_message);
    }
    
    return response;
}

std::optional<std::tuple<std::string, int>> PyReportResponse::get_source_info() const {
    return source_info;
}

bool PyReportResponse::is_success() const {
    return header.type == proto::PacketType::ReportResponse; // Type 5
}

std::unordered_map<std::string, std::string> PyReportResponse::get_response_summary() const {
    std::unordered_map<std::string, std::string> summary;
    summary["type"] = "report_response";
    summary["success"] = is_success() ? "true" : "false";
    summary["area_code"] = std::to_string(header.area_code);
    summary["packet_id"] = std::to_string(header.packet_id);
    
    if (auto source = get_source_info()) {
        summary["source_ip"] = std::get<0>(*source);
        summary["source_port"] = std::to_string(std::get<1>(*source));
    }
    
    return summary;
}

bool PyReportResponse::validate() const {
    if (header.version == 0 || header.version > 15) {
        return false;
    }
    
    if (header.type != proto::PacketType::ReportResponse) {
        return false;
    }
    
    return true;
}

std::vector<proto::ExtendedField> PyReportResponse::build_extended_fields() const {
    std::vector<proto::ExtendedField> fields;
    
    // 送信元情報を拡張フィールドに追加
    if (source_info) {
        proto::ExtendedField source_field;
        source_field.data_type = 0x20; // source type
        
        auto [ip, port] = *source_info;
        std::string source_str = ip + ":" + std::to_string(port);
        source_field.data.assign(source_str.begin(), source_str.end());
        
        fields.push_back(source_field);
    }
    
    return fields;
}

std::optional<std::tuple<std::string, int>> PyReportResponse::extract_source_info(
    const std::vector<proto::ExtendedField>& extensions
) {
    for (const auto& field : extensions) {
        if (field.data_type == 0x20) { // source type
            std::string source_str(field.data.begin(), field.data.end());
            size_t colon_pos = source_str.find(':');
            if (colon_pos != std::string::npos) {
                std::string ip = source_str.substr(0, colon_pos);
                int port = std::stoi(source_str.substr(colon_pos + 1));
                return std::make_tuple(ip, port);
            }
        }
    }
    return std::nullopt;
}

// PyPacketIDGenerator implementation
PyPacketIDGenerator::PyPacketIDGenerator() {
    std::random_device rd;
    std::mt19937 gen(rd());
    std::uniform_int_distribution<> dis(0, MAX_ID - 1);
    current_ = static_cast<uint16_t>(dis(gen));
}

uint16_t PyPacketIDGenerator::next_id() {
    std::lock_guard<std::mutex> lock(mutex_);
    uint16_t id = current_;
    current_ = (current_ + 1) % MAX_ID;
    return id;
}

// Utility functions
namespace py_utils {
    std::string packet_type_to_string(uint8_t type) {
        switch (type) {
            case 0: return "WeatherRequest";
            case 1: return "WeatherResponse";
            case 2: return "LocationRequest";
            case 3: return "LocationResponse";
            case 4: return "ReportRequest";
            case 5: return "ReportResponse";
            case 6: return "QueryRequest";
            case 7: return "ErrorResponse";
            default: return "Unknown";
        }
    }
    
    uint64_t current_unix_timestamp() {
        return static_cast<uint64_t>(std::time(nullptr));
    }
}

} // namespace wiplib::packet::compat