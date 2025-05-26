"""
bit_utils.py のユニットテスト

ビット操作ユーティリティ関数のテストを行います。
"""

import pytest
import sys
import os

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from wtp.packet.bit_utils import extract_bits, extract_rest_bits
from wtp.packet.exceptions import BitFieldError


class TestExtractBits:
    """extract_bits関数のテストクラス"""
    
    def test_basic_extraction(self):
        """基本的なビット抽出のテスト"""
        # 0b110110 から位置1から3ビット抽出 → 0b11
        result = extract_bits(0b110110, 1, 3)
        assert result == 0b11
        
        # 0b11111111 から位置0から4ビット抽出 → 0b1111
        result = extract_bits(0b11111111, 0, 4)
        assert result == 0b1111
        
        # 0b10101010 から位置2から3ビット抽出 → 0b010
        result = extract_bits(0b10101010, 2, 3)
        assert result == 0b010
    
    def test_single_bit_extraction(self):
        """1ビット抽出のテスト"""
        # 各ビット位置から1ビットずつ抽出
        bitstr = 0b10101010
        
        assert extract_bits(bitstr, 0, 1) == 0  # 最下位ビット
        assert extract_bits(bitstr, 1, 1) == 1
        assert extract_bits(bitstr, 2, 1) == 0
        assert extract_bits(bitstr, 3, 1) == 1
        assert extract_bits(bitstr, 4, 1) == 0
        assert extract_bits(bitstr, 5, 1) == 1
        assert extract_bits(bitstr, 6, 1) == 0
        assert extract_bits(bitstr, 7, 1) == 1  # 最上位ビット
    
    def test_full_width_extraction(self):
        """全ビット幅の抽出テスト"""
        # 8ビット全体を抽出
        bitstr = 0b11010110
        result = extract_bits(bitstr, 0, 8)
        assert result == bitstr
        
        # 16ビット全体を抽出
        bitstr = 0b1101011010101010
        result = extract_bits(bitstr, 0, 16)
        assert result == bitstr
    
    def test_zero_value(self):
        """0からのビット抽出テスト"""
        result = extract_bits(0, 0, 1)
        assert result == 0
        
        result = extract_bits(0, 0, 8)
        assert result == 0
        
        result = extract_bits(0, 5, 3)
        assert result == 0
    
    def test_large_numbers(self):
        """大きな数値からのビット抽出テスト"""
        # 32ビット値
        bitstr = 0xFFFFFFFF
        result = extract_bits(bitstr, 0, 16)
        assert result == 0xFFFF
        
        result = extract_bits(bitstr, 16, 16)
        assert result == 0xFFFF
        
        # 64ビット値
        bitstr = 0x123456789ABCDEF0
        result = extract_bits(bitstr, 0, 8)
        assert result == 0xF0
        
        result = extract_bits(bitstr, 8, 8)
        assert result == 0xDE
    
    def test_boundary_conditions(self):
        """境界条件のテスト"""
        bitstr = 0b11111111
        
        # 開始位置が最後のビット
        result = extract_bits(bitstr, 7, 1)
        assert result == 1
        
        # 長さが1
        result = extract_bits(bitstr, 0, 1)
        assert result == 1
        
        # 開始位置が0
        result = extract_bits(bitstr, 0, 4)
        assert result == 0b1111
    
    def test_invalid_length(self):
        """無効な長さのテスト"""
        with pytest.raises(BitFieldError, match="長さは正の整数である必要があります"):
            extract_bits(0b11111111, 0, 0)
        
        with pytest.raises(BitFieldError, match="長さは正の整数である必要があります"):
            extract_bits(0b11111111, 0, -1)
        
        with pytest.raises(BitFieldError, match="長さは正の整数である必要があります"):
            extract_bits(0b11111111, 0, -5)
    
    def test_docstring_example(self):
        """ドキュメント文字列の例のテスト"""
        # >>> extract_bits(0b110110, 1, 3)
        # 0b11
        result = extract_bits(0b110110, 1, 3)
        assert result == 0b11
    
    def test_mask_behavior(self):
        """マスク動作の詳細テスト"""
        # ビットマスクが正しく適用されることを確認
        bitstr = 0b11111111
        
        # 3ビット抽出 → マスク 0b111
        result = extract_bits(bitstr, 0, 3)
        assert result == 0b111
        
        # 4ビット抽出 → マスク 0b1111
        result = extract_bits(bitstr, 0, 4)
        assert result == 0b1111
        
        # 上位ビットが正しく除去されることを確認
        bitstr = 0b11110000
        result = extract_bits(bitstr, 0, 4)
        assert result == 0b0000  # 下位4ビットは0


