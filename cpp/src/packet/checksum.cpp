#include "wiplib/packet/checksum.hpp"
#include <numeric>

namespace wiplib::packet {

namespace detail {
    uint16_t carry_fold(uint32_t value) {
        // キャリーフォールド: 上位ビットを下位に加算
        while (value > 0xFFFF) {
            value = (value & 0xFFFF) + (value >> 16);
        }
        return static_cast<uint16_t>(value);
    }
}

uint16_t calc_checksum12(std::span<const uint8_t> data) {
    // インターネットチェックサムアルゴリズムを12ビット用に調整
    uint32_t sum = 0;
    
    // 2バイトずつ処理
    for (size_t i = 0; i < data.size(); i += 2) {
        uint16_t word = 0;
        if (i + 1 < data.size()) {
            // ビッグエンディアンで2バイトを結合
            word = (static_cast<uint16_t>(data[i]) << 8) | data[i + 1];
        } else {
            // 奇数バイトの場合、上位バイトのみ
            word = static_cast<uint16_t>(data[i]) << 8;
        }
        sum += word;
    }
    
    // キャリーフォールド
    uint16_t folded = detail::carry_fold(sum);
    
    // 1の補数を取って12ビットにマスク
    uint16_t checksum = (~folded) & 0x0FFF;
    
    return checksum;
}

bool verify_checksum12(std::span<const uint8_t> data, uint16_t expected_checksum) {
    uint16_t calculated = calc_checksum12(data);
    return calculated == expected_checksum;
}

} // namespace wiplib::packet