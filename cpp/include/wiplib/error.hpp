#pragma once

#include <system_error>

namespace wiplib {

enum class WipErrc {
  ok = 0,
  invalid_packet = 1,
  checksum_mismatch = 2,
  io_error = 3,
  timeout = 4,
  not_implemented = 5,
};

class WipErrorCategory final : public std::error_category {
public:
  const char* name() const noexcept override { return "wiplib"; }
  std::string message(int ev) const override {
    switch (static_cast<WipErrc>(ev)) {
      case WipErrc::ok: return "ok";
      case WipErrc::invalid_packet: return "invalid packet";
      case WipErrc::checksum_mismatch: return "checksum mismatch";
      case WipErrc::io_error: return "I/O error";
      case WipErrc::timeout: return "timeout";
      case WipErrc::not_implemented: return "not implemented";
      default: return "unknown error";
    }
  }
};

inline const std::error_category& wip_error_category() {
  static WipErrorCategory cat;
  return cat;
}

inline std::error_code make_error_code(WipErrc e) {
  return {static_cast<int>(e), wip_error_category()};
}

} // namespace wiplib

namespace std {
template<> struct is_error_code_enum<wiplib::WipErrc> : true_type {};
}

