#pragma once

#include <cstdint>
#include <span>

namespace wiplib::packet {

/**
 * @brief 12ビットチェックサム計算
 * @param data データバイト配列
 * @return 12ビットチェックサム値
 */
uint16_t calc_checksum12(std::span<const uint8_t> data);

/**
 * @brief 12ビットチェックサム検証
 * @param data データバイト配列
 * @param expected_checksum 期待されるチェックサム値
 * @return チェックサムが一致する場合true
 */
bool verify_checksum12(std::span<const uint8_t> data, uint16_t expected_checksum);

namespace detail {
    /**
     * @brief キャリーフォールド実装（最適化版）
     * @param value 計算対象値
     * @return フォールド後の値
     */
    uint16_t carry_fold(uint32_t value);
}

} // namespace wiplib::packet