#include <cassert>
#include "../common/packet/core/format_base.h"

int main() {
    using namespace common::packet::core;
    FormatBase f;
    f.version = 3;
    f.packet_id = 1234;
    f.type = 2;

    auto bytes = f.toBytes();
    FormatBase g;
    g.fromBytes(bytes);

    assert(g.version == f.version);
    assert(g.packet_id == f.packet_id);
    assert(g.type == f.type);
    return 0;
}
