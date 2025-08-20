#include "wiplib/client/utils/receive_with_id.hpp"
#include "wiplib/packet/codec.hpp"
#include "wiplib/utils/platform_compat.hpp"
#include <cstring>
#include <future>

namespace wiplib::client::utils {

ReceiveWithId::ReceiveWithId(int socket_fd, bool enable_ordering)
    : socket_fd_(socket_fd), enable_ordering_(enable_ordering) {}

ReceiveWithId::~ReceiveWithId() { stop_streaming(); running_ = false; }

packet::GenericResponse ReceiveWithId::receive_sync(uint16_t packet_id, std::chrono::milliseconds timeout) {
    // Set SO_RCVTIMEO temporarily
    struct timeval tv; 
    tv.tv_sec = static_cast<long>(timeout.count() / 1000);
    tv.tv_usec = static_cast<suseconds_t>((timeout.count() % 1000) * 1000);
    wiplib::utils::platform_setsockopt(socket_fd_, SOL_SOCKET, SO_RCVTIMEO, &tv, sizeof(tv));

    for (;;) {
        std::uint8_t buf[2048];
        ssize_t r = wiplib::utils::platform_recv(socket_fd_, buf, sizeof(buf), 0);
        if (r < 0) {
            int error = platform_socket_error();
            if (error == EAGAIN || error == EWOULDBLOCK) {
                stats_.timeout_receives++;
                throw ReceiveTimeoutException(packet_id);
            }
            continue;
        }
        stats_.bytes_received += static_cast<uint64_t>(r);
        auto res = wiplib::proto::decode_packet(std::span<const std::uint8_t>(buf, static_cast<size_t>(r)));
        if (!res) { stats_.corrupted_packets++; continue; }
        const auto& p = res.value();
        if (p.header.packet_id == (packet_id & 0x0FFFu)) {
            stats_.successful_receives++;
            return packet::GenericResponse::decode(std::span<const std::uint8_t>(buf, static_cast<size_t>(r))).value();
        }
        stats_.duplicate_packets++; // treat as not matching for simplicity
    }
}

std::future<packet::GenericResponse> ReceiveWithId::receive_async(uint16_t packet_id, std::chrono::milliseconds timeout) {
    return std::async(std::launch::async, [this, packet_id, timeout]() {
        return this->receive_sync(packet_id, timeout);
    });
}

void ReceiveWithId::receive_with_callback(uint16_t packet_id, ReceiveCallback callback, std::chrono::milliseconds timeout) {
    std::thread([this, packet_id, cb = std::move(callback), timeout]() mutable {
        try {
            auto r = this->receive_sync(packet_id, timeout);
            cb(r, true, "");
        } catch (const std::exception& e) {
            cb(packet::GenericResponse{packet_id}, false, e.what());
        }
    }).detach();
}

MultiPacketResult ReceiveWithId::receive_multiple(const std::vector<uint16_t>& packet_ids, std::chrono::milliseconds timeout, bool /*partial_results*/) {
    MultiPacketResult out{};
    auto start = std::chrono::steady_clock::now();
    for (auto pid : packet_ids) {
        try {
            out.responses.push_back(receive_sync(pid, timeout));
            out.successful_count++;
        } catch (const std::exception& e) {
            out.failed_count++;
            out.error_messages.emplace_back(e.what());
        }
    }
    out.total_time = std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::steady_clock::now() - start);
    return out;
}

void ReceiveWithId::start_streaming(ReceiveCallback callback, std::function<bool(const packet::GenericResponse&)> filter_func) {
    streaming_callback_ = std::move(callback);
    streaming_filter_ = std::move(filter_func);
    streaming_ = true;
    receive_thread_ = std::make_unique<std::thread>(&ReceiveWithId::receive_loop, this);
}

void ReceiveWithId::stop_streaming() {
    streaming_ = false;
    if (receive_thread_ && receive_thread_->joinable()) receive_thread_->join();
}

bool ReceiveWithId::cancel_receive(uint16_t) { return false; }
void ReceiveWithId::cancel_all_receives() {}

void ReceiveWithId::set_duplicate_detection(bool enabled, size_t window_size) {
    duplicate_detection_enabled_ = enabled;
    duplicate_window_size_ = window_size;
}

void ReceiveWithId::set_receive_buffer_size(size_t size) { receive_buffer_size_ = size; }
ReceiveStats ReceiveWithId::get_statistics() const { return stats_; }
size_t ReceiveWithId::get_pending_receive_count() const { return pending_receives_.size(); }
void ReceiveWithId::set_debug_enabled(bool enabled) { debug_enabled_ = enabled; }

void ReceiveWithId::receive_loop() {
    while (streaming_) {
        auto resp = receive_single_packet();
        process_received_packet(resp);
    }
}

packet::GenericResponse ReceiveWithId::receive_single_packet() {
    std::vector<std::uint8_t> buf(receive_buffer_size_);
    ssize_t r = wiplib::utils::platform_recv(socket_fd_, buf.data(), buf.size(), 0);
    if (r <= 0) return packet::GenericResponse{0};
    buf.resize(static_cast<size_t>(r));
    auto res = wiplib::proto::decode_packet(buf);
    if (!res) { stats_.corrupted_packets++; return packet::GenericResponse{0}; }
    auto gr = packet::GenericResponse::decode(buf);
    return gr.value();
}

void ReceiveWithId::process_received_packet(const packet::GenericResponse& response) {
    if (streaming_callback_) {
        if (!streaming_filter_ || streaming_filter_(response)) {
            streaming_callback_(response, true, "");
        }
    }
}

void ReceiveWithId::handle_ordered_packet(const packet::GenericResponse&) {}
void ReceiveWithId::deliver_packet(const packet::GenericResponse&) {}
bool ReceiveWithId::is_duplicate_packet(uint16_t) { return false; }
void ReceiveWithId::record_packet_id(uint16_t) {}
void ReceiveWithId::cleanup_expired_receives() {}
void ReceiveWithId::log_debug(const std::string&) {}

} // namespace wiplib::client::utils
