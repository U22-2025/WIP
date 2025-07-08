#ifndef COMMON_PACKET_MODELS_RESPONSE_H
#define COMMON_PACKET_MODELS_RESPONSE_H

#include "../core/format.h"

namespace common {
namespace packet {
namespace models {
using namespace core;

class Response : public Format {
public:
    Response() = default;
};

} // namespace models
} // namespace packet
} // namespace common

#endif