class TestExtractRestBits:
    """extract_rest_bits関数のテストクラス"""
    
    def test_basic_rest_extraction(self):
        """基本的な残りビット抽出のテスト"""
        # 0b110110 から位置2以降 → 0b1101
        result = extract_rest_bits(0b110110, 2)
        assert result == 0b1101
        
        # 0b11111111 から位置4以降 → 0b1111
        result = extract_rest_bits(0b11111111, 4)
        assert result == 0b1111
    
    def test_start_position_zero(self):
        """開始位置0のテスト（全ビット取得）"""
        bitstr = 0b10101010
        result = extract_rest_bits(bitstr, 0)
        assert result == bitstr
        
        bitstr = 0b11111111
        result = extract_rest_bits(bitstr, 0)
        assert result == bitstr
    
    def test_start_position_beyond_bits(self):
        """ビット長を超えた開始位置のテスト"""
        bitstr = 0b1111  # 4ビット
        
        # 開始位置がビット長と同じ
        result = extract_rest_bits(bitstr, 4)
        assert result == 0
        
        # 開始位置がビット長を超える
        result = extract_rest_bits(bitstr, 10)
        assert result == 0
    
    def test_single_bit_shifts(self):
        """1ビットずつシフトするテスト"""
        bitstr = 0b11110000
        
        assert extract_rest_bits(bitstr, 0) == 0b11110000
        assert extract_rest_bits(bitstr, 1) == 0b1111000
        assert extract_rest_bits(bitstr, 2) == 0b111100
        assert extract_rest_bits(bitstr, 3) == 0b11110
        assert extract_rest_bits(bitstr, 4) == 0b1111
        assert extract_rest_bits(bitstr, 5) == 0b111
        assert extract_rest_bits(bitstr, 6) == 0b11
        assert extract_rest_bits(bitstr, 7) == 0b1
        assert extract_rest_bits(bitstr, 8) == 0b0
    
    def test_zero_value(self):
        """0からの残りビット抽出テスト"""
        result = extract_rest_bits(0, 0)
        assert result == 0
        
        result = extract_rest_bits(0, 5)
        assert result == 0
        
        result = extract_rest_bits(0, 100)
        assert result == 0
    
    def test_large_numbers(self):
        """大きな数値からの残りビット抽出テスト"""
        # 32ビット値
        bitstr = 0x12345678
        result = extract_rest_bits(bitstr, 16)
        assert result == 0x1234
        
        # 64ビット値
        bitstr = 0x123456789ABCDEF0
        result = extract_rest_bits(bitstr, 32)
        assert result == 0x12345678
    
    def test_docstring_example(self):
        """ドキュメント文字列の例のテスト"""
        # >>> extract_rest_bits(0b110110, 2)
        # 0b1101
        result = extract_rest_bits(0b110110, 2)
        assert result == 0b1101
    
    def test_right_shift_behavior(self):
        """右シフト動作の詳細テスト"""
        bitstr = 0b10101010
        
        # 各位置での右シフト結果を確認
        for i in range(9):  # 0から8まで
            expected = bitstr >> i
            result = extract_rest_bits(bitstr, i)
            assert result == expected, f"Position {i}: expected {expected:b}, got {result:b}"


class TestBitUtilsIntegration:
    """ビットユーティリティ関数の統合テスト"""
    
    def test_extract_and_rest_combination(self):
        """extract_bitsとextract_rest_bitsの組み合わせテスト"""
        bitstr = 0b11110000
        
        # 下位4ビットを抽出
        lower = extract_bits(bitstr, 0, 4)
        assert lower == 0b0000
        
        # 上位4ビットを抽出（残りビット使用）
        upper = extract_rest_bits(bitstr, 4)
        assert upper == 0b1111
        
        # 再構成
        reconstructed = (upper << 4) | lower
        assert reconstructed == bitstr
    
    def test_field_extraction_simulation(self):
        """実際のフィールド抽出をシミュレート"""
        # パケットヘッダーのようなビット構造をシミュレート
        # version(4bit) + packet_id(12bit) + type(3bit) + flags(13bit)
        version = 0b1010      # 4ビット
        packet_id = 0b110011001100  # 12ビット
        type_field = 0b101    # 3ビット
        flags = 0b1010101010101  # 13ビット
        
        # ビット列を構成
        bitstr = (version << 28) | (packet_id << 16) | (type_field << 13) | flags
        
        # フィールドを抽出
        extracted_version = extract_bits(bitstr, 28, 4)
        extracted_packet_id = extract_bits(bitstr, 16, 12)
        extracted_type = extract_bits(bitstr, 13, 3)
        extracted_flags = extract_bits(bitstr, 0, 13)
        
        # 検証
        assert extracted_version == version
        assert extracted_packet_id == packet_id
        assert extracted_type == type_field
        assert extracted_flags == flags
    
    def test_performance_patterns(self):
        """パフォーマンステスト用のパターン"""
        # 大きなビット列での動作確認
        large_bitstr = 0xFFFFFFFFFFFFFFFF  # 64ビット全て1
        
        # 様々な位置とサイズでの抽出
        test_cases = [
            (0, 8), (8, 8), (16, 8), (24, 8),
            (32, 8), (40, 8), (48, 8), (56, 8),
            (0, 16), (16, 16), (32, 16), (48, 16),
            (0, 32), (32, 32)
        ]
        
        for start, length in test_cases:
            result = extract_bits(large_bitstr, start, length)
            expected = (1 << length) - 1  # 指定長の全て1
            assert result == expected
    
    def test_edge_case_combinations(self):
        """エッジケースの組み合わせテスト"""
        # 最小値
        assert extract_bits(1, 0, 1) == 1
        assert extract_rest_bits(1, 0) == 1
        
        # 単一ビット
        assert extract_bits(1, 0, 1) == 1
        assert extract_bits(1, 1, 1) == 0
        
        # 境界での動作
        bitstr = 0b10000000  # 最上位ビットのみ1
        assert extract_bits(bitstr, 7, 1) == 1
        assert extract_bits(bitstr, 0, 7) == 0
        assert extract_rest_bits(bitstr, 7) == 1
