#pragma once

#include <cstdint>
#include <span>

namespace wiplib::packet {

/**
 * @brief 指定したビット範囲を抽出
 * @param data データ
 * @param bit_offset ビットオフセット（0から開始）
 * @param bit_length ビット長
 * @return 抽出されたビット値
 */
uint64_t extract_bits(uint64_t data, uint8_t bit_offset, uint8_t bit_length);

/**
 * @brief バイト配列から指定したビット範囲を抽出
 * @param data バイト配列
 * @param bit_offset ビットオフセット（0から開始）
 * @param bit_length ビット長
 * @return 抽出されたビット値
 */
uint64_t extract_bits(std::span<const uint8_t> data, uint32_t bit_offset, uint8_t bit_length);

/**
 * @brief 指定したビット範囲に値を設定
 * @param data 対象データ
 * @param bit_offset ビットオフセット（0から開始）
 * @param bit_length ビット長
 * @param value 設定する値
 * @return 設定後のデータ
 */
uint64_t set_bits(uint64_t data, uint8_t bit_offset, uint8_t bit_length, uint64_t value);

/**
 * @brief バイト配列の指定したビット範囲に値を設定
 * @param data バイト配列
 * @param bit_offset ビットオフセット（0から開始）
 * @param bit_length ビット長
 * @param value 設定する値
 */
void set_bits(std::span<uint8_t> data, uint32_t bit_offset, uint8_t bit_length, uint64_t value);

/**
 * @brief リトルエンディアン形式で16ビット値を読み取り
 * @param data データポインタ
 * @return 16ビット値
 */
uint16_t read_le16(const uint8_t* data);

/**
 * @brief リトルエンディアン形式で32ビット値を読み取り
 * @param data データポインタ
 * @return 32ビット値
 */
uint32_t read_le32(const uint8_t* data);

/**
 * @brief リトルエンディアン形式で64ビット値を読み取り
 * @param data データポインタ
 * @return 64ビット値
 */
uint64_t read_le64(const uint8_t* data);

/**
 * @brief リトルエンディアン形式で16ビット値を書き込み
 * @param data データポインタ
 * @param value 書き込む値
 */
void write_le16(uint8_t* data, uint16_t value);

/**
 * @brief リトルエンディアン形式で32ビット値を書き込み
 * @param data データポインタ
 * @param value 書き込む値
 */
void write_le32(uint8_t* data, uint32_t value);

/**
 * @brief リトルエンディアン形式で64ビット値を書き込み
 * @param data データポインタ
 * @param value 書き込む値
 */
void write_le64(uint8_t* data, uint64_t value);

} // namespace wiplib::packet