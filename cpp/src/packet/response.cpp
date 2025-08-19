#include "wiplib/packet/response.hpp"
#include "wiplib/packet/codec.hpp"

namespace wiplib::packet {

GenericResponse::GenericResponse(uint16_t request_packet_id) {
    packet_.header.version = 1;
    packet_.header.packet_id = static_cast<uint16_t>(request_packet_id & 0x0FFFu);
}

void GenericResponse::set_request_packet_id(uint16_t request_packet_id) {
    packet_.header.packet_id = static_cast<uint16_t>(request_packet_id & 0x0FFFu);
}

void GenericResponse::set_header(proto::PacketType type, uint32_t area_code) {
    packet_.header.type = type;
    packet_.header.area_code = (area_code & 0xFFFFFu);
}

void GenericResponse::set_response_fields(const proto::ResponseFields& fields) {
    packet_.response_fields = fields;
}

void GenericResponse::set_flags(proto::Flags flags) {
    packet_.header.flags = flags;
}

void GenericResponse::set_current_timestamp() {
    using namespace std::chrono;
    packet_.header.timestamp = static_cast<uint64_t>(duration_cast<seconds>(system_clock::now().time_since_epoch()).count());
}

void GenericResponse::set_timestamp(uint64_t timestamp) {
    packet_.header.timestamp = timestamp;
}

void GenericResponse::add_extended_field(const proto::ExtendedField& field) {
    packet_.extensions.push_back(field);
    packet_.header.flags.extended = true;
}

void GenericResponse::set_response_info(const ResponseInfo& info) {
    response_info_ = info;
}

void GenericResponse::set_data_quality(const DataQuality& quality) {
    data_quality_ = quality;
}

void GenericResponse::add_metadata(const std::string& key, const std::string& value) {
    metadata_[key] = value;
}

void GenericResponse::calculate_and_set_checksum() {
    // No-op: checksum set by codec during encode.
}

std::vector<uint8_t> GenericResponse::encode() const {
    auto res = proto::encode_packet(packet_);
    if (!res) return {};
    return res.value();
}

std::optional<GenericResponse> GenericResponse::decode(std::span<const uint8_t> data) {
    auto res = proto::decode_packet(data);
    if (!res) return std::nullopt;
    GenericResponse gr{res.value().header.packet_id};
    gr.packet_ = res.value();
    return gr;
}

bool GenericResponse::validate() const {
    if (packet_.header.version != 1) return false;
    if ((packet_.header.packet_id & ~0x0FFFu) != 0) return false;
    return true;
}

bool GenericResponse::is_success() const {
    return packet_.response_fields.has_value();
}

bool GenericResponse::has_error() const {
    return false; // Placeholder: no explicit error field in proto
}

std::chrono::milliseconds GenericResponse::get_age() const {
    return std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::steady_clock::now() - creation_time_);
}

// response_utils
std::string response_utils::status_to_string(ResponseStatus status) {
    switch (status) {
        case ResponseStatus::Success: return "Success";
        case ResponseStatus::PartialSuccess: return "PartialSuccess";
        case ResponseStatus::Warning: return "Warning";
        case ResponseStatus::Error: return "Error";
        case ResponseStatus::Timeout: return "Timeout";
        case ResponseStatus::Retry: return "Retry";
    }
    return "Unknown";
}

double response_utils::calculate_quality_score(const DataQuality& q) {
    // Simple average normalized
    double acc = q.accuracy / 255.0;
    double fr = q.freshness / 255.0;
    double comp = q.completeness / 255.0;
    return (acc + fr + comp) / 3.0;
}

uint8_t response_utils::evaluate_performance(uint64_t processing_time_us) {
    if (processing_time_us == 0) return 100;
    if (processing_time_us < 1000) return 100;
    if (processing_time_us < 5000) return 80;
    if (processing_time_us < 20000) return 60;
    return 40;
}

std::string response_utils::load_to_string(uint16_t load) {
    if (load < 20000) return "Low";
    if (load < 40000) return "Moderate";
    if (load < 60000) return "High";
    return "Critical";
}

bool response_utils::is_cacheable(const GenericResponse& response) {
    return response.get_response_fields().has_value();
}

std::chrono::seconds response_utils::calculate_ttl(const GenericResponse& /*response*/) {
    return std::chrono::seconds{300};
}

} // namespace wiplib::packet

