"""
pytest共通設定とフィクスチャ

全テストで共通して使用される設定とフィクスチャを定義します。
"""

import pytest
import sys
import os
from typing import Dict, Any, List
from datetime import datetime

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from wtp.packet import Format, Request, Response, BitFieldError


@pytest.fixture
def basic_packet_data() -> Dict[str, Any]:
    """基本的なパケットデータのフィクスチャ"""
    return {
        'version': 1,
        'packet_id': 123,
        'type': 2,
        'weather_flag': 1,
        'temperature_flag': 1,
        'pops_flag': 1,
        'alert_flag': 0,
        'disaster_flag': 0,
        'ex_flag': 0,
        'day': 3,
        'reserved': 0,
        'timestamp': int(datetime.now().timestamp()),
        'area_code': 12345,
        'checksum': 0  # 自動計算される
    }


@pytest.fixture
def extended_field_data() -> Dict[str, Any]:
    """拡張フィールドのテストデータ"""
    return {
        'alert': ['津波警報', '大雨警報'],
        'disaster': ['土砂崩れ'],
        'latitude': 35.6895,
        'longitude': 139.6917,
        'source_ip': '192.168.1.1'
    }


@pytest.fixture
def response_packet_data() -> Dict[str, Any]:
    """レスポンスパケット用のテストデータ"""
    return {
        'weather_code': 1000,
        'temperature': 125,  # 25℃ (125 - 100)
        'pops': 30  # 30%
    }


@pytest.fixture
def boundary_values() -> Dict[str, Dict[str, int]]:
    """境界値テスト用のデータ"""
    return {
        'version': {'min': 0, 'max': 15},
        'packet_id': {'min': 0, 'max': 4095},
        'type': {'min': 0, 'max': 7},
        'day': {'min': 0, 'max': 7},
        'reserved': {'min': 0, 'max': 15},
        'area_code': {'min': 0, 'max': 1048575},
        'checksum': {'min': 0, 'max': 4095},
        'weather_code': {'min': 0, 'max': 65535},
        'temperature': {'min': 0, 'max': 255},
        'pops': {'min': 0, 'max': 100}
    }


@pytest.fixture
def invalid_values() -> Dict[str, List[int]]:
    """無効な値のテストデータ"""
    return {
        'version': [-1, 16, 100],
        'packet_id': [-1, 4096, 10000],
        'type': [-1, 8, 15],
        'day': [-1, 8, 10],
        'reserved': [-1, 16, 100],
        'area_code': [-1, 1048576, 2000000],
        'checksum': [-1, 4096, 10000],
        'weather_code': [-1, 65536, 100000],
        'temperature': [-1, 256, 1000],
        'pops': [-1, 101, 200]
    }


@pytest.fixture
def japanese_text_data() -> Dict[str, List[str]]:
    """日本語テキストのテストデータ"""
    return {
        'alert': [
            '津波警報',
            '大雨警報',
            '暴風警報',
            '大雪警報',
            '洪水警報'
        ],
        'disaster': [
            '土砂崩れ',
            '河川氾濫',
            '道路冠水',
            '停電',
            '建物倒壊'
        ],
        'special_chars': [
            'テスト①②③',
            '記号！＠＃＄％',
            '改行\n含む',
            'タブ\t文字',
            '空白　全角'
        ]
    }


@pytest.fixture
def large_data_set() -> Dict[str, Any]:
    """大量データのテストケース"""
    return {
        'alert': [f'警報{i}' for i in range(100)],
        'disaster': [f'災害{i}' for i in range(50)],
        'long_string': 'あ' * 1000,  # 長い文字列
        'large_number': 999999999
    }


class PacketTestHelper:
    """パケットテスト用のヘルパークラス"""
    
    @staticmethod
    def create_test_packet(packet_class, **kwargs):
        """テスト用パケットを作成"""
        try:
            return packet_class(**kwargs)
        except Exception as e:
            pytest.fail(f"パケット作成に失敗: {e}")
    
    @staticmethod
    def assert_packet_equality(packet1, packet2, ignore_checksum=False):
        """パケットの等価性をチェック"""
        dict1 = packet1.as_dict()
        dict2 = packet2.as_dict()
        
        if ignore_checksum:
            dict1.pop('checksum', None)
            dict2.pop('checksum', None)
        
        assert dict1 == dict2, f"パケットが一致しません:\n期待値: {dict1}\n実際値: {dict2}"
    
    @staticmethod
    def assert_roundtrip_conversion(packet):
        """往復変換の整合性をチェック"""
        # パケット → バイト列 → パケット
        bytes_data = packet.to_bytes()
        restored = packet.__class__.from_bytes(bytes_data)
        
        PacketTestHelper.assert_packet_equality(packet, restored)
        return restored


@pytest.fixture
def packet_helper():
    """パケットテストヘルパーのフィクスチャ"""
    return PacketTestHelper


# テスト設定
def pytest_configure(config):
    """pytest設定"""
    config.addinivalue_line(
        "markers", "slow: 時間のかかるテスト"
    )
    config.addinivalue_line(
        "markers", "integration: 統合テスト"
    )
    config.addinivalue_line(
        "markers", "performance: パフォーマンステスト"
    )
    config.addinivalue_line(
        "markers", "robustness: 堅牢性テスト"
    )


def pytest_collection_modifyitems(config, items):
    """テストアイテムの修正"""
    for item in items:
        # 統合テストにマーカーを追加
        if "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        # パフォーマンステストにマーカーを追加
        elif "performance" in str(item.fspath):
            item.add_marker(pytest.mark.performance)
            item.add_marker(pytest.mark.slow)
        # 堅牢性テストにマーカーを追加
        elif "robustness" in str(item.fspath):
            item.add_marker(pytest.mark.robustness)
