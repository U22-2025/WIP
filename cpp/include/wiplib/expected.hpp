#pragma once

#include <system_error>
#include <utility>

namespace wiplib {

template<typename T>
class Result {
public:
  Result(const T& value) : ok_(true), value_(value) {}
  Result(T&& value) : ok_(true), value_(std::move(value)) {}
  Result(std::error_code ec) : ok_(false), ec_(ec) {}

  bool has_value() const noexcept { return ok_; }
  explicit operator bool() const noexcept { return ok_; }
  const T& value() const { return value_; }
  T& value() { return value_; }
  const std::error_code& error() const { return ec_; }

private:
  bool ok_ = false;
  T value_{};
  std::error_code ec_{};
};

} // namespace wiplib

