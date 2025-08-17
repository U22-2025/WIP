#pragma once

// Phase 0: 認証プレースホルダー（空実装）
// 本ヘッダは将来の Phase 1 以降で有効化されるヘルパの名前を先行定義します。
// 現時点では一切の動作変更を行わないため、常に no-op を返します。

#include <string>
#include "wiplib/packet/packet.hpp"

namespace wiplib::utils {

// 将来の本実装では、パケットに auth_hash (ext id=4, hex-UTF8) を付与し、
// header.flags.extended を立てます。Phase 0 では変更なし（false を返す）。
inline bool attach_auth_hash(wiplib::proto::Packet& /*packet*/, const std::string& /*passphrase*/) {
    return false; // no-op in Phase 0
}

} // namespace wiplib::utils

