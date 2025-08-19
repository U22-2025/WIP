#include "wiplib/packet/request.hpp"
#include "wiplib/packet/codec.hpp"
#include <random>

namespace wiplib::packet {

GenericRequest::GenericRequest(proto::PacketType type) {
    packet_.header.version = 1;
    packet_.header.type = type;
    packet_.header.packet_id = 0;
    packet_.header.day = 0;
}

void GenericRequest::set_header(uint16_t packet_id, proto::PacketType type, uint32_t area_code) {
    packet_.header.version = 1;
    packet_.header.packet_id = static_cast<uint16_t>(packet_id & 0x0FFFu);
    packet_.header.type = type;
    packet_.header.area_code = (area_code & 0xFFFFFu);
}

void GenericRequest::set_flags(proto::Flags flags) {
    packet_.header.flags = flags;
}

void GenericRequest::set_day_offset(uint8_t day) {
    packet_.header.day = static_cast<uint8_t>(day & 0x07u);
}

void GenericRequest::set_current_timestamp() {
    using namespace std::chrono;
    packet_.header.timestamp = static_cast<uint64_t>(duration_cast<seconds>(system_clock::now().time_since_epoch()).count());
}

void GenericRequest::set_timestamp(uint64_t timestamp) {
    packet_.header.timestamp = timestamp;
}

void GenericRequest::add_extended_field(const proto::ExtendedField& field) {
    packet_.extensions.push_back(field);
    packet_.header.flags.extended = true;
}

void GenericRequest::set_options(const RequestOptions& options) {
    options_ = options;
}

void GenericRequest::add_metadata(const std::string& key, const std::string& value) {
    metadata_[key] = value;
}

void GenericRequest::calculate_and_set_checksum() {
    // No-op: checksum is computed during encode_packet()
}

std::vector<uint8_t> GenericRequest::encode() const {
    auto res = proto::encode_packet(packet_);
    if (!res) return {};
    return res.value();
}

bool GenericRequest::validate() const {
    // Minimal validation: version and packet_id range
    if (packet_.header.version != 1) return false;
    if ((packet_.header.packet_id & ~0x0FFFu) != 0) return false;
    return true;
}

bool GenericRequest::is_timed_out() const {
    return get_elapsed_time() > options_.timeout;
}

std::chrono::milliseconds GenericRequest::get_elapsed_time() const {
    return std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::steady_clock::now() - creation_time_);
}

// request_utils
uint16_t request_utils::generate_packet_id() {
    static std::mt19937 rng{std::random_device{}()};
    return static_cast<uint16_t>(rng() & 0x0FFFu);
}

bool request_utils::validate_area_code(uint32_t area_code) {
    return (area_code <= 0xFFFFFu);
}

std::chrono::milliseconds request_utils::calculate_timeout(std::chrono::milliseconds base_timeout, uint8_t retry_count) {
    using ms = std::chrono::milliseconds;
    auto mult = static_cast<uint64_t>(retry_count + 1);
    auto computed = ms(base_timeout.count() * mult);
    auto cap = ms(120000);
    return (computed > cap) ? cap : computed;
}

std::string request_utils::generate_correlation_id() {
    static std::mt19937 rng{std::random_device{}()};
    static const char* hex = "0123456789abcdef";
    std::string s(16, '0');
    for (char& c : s) { c = hex[rng() & 0xF]; }
    return s;
}

bool request_utils::is_duplicate_request(const GenericRequest& r1, const GenericRequest& r2) {
    const auto& h1 = r1.get_header();
    const auto& h2 = r2.get_header();
    return h1.packet_id == h2.packet_id && h1.type == h2.type && h1.area_code == h2.area_code;
}

} // namespace wiplib::packet

