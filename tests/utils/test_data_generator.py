"""
テストデータ生成ユーティリティ

様々なテストシナリオ用のデータを生成します。
"""

import random
import string
from typing import Dict, Any, List, Tuple
from datetime import datetime, timedelta


class TestDataGenerator:
    """テストデータ生成クラス"""
    
    @staticmethod
    def generate_random_packet_data(seed: int = None) -> Dict[str, Any]:
        """ランダムなパケットデータを生成"""
        if seed is not None:
            random.seed(seed)
        
        return {
            'version': random.randint(0, 15),
            'packet_id': random.randint(0, 4095),
            'type': random.randint(0, 7),
            'weather_flag': random.randint(0, 1),
            'temperature_flag': random.randint(0, 1),
            'pops_flag': random.randint(0, 1),
            'alert_flag': random.randint(0, 1),
            'disaster_flag': random.randint(0, 1),
            'ex_flag': random.randint(0, 1),
            'day': random.randint(0, 7),
            'reserved': random.randint(0, 15),
            'timestamp': int(datetime.now().timestamp()),
            'area_code': random.randint(0, 1048575),
            'checksum': 0  # 自動計算される
        }
    
    @staticmethod
    def generate_boundary_test_cases() -> List[Tuple[str, Dict[str, Any]]]:
        """境界値テストケースを生成"""
        test_cases = []
        
        # 各フィールドの境界値
        boundaries = {
            'version': [0, 15],
            'packet_id': [0, 4095],
            'type': [0, 7],
            'day': [0, 7],
            'reserved': [0, 15],
            'area_code': [0, 1048575],
            'checksum': [0, 4095]
        }
        
        base_data = TestDataGenerator.generate_random_packet_data(42)
        
        for field, values in boundaries.items():
            for value in values:
                test_data = base_data.copy()
                test_data[field] = value
                test_cases.append((f"{field}_{value}", test_data))
        
        return test_cases
    
    @staticmethod
    def generate_extended_field_data(complexity: str = 'simple') -> Dict[str, Any]:
        """拡張フィールドのテストデータを生成"""
        if complexity == 'simple':
            return {
                'alert': ['警報1'],
                'latitude': 35.6895,
                'longitude': 139.6917
            }
        elif complexity == 'medium':
            return {
                'alert': ['津波警報', '大雨警報'],
                'disaster': ['土砂崩れ'],
                'latitude': 35.6895,
                'longitude': 139.6917,
                'source_ip': '192.168.1.1'
            }
        elif complexity == 'complex':
            return {
                'alert': [f'警報{i}' for i in range(10)],
                'disaster': [f'災害{i}' for i in range(5)],
                'latitude': 35.6895,
                'longitude': 139.6917,
                'source_ip': '192.168.1.100'
            }
        else:
            raise ValueError(f"Unknown complexity: {complexity}")
    
    @staticmethod
    def generate_japanese_text_variations() -> List[str]:
        """日本語テキストのバリエーションを生成"""
        return [
            'ひらがな',
            'カタカナ',
            '漢字',
            'ひらがなカタカナ漢字',
            '数字123',
            '記号！？',
            '英数字ABC123',
            '混合テストABC123あいう',
            '長い文字列' * 10,
            ''  # 空文字列
        ]
    
    @staticmethod
    def generate_boundary_values() -> Dict[str, Dict[str, int]]:
        """
        各フィールドの境界値を生成
        
        Returns:
            フィールド名をキーとした境界値辞書
        """
        return {
            'version': {'min': 0, 'max': 15},
            'packet_id': {'min': 0, 'max': 4095},
            'type': {'min': 0, 'max': 7},
            'weather_flag': {'min': 0, 'max': 1},
            'temperature_flag': {'min': 0, 'max': 1},
            'pops_flag': {'min': 0, 'max': 1},
            'alert_flag': {'min': 0, 'max': 1},
            'disaster_flag': {'min': 0, 'max': 1},
            'ex_flag': {'min': 0, 'max': 1},
            'day': {'min': 0, 'max': 7},
            'reserved': {'min': 0, 'max': 15},
            'timestamp': {'min': 0, 'max': 2**64 - 1},
            'area_code': {'min': 0, 'max': 1048575},
            'checksum': {'min': 0, 'max': 4095},
        }
    
    @staticmethod
    def generate_response_packet_data(weather_type: str = 'normal') -> Dict[str, Any]:
        """レスポンスパケット用のテストデータを生成"""
        base_data = TestDataGenerator.generate_random_packet_data(42)
        
        if weather_type == 'normal':
            response_data = {
                'weather_code': 1000,  # 晴れ
                'temperature': 125,    # 25℃
                'pops': 30            # 30%
            }
        elif weather_type == 'storm':
            response_data = {
                'weather_code': 2000,  # 嵐
                'temperature': 120,    # 20℃
                'pops': 90            # 90%
            }
        elif weather_type == 'extreme_cold':
            response_data = {
                'weather_code': 3000,  # 極寒
                'temperature': 0,      # -100℃
                'pops': 0             # 0%
            }
        elif weather_type == 'extreme_hot':
            response_data = {
                'weather_code': 4000,  # 猛暑
                'temperature': 255,    # 155℃
                'pops': 0             # 0%
            }
        else:
            raise ValueError(f"Unknown weather_type: {weather_type}")
        
        base_data.update(response_data)
        return base_data
    
    @staticmethod
    def generate_invalid_data_cases() -> List[Tuple[str, Dict[str, Any], str]]:
        """無効なデータのテストケースを生成"""
        test_cases = []
        base_data = TestDataGenerator.generate_random_packet_data(42)
        
        # 範囲外の値
        invalid_cases = [
            ('version_negative', {'version': -1}, 'version'),
            ('version_too_large', {'version': 16}, 'version'),
            ('packet_id_negative', {'packet_id': -1}, 'packet_id'),
            ('packet_id_too_large', {'packet_id': 4096}, 'packet_id'),
            ('type_negative', {'type': -1}, 'type'),
            ('type_too_large', {'type': 8}, 'type'),
            ('area_code_negative', {'area_code': -1}, 'area_code'),
            ('area_code_too_large', {'area_code': 1048576}, 'area_code'),
        ]
        
        for case_name, invalid_data, field_name in invalid_cases:
            test_data = base_data.copy()
            test_data.update(invalid_data)
            test_cases.append((case_name, test_data, field_name))
        
        return test_cases
    
    @staticmethod
    def generate_large_dataset(count: int = 1000) -> List[Dict[str, Any]]:
        """大量のテストデータセットを生成"""
        datasets = []
        for i in range(count):
            data = TestDataGenerator.generate_random_packet_data(i)
            # 一部に拡張フィールドを追加
            if i % 3 == 0:
                data['ex_flag'] = 1
                data['ex_field'] = TestDataGenerator.generate_extended_field_data('simple')
            elif i % 5 == 0:
                data['ex_flag'] = 1
                data['ex_field'] = TestDataGenerator.generate_extended_field_data('complex')
            
            datasets.append(data)
        
        return datasets
    
    @staticmethod
    def generate_timestamp_variations() -> List[int]:
        """タイムスタンプのバリエーションを生成"""
        now = datetime.now()
        return [
            0,  # Unix epoch
            int(now.timestamp()),  # 現在時刻
            int((now - timedelta(days=365)).timestamp()),  # 1年前
            int((now + timedelta(days=365)).timestamp()),  # 1年後
            2147483647,  # 32bit最大値
            4294967295,  # 32bit unsigned最大値
        ]
    
    @staticmethod
    def generate_bit_pattern_tests() -> List[Tuple[str, int]]:
        """ビットパターンのテストケースを生成"""
        return [
            ('all_zeros', 0),
            ('all_ones_8bit', 0xFF),
            ('all_ones_16bit', 0xFFFF),
            ('all_ones_32bit', 0xFFFFFFFF),
            ('alternating_01', 0x55555555),
            ('alternating_10', 0xAAAAAAAA),
            ('single_bit_0', 1),
            ('single_bit_7', 1 << 7),
            ('single_bit_15', 1 << 15),
            ('single_bit_31', 1 << 31),
        ]
    
    @staticmethod
    def generate_checksum_test_data() -> List[bytes]:
        """チェックサム計算用のテストデータを生成"""
        test_data = []
        
        # 基本パターン
        test_data.append(b'\x00' * 32)  # 全て0
        test_data.append(b'\xFF' * 32)  # 全て1
        test_data.append(b'\x55' * 32)  # 01010101パターン
        test_data.append(b'\xAA' * 32)  # 10101010パターン
        
        # ランダムデータ
        random.seed(42)
        for _ in range(10):
            data = bytes([random.randint(0, 255) for _ in range(32)])
            test_data.append(data)
        
        # 実際のパケットデータ風
        packet_like = bytearray(32)
        packet_like[0] = 0x12  # version + packet_id上位
        packet_like[1] = 0x34  # packet_id下位 + type
        packet_like[2] = 0x56  # flags
        packet_like[3] = 0x78  # day + reserved
        # timestamp (8 bytes)
        timestamp = int(datetime.now().timestamp())
        for i in range(8):
            packet_like[4 + i] = (timestamp >> (8 * (7 - i))) & 0xFF
        test_data.append(bytes(packet_like))
        
        return test_data
