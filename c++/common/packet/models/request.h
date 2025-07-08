#ifndef COMMON_PACKET_MODELS_REQUEST_H
#define COMMON_PACKET_MODELS_REQUEST_H

#include "../core/format.h"

namespace common {
namespace packet {
namespace models {
using namespace core;

class Request : public Format {
public:
    Request() = default;
};

} // namespace models
} // namespace packet
} // namespace common

#endif
