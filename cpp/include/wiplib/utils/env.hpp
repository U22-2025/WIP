#pragma once

#include <optional>
#include <string>

namespace wiplib::utils {

// OSごとの環境変数名の違いを吸収するgetenvラッパー
std::optional<std::string> getenv_os(const std::string& key);

} // namespace wiplib::utils

