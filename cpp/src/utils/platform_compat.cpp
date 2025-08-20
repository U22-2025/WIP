#include "wiplib/utils/platform_compat.hpp"
#include <atomic>
#include <mutex>

namespace wiplib::utils {

std::atomic<bool> WinsockInitializer::initialized_{false};
std::mutex WinsockInitializer::mutex_;

}  // namespace wiplib::utils