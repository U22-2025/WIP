#pragma once

#include "core/core.hpp"
#include "models/Request.hpp"
#include "models/Response.hpp"
#include "types/LocationPacket.hpp"
#include "types/QueryPacket.hpp"
#include "types/ReportPacket.hpp"
#include "types/ErrorResponse.hpp"
#include "debug/DebugLogger.hpp"

namespace wip {
namespace packet {
inline constexpr const char* VERSION = "1.1.0";
} // namespace packet
} // namespace wip
