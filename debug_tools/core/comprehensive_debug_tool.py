#!/usr/bin/env python3
"""
拡張フィールド処理の網羅的デバッグツール
全ての処理段階を詳細に追跡し、問題の特定を支援します
"""

import sys
import os
import traceback
from typing import Dict, Any, List, Optional, Union
import json

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'wtp'))

from wtp.packet import Format
from wtp.packet.extended_field_mixin import ExtendedFieldType
from wtp.packet.bit_utils import extract_bits, extract_rest_bits


class ExtendedFieldDebugger:
    """拡張フィールドの網羅的デバッグクラス"""
    
    def __init__(self):
        self.debug_log = []
        self.error_log = []
        
    def log(self, message: str, level: str = "INFO"):
        """デバッグログを記録"""
        log_entry = {
            "level": level,
            "message": message,
            "timestamp": self._get_timestamp()
        }
        self.debug_log.append(log_entry)
        print(f"[{level}] {message}")
        
    def error(self, message: str, exception: Optional[Exception] = None):
        """エラーログを記録"""
        error_entry = {
            "message": message,
            "exception": str(exception) if exception else None,
            "traceback": traceback.format_exc() if exception else None,
            "timestamp": self._get_timestamp()
        }
        self.error_log.append(error_entry)
        print(f"[ERROR] {message}")
        if exception:
            print(f"Exception: {exception}")
            
    def _get_timestamp(self):
        """タイムスタンプを取得"""
        import datetime
        return datetime.datetime.now().isoformat()
        
    def debug_field_constants(self):
        """フィールド定数の検証"""
        self.log("=== フィールド定数検証 ===")
        
        # 基本定数の確認
        constants = {
            "ALERT": ExtendedFieldType.ALERT,
            "DISASTER": ExtendedFieldType.DISASTER,
            "LATITUDE": ExtendedFieldType.LATITUDE,
            "LONGITUDE": ExtendedFieldType.LONGITUDE,
            "SOURCE_IP": ExtendedFieldType.SOURCE_IP,
        }
        
        for name, value in constants.items():
            self.log(f"{name} = {value}")
            
        # フィールドタイプ分類の確認
        self.log(f"STRING_LIST_FIELDS = {ExtendedFieldType.STRING_LIST_FIELDS}")
        self.log(f"COORDINATE_FIELDS = {ExtendedFieldType.COORDINATE_FIELDS}")
        self.log(f"STRING_FIELDS = {ExtendedFieldType.STRING_FIELDS}")
        
        # 範囲制限の確認
        self.log(f"LATITUDE_MIN = {ExtendedFieldType.LATITUDE_MIN}")
        self.log(f"LATITUDE_MAX = {ExtendedFieldType.LATITUDE_MAX}")
        self.log(f"LONGITUDE_MIN = {ExtendedFieldType.LONGITUDE_MIN}")
        self.log(f"LONGITUDE_MAX = {ExtendedFieldType.LONGITUDE_MAX}")
        self.log(f"COORDINATE_SCALE = {ExtendedFieldType.COORDINATE_SCALE}")
        
        # キーが6ビット範囲内かチェック
        for name, value in constants.items():
            if 0 <= value <= 63:
                self.log(f"{name}({value})は6ビット範囲内: OK")
            else:
                self.error(f"{name}({value})は6ビット範囲外: NG")
                
    def debug_single_field_encoding(self, field_name: str, field_value: Any):
        """単一フィールドのエンコード処理をデバッグ"""
        self.log(f"=== {field_name} フィールドエンコードデバッグ ===")
        
        try:
            # パケット作成
            packet = Format(
                version=1,
                packet_id=1,
                ex_flag=1,
                timestamp=1234567890,
                ex_field={field_name: field_value}
            )
            
            self.log(f"入力値: {field_value} (型: {type(field_value)})")
            self.log(f"作成されたex_field: {packet.ex_field}")
            
            # キーマッピング確認
            key_int = packet._get_extended_field_key_from_str(field_name)
            self.log(f"キー整数値: {key_int}")
            
            if key_int is None:
                self.error(f"キーマッピングが見つかりません: {field_name}")
                return None
                
            # エンコード処理の詳細追跡
            self._debug_encoding_process(packet, field_name, field_value, key_int)
            
            # バイト列変換
            data = packet.to_bytes()
            self.log(f"バイト列長: {len(data)} bytes")
            self.log(f"バイト列(hex): {data.hex()}")
            
            return data
            
        except Exception as e:
            self.error(f"エンコード中にエラー: {e}", e)
            return None
            
    def _debug_encoding_process(self, packet: Format, field_name: str, field_value: Any, key_int: int):
        """エンコード処理の詳細デバッグ"""
        self.log(f"--- エンコード処理詳細 ---")
        
        try:
            # 値の前処理
            if isinstance(field_value, str):
                value_bytes = field_value.encode('utf-8')
                self.log(f"文字列エンコード: '{field_value}' -> {value_bytes}")
            elif field_name in ['latitude', 'longitude']:
                coord_value = float(field_value)
                self.log(f"座標値: {coord_value}")
                
                # 範囲チェック
                if field_name == 'latitude':
                    in_range = ExtendedFieldType.LATITUDE_MIN <= coord_value <= ExtendedFieldType.LATITUDE_MAX
                    self.log(f"緯度範囲チェック: {in_range}")
                elif field_name == 'longitude':
                    in_range = ExtendedFieldType.LONGITUDE_MIN <= coord_value <= ExtendedFieldType.LONGITUDE_MAX
                    self.log(f"経度範囲チェック: {in_range}")
                
                # 整数変換
                int_value = int(coord_value * ExtendedFieldType.COORDINATE_SCALE)
                self.log(f"整数変換: {coord_value} * {ExtendedFieldType.COORDINATE_SCALE} = {int_value}")
                
                # 32ビット範囲チェック
                in_int32_range = ExtendedFieldType.INT32_MIN <= int_value <= ExtendedFieldType.INT32_MAX
                self.log(f"32ビット範囲チェック: {in_int32_range}")
                
                value_bytes = int_value.to_bytes(4, byteorder='big', signed=True)
                self.log(f"4バイト符号付き整数: {value_bytes}")
            else:
                self.log(f"その他の値型: {type(field_value)}")
                value_bytes = str(field_value).encode('utf-8')
                
            # ヘッダー作成
            bytes_needed = len(value_bytes)
            self.log(f"必要バイト数: {bytes_needed}")
            
            header = ((bytes_needed & packet.MAX_EXTENDED_LENGTH) << packet.EXTENDED_HEADER_KEY) | (key_int & packet.MAX_EXTENDED_KEY)
            self.log(f"ヘッダー: {bin(header)} ({header})")
            
            # ビット構造の詳細
            bytes_length_part = (bytes_needed & packet.MAX_EXTENDED_LENGTH) << packet.EXTENDED_HEADER_KEY
            key_part = key_int & packet.MAX_EXTENDED_KEY
            self.log(f"バイト長部分: {bin(bytes_length_part)} ({bytes_length_part})")
            self.log(f"キー部分: {bin(key_part)} ({key_part})")
            
            value_bits = int.from_bytes(value_bytes, byteorder='big')
            self.log(f"値ビット: {bin(value_bits)} ({value_bits})")
            self.log(f"値ビット長: {value_bits.bit_length()}")
            
            # レコードビット作成
            record_bits = (value_bits << packet.EXTENDED_HEADER_TOTAL) | header
            self.log(f"レコードビット: {bin(record_bits)}")
            self.log(f"レコードビット長: {record_bits.bit_length()}")
            
            # 期待されるビット長
            expected_bits = packet.EXTENDED_HEADER_TOTAL + (bytes_needed * 8)
            self.log(f"期待ビット長: {expected_bits}")
            self.log(f"実際ビット長: {record_bits.bit_length()}")
            
        except Exception as e:
            self.error(f"エンコード処理詳細でエラー: {e}", e)
            
    def debug_single_field_decoding(self, data: bytes, expected_field: str, expected_value: Any):
        """単一フィールドのデコード処理をデバッグ"""
        self.log(f"=== {expected_field} フィールドデコードデバッグ ===")
        
        try:
            # バイト列からビット列に変換
            bitstr = int.from_bytes(data, byteorder='big')
            self.log(f"バイト列: {data.hex()}")
            self.log(f"ビット列: {bin(bitstr)}")
            self.log(f"ビット列長: {bitstr.bit_length()}")
            
            # パケット復元
            restored = Format.from_bytes(data)
            self.log(f"復元されたex_field: {restored.ex_field}")
            
            # 詳細なデコード処理の追跡
            self._debug_decoding_process(data, bitstr)
            
            # 結果の検証
            if expected_field in restored.ex_field:
                restored_value = restored.ex_field[expected_field]
                self.log(f"期待値: {expected_value}")
                self.log(f"復元値: {restored_value}")
                
                if isinstance(expected_value, float):
                    error = abs(expected_value - restored_value) if restored_value is not None else float('inf')
                    self.log(f"誤差: {error}")
                    success = error < 0.000001
                else:
                    success = expected_value == restored_value
                    
                self.log(f"検証結果: {'✅ 成功' if success else '❌ 失敗'}")
                return success
            else:
                self.error(f"フィールド '{expected_field}' が復元されませんでした")
                return False
                
        except Exception as e:
            self.error(f"デコード中にエラー: {e}", e)
            return False
            
    def _debug_decoding_process(self, data: bytes, bitstr: int):
        """デコード処理の詳細デバッグ"""
        self.log(f"--- デコード処理詳細 ---")
        
        try:
            # 基本フィールドの終了位置を計算
            packet = Format(version=1, packet_id=1, ex_flag=0, timestamp=1234567890)
            max_pos = max(pos + size for field, (pos, size) in packet._BIT_FIELDS.items())
            self.log(f"基本フィールド終了位置: {max_pos}")
            
            # 拡張フィールドビットを抽出
            ex_field_bits = extract_rest_bits(bitstr, max_pos)
            self.log(f"拡張フィールドビット: {bin(ex_field_bits)}")
            self.log(f"拡張フィールドビット長: {ex_field_bits.bit_length()}")
            
            # 正確なビット長を計算
            total_bits = len(data) * 8
            ex_field_total_bits = total_bits - max_pos
            self.log(f"総ビット数: {total_bits}")
            self.log(f"拡張フィールド総ビット数: {ex_field_total_bits}")
            
            # 手動でヘッダー解析
            if ex_field_bits.bit_length() >= packet.EXTENDED_HEADER_TOTAL:
                header = extract_bits(ex_field_bits, 0, packet.EXTENDED_HEADER_TOTAL)
                bytes_length = (header >> packet.EXTENDED_HEADER_KEY) & packet.MAX_EXTENDED_LENGTH
                key = header & packet.MAX_EXTENDED_KEY
                
                self.log(f"ヘッダー: {bin(header)} ({header})")
                self.log(f"抽出バイト長: {bytes_length}")
                self.log(f"抽出キー: {key}")
                
                # キーマッピング確認
                field_name = packet._get_extended_field_key(key)
                self.log(f"キーから復元したフィールド名: {field_name}")
                
                # 必要ビット数の確認
                required_bits = packet.EXTENDED_HEADER_TOTAL + (bytes_length * 8)
                self.log(f"必要ビット数: {required_bits}")
                self.log(f"利用可能ビット数: {ex_field_total_bits}")
                
                if required_bits <= ex_field_total_bits:
                    # 値ビットを抽出
                    value_bits = extract_bits(ex_field_bits, packet.EXTENDED_HEADER_TOTAL, bytes_length * 8)
                    self.log(f"値ビット: {bin(value_bits)}")
                    
                    # 値をバイト列に変換
                    value_bytes = value_bits.to_bytes(bytes_length, byteorder='big')
                    self.log(f"値バイト列: {value_bytes}")
                    
                    # 値の復元
                    if key in ExtendedFieldType.COORDINATE_FIELDS:
                        if bytes_length == 4:
                            int_value = int.from_bytes(value_bytes, byteorder='big', signed=True)
                            coord_value = int_value / ExtendedFieldType.COORDINATE_SCALE
                            self.log(f"座標復元: {int_value} / {ExtendedFieldType.COORDINATE_SCALE} = {coord_value}")
                        else:
                            self.log(f"予期しないバイト長: {bytes_length}")
                    elif key in ExtendedFieldType.STRING_LIST_FIELDS or key == ExtendedFieldType.SOURCE_IP:
                        string_value = value_bytes.decode('utf-8').rstrip('\x00#')
                        self.log(f"文字列復元: '{string_value}'")
                else:
                    self.error(f"ビット数不足: 必要{required_bits} > 利用可能{ex_field_total_bits}")
            else:
                self.error(f"ヘッダー分のビット数不足: {ex_field_bits.bit_length()} < {packet.EXTENDED_HEADER_TOTAL}")
                
        except Exception as e:
            self.error(f"デコード処理詳細でエラー: {e}", e)
            
    def debug_multiple_fields(self, test_data: Dict[str, Any]):
        """複数フィールドの組み合わせテスト"""
        self.log(f"=== 複数フィールド組み合わせデバッグ ===")
        self.log(f"テストデータ: {test_data}")
        
        try:
            # エンコード
            packet = Format(
                version=1,
                packet_id=100,
                ex_flag=1,
                timestamp=1234567890,
                ex_field=test_data
            )
            
            self.log(f"作成されたex_field: {packet.ex_field}")
            
            # 各フィールドのエンコード詳細
            for field_name, field_value in test_data.items():
                self.log(f"--- {field_name} = {field_value} ---")
                key_int = packet._get_extended_field_key_from_str(field_name)
                self.log(f"キー: {key_int}")
                
            # バイト列変換
            data = packet.to_bytes()
            self.log(f"バイト列長: {len(data)} bytes")
            
            # デコード
            restored = Format.from_bytes(data)
            self.log(f"復元されたex_field: {restored.ex_field}")
            
            # 結果検証
            success = True
            for field_name, expected_value in test_data.items():
                if field_name in restored.ex_field:
                    restored_value = restored.ex_field[field_name]
                    if isinstance(expected_value, float):
                        error = abs(expected_value - restored_value)
                        field_success = error < 0.000001
                    else:
                        field_success = expected_value == restored_value
                        
                    self.log(f"{field_name}: {'✅' if field_success else '❌'}")
                    if not field_success:
                        success = False
                else:
                    self.log(f"{field_name}: ❌ (フィールドなし)")
                    success = False
                    
            self.log(f"全体結果: {'✅ 成功' if success else '❌ 失敗'}")
            return success
            
        except Exception as e:
            self.error(f"複数フィールドテスト中にエラー: {e}", e)
            return False
            
    def debug_edge_cases(self):
        """エッジケースのテスト"""
        self.log("=== エッジケーステスト ===")
        
        edge_cases = [
            # 座標の極値
            {"latitude": 90.0, "longitude": 180.0},
            {"latitude": -90.0, "longitude": -180.0},
            {"latitude": 0.0, "longitude": 0.0},
            
            # 文字列の特殊ケース
            {"source_ip": "0.0.0.0"},
            {"source_ip": "255.255.255.255"},
            {"alert": [""]},  # 空文字列
            {"alert": ["非常に長い警報メッセージ" * 10]},  # 長い文字列
            
            # 複数フィールドの組み合わせ
            {
                "alert": ["津波警報", "大雨警報"],
                "disaster": ["洪水", "土砂崩れ"],
                "latitude": 35.6895,
                "longitude": 139.6917,
                "source_ip": "192.168.1.1"
            }
        ]
        
        for i, test_case in enumerate(edge_cases, 1):
            self.log(f"--- エッジケース {i}: {test_case} ---")
            try:
                success = self.debug_multiple_fields(test_case)
                self.log(f"エッジケース {i} 結果: {'✅' if success else '❌'}")
            except Exception as e:
                self.error(f"エッジケース {i} でエラー: {e}", e)
                
    def generate_report(self, output_file: str = None):
        """デバッグレポートを生成"""
        report = {
            "debug_log": self.debug_log,
            "error_log": self.error_log,
            "summary": {
                "total_logs": len(self.debug_log),
                "total_errors": len(self.error_log),
                "has_errors": len(self.error_log) > 0
            }
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
            
        self.log(f"デバッグレポートを生成しました: {output_file}")
        
    def run_comprehensive_debug(self):
        """網羅的デバッグの実行"""
        self.log("網羅的デバッグ開始")
        
        # 1. 定数検証
        self.debug_field_constants()
        
        # 2. 個別フィールドテスト
        test_fields = [
            ("alert", ["津波警報"]),
            ("disaster", ["土砂崩れ"]),
            ("latitude", 35.6895),
            ("longitude", 139.6917),
            ("source_ip", "192.168.1.1")
        ]
        
        for field_name, field_value in test_fields:
            self.log(f"\n{'='*50}")
            data = self.debug_single_field_encoding(field_name, field_value)
            if data:
                self.debug_single_field_decoding(data, field_name, field_value)
                
        # 3. 複数フィールドテスト
        self.log(f"\n{'='*50}")
        multi_field_test = {
            "alert": ["津波警報"],
            "latitude": 35.6895,
            "longitude": 139.6917,
            "source_ip": "192.168.1.1"
        }
        self.debug_multiple_fields(multi_field_test)
        
        # 4. エッジケーステスト
        self.log(f"\n{'='*50}")
        self.debug_edge_cases()
        
        # 5. レポート生成
        self.generate_report()
        
        self.log("網羅的デバッグ完了")


def main():
    """メイン関数"""
    debugger = ExtendedFieldDebugger()
    debugger.run_comprehensive_debug()


if __name__ == "__main__":
    main()
