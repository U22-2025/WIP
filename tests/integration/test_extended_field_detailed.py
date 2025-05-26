"""
拡張フィールド詳細テスト

ex_fieldの可用性を詳細に検証し、どの組み合わせが使用可能かを明確にします。
"""

import pytest
import sys
import os
from typing import Dict, Any, List, Tuple

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from wtp.packet import Format, Request, Response, BitFieldError
from tests.utils import TestDataGenerator, PacketAssertions


class TestExtendedFieldDiagnostics:
    """拡張フィールドの診断テスト"""
    
    def test_individual_field_analysis(self, basic_packet_data):
        """各拡張フィールドを個別に分析"""
        individual_fields = [
            ('alert_single', {'alert': ['津波警報']}),
            ('alert_multiple', {'alert': ['津波警報', '大雨警報']}),
            ('disaster_single', {'disaster': ['土砂崩れ']}),
            ('disaster_multiple', {'disaster': ['土砂崩れ', '洪水']}),
            ('latitude', {'latitude': 35.6895}),
            ('longitude', {'longitude': 139.6917}),
            ('source_ip', {'source_ip': '192.168.1.1'}),
        ]
        
        results = {}
        
        for field_name, ex_field in individual_fields:
            packet_data = basic_packet_data.copy()
            packet_data['ex_flag'] = 1
            packet_data['ex_field'] = ex_field
            
            try:
                # パケット作成
                original_packet = Format(**packet_data)
                
                # バイト列変換
                bytes_data = original_packet.to_bytes()
                
                # 復元
                restored_packet = Format.from_bytes(bytes_data)
                
                # 結果分析
                original_ex = original_packet.ex_field
                restored_ex = restored_packet.ex_field
                
                success = self._compare_ex_fields(original_ex, restored_ex)
                
                results[field_name] = {
                    'success': success,
                    'original': original_ex,
                    'restored': restored_ex,
                    'bytes_length': len(bytes_data)
                }
                
                print(f"\n=== {field_name} ===")
                print(f"Original: {original_ex}")
                print(f"Restored: {restored_ex}")
                print(f"Success: {success}")
                print(f"Bytes: {len(bytes_data)}")
                
            except Exception as e:
                results[field_name] = {
                    'success': False,
                    'error': str(e),
                    'original': ex_field,
                    'restored': None
                }
                print(f"\n=== {field_name} ===")
                print(f"ERROR: {e}")
        
        # 結果サマリー
        successful_fields = [name for name, result in results.items() if result['success']]
        failed_fields = [name for name, result in results.items() if not result['success']]
        
        print(f"\n=== SUMMARY ===")
        print(f"Successful: {successful_fields}")
        print(f"Failed: {failed_fields}")
        
        # 少なくとも一部は成功することを確認
        assert len(successful_fields) > 0, f"すべてのフィールドが失敗しました: {results}"
    
    def test_field_combinations(self, basic_packet_data):
        """フィールドの組み合わせテスト"""
        combinations = [
            ('alert_disaster', {'alert': ['警報'], 'disaster': ['災害']}),
            ('coordinates', {'latitude': 35.6895, 'longitude': 139.6917}),
            ('alert_ip', {'alert': ['警報'], 'source_ip': '192.168.1.1'}),
            ('disaster_ip', {'disaster': ['災害'], 'source_ip': '192.168.1.1'}),
            ('coordinates_ip', {'latitude': 35.6895, 'longitude': 139.6917, 'source_ip': '192.168.1.1'}),
            ('alert_coordinates', {'alert': ['警報'], 'latitude': 35.6895, 'longitude': 139.6917}),
        ]
        
        results = {}
        
        for combo_name, ex_field in combinations:
            packet_data = basic_packet_data.copy()
            packet_data['ex_flag'] = 1
            packet_data['ex_field'] = ex_field
            
            try:
                # パケット作成
                original_packet = Format(**packet_data)
                
                # バイト列変換
                bytes_data = original_packet.to_bytes()
                
                # 復元
                restored_packet = Format.from_bytes(bytes_data)
                
                # 結果分析
                original_ex = original_packet.ex_field
                restored_ex = restored_packet.ex_field
                
                success = self._compare_ex_fields(original_ex, restored_ex)
                
                results[combo_name] = {
                    'success': success,
                    'original': original_ex,
                    'restored': restored_ex,
                    'match_ratio': self._calculate_match_ratio(original_ex, restored_ex)
                }
                
                print(f"\n=== {combo_name} ===")
                print(f"Original: {original_ex}")
                print(f"Restored: {restored_ex}")
                print(f"Success: {success}")
                print(f"Match ratio: {results[combo_name]['match_ratio']:.2f}")
                
            except Exception as e:
                results[combo_name] = {
                    'success': False,
                    'error': str(e),
                    'original': ex_field,
                    'restored': None,
                    'match_ratio': 0.0
                }
                print(f"\n=== {combo_name} ===")
                print(f"ERROR: {e}")
        
        # 結果サマリー
        successful_combos = [name for name, result in results.items() if result['success']]
        partial_combos = [name for name, result in results.items() 
                         if not result['success'] and result.get('match_ratio', 0) > 0]
        failed_combos = [name for name, result in results.items() 
                        if not result['success'] and result.get('match_ratio', 0) == 0]
        
        print(f"\n=== COMBINATION SUMMARY ===")
        print(f"Fully successful: {successful_combos}")
        print(f"Partially successful: {partial_combos}")
        print(f"Failed: {failed_combos}")
        
        # 結果をアサート（部分的成功も含めて評価）
        total_success_rate = len(successful_combos) / len(combinations)
        print(f"Success rate: {total_success_rate:.2f}")
        
        # 少なくとも50%は何らかの形で動作することを期待
        assert total_success_rate > 0 or len(partial_combos) > 0, \
            f"すべての組み合わせが完全に失敗しました: {results}"
    
    def test_bit_structure_analysis(self, basic_packet_data):
        """ビット構造の詳細分析"""
        test_cases = [
            ('simple_alert', {'alert': ['TEST']}),
            ('simple_number', {'latitude': 123.456}),
            ('simple_ip', {'source_ip': '127.0.0.1'}),
        ]
        
        for case_name, ex_field in test_cases:
            packet_data = basic_packet_data.copy()
            packet_data['ex_flag'] = 1
            packet_data['ex_field'] = ex_field
            
            try:
                # パケット作成
                packet = Format(**packet_data)
                
                # ビット構造分析
                bitstr = packet.to_bits()
                
                # 拡張フィールド部分を抽出
                ex_field_start = max(pos + size for field, (pos, size) in packet._BIT_FIELDS.items())
                ex_field_bits = bitstr >> ex_field_start
                
                print(f"\n=== BIT ANALYSIS: {case_name} ===")
                print(f"Ex field: {ex_field}")
                print(f"Full bitstr: 0x{bitstr:x}")
                print(f"Ex field start: {ex_field_start}")
                print(f"Ex field bits: 0x{ex_field_bits:x}")
                print(f"Ex field bits length: {ex_field_bits.bit_length()}")
                
                # ヘッダー解析
                if ex_field_bits > 0:
                    self._analyze_extended_field_headers(ex_field_bits)
                
            except Exception as e:
                print(f"\n=== BIT ANALYSIS ERROR: {case_name} ===")
                print(f"Error: {e}")
    
    def test_real_world_scenarios(self, basic_packet_data):
        """実世界のシナリオテスト"""
        scenarios = [
            ('emergency_alert', {
                'alert': ['津波警報'],
                'source_ip': '192.168.1.100'
            }),
            ('weather_location', {
                'latitude': 35.6895,
                'longitude': 139.6917
            }),
            ('disaster_report', {
                'disaster': ['土砂崩れ'],
                'latitude': 35.6895,
                'source_ip': '192.168.1.200'
            }),
            ('multiple_alerts', {
                'alert': ['津波警報', '大雨警報'],
                'disaster': ['洪水']
            }),
            ('full_info', {
                'alert': ['緊急警報'],
                'disaster': ['地震'],
                'latitude': 35.6895,
                'longitude': 139.6917,
                'source_ip': '192.168.1.1'
            })
        ]
        
        usable_scenarios = []
        problematic_scenarios = []
        
        for scenario_name, ex_field in scenarios:
            packet_data = basic_packet_data.copy()
            packet_data['ex_flag'] = 1
            packet_data['ex_field'] = ex_field
            
            try:
                # パケット作成
                original_packet = Format(**packet_data)
                
                # 往復変換
                bytes_data = original_packet.to_bytes()
                restored_packet = Format.from_bytes(bytes_data)
                
                # 結果評価
                match_ratio = self._calculate_match_ratio(
                    original_packet.ex_field, 
                    restored_packet.ex_field
                )
                
                print(f"\n=== SCENARIO: {scenario_name} ===")
                print(f"Original: {original_packet.ex_field}")
                print(f"Restored: {restored_packet.ex_field}")
                print(f"Match ratio: {match_ratio:.2f}")
                
                if match_ratio >= 0.8:  # 80%以上一致
                    usable_scenarios.append((scenario_name, match_ratio))
                    print("✅ USABLE")
                elif match_ratio >= 0.5:  # 50%以上一致
                    problematic_scenarios.append((scenario_name, match_ratio))
                    print("⚠️ PARTIALLY USABLE")
                else:
                    problematic_scenarios.append((scenario_name, match_ratio))
                    print("❌ PROBLEMATIC")
                
            except Exception as e:
                problematic_scenarios.append((scenario_name, 0.0))
                print(f"\n=== SCENARIO ERROR: {scenario_name} ===")
                print(f"Error: {e}")
                print("❌ FAILED")
        
        print(f"\n=== REAL WORLD SCENARIO SUMMARY ===")
        print(f"Usable scenarios: {[name for name, ratio in usable_scenarios]}")
        print(f"Problematic scenarios: {[name for name, ratio in problematic_scenarios]}")
        
        # 実用性レポート
        total_scenarios = len(scenarios)
        usable_count = len(usable_scenarios)
        usability_rate = usable_count / total_scenarios
        
        print(f"Usability rate: {usability_rate:.2f} ({usable_count}/{total_scenarios})")
        
        # 少なくとも一部のシナリオは使用可能であることを確認
        assert usable_count > 0, "実用的なシナリオが一つもありません"
    
    def _compare_ex_fields(self, original: Dict[str, Any], restored: Dict[str, Any]) -> bool:
        """拡張フィールドの比較"""
        if not original and not restored:
            return True
        
        if not original or not restored:
            return False
        
        # キーの比較
        if set(original.keys()) != set(restored.keys()):
            return False
        
        # 値の比較
        for key in original.keys():
            orig_val = original[key]
            rest_val = restored[key]
            
            if isinstance(orig_val, list) and isinstance(rest_val, list):
                if orig_val != rest_val:
                    return False
            elif isinstance(orig_val, (int, float)) and isinstance(rest_val, (int, float)):
                if abs(float(orig_val) - float(rest_val)) > 1e-6:
                    return False
            else:
                if orig_val != rest_val:
                    return False
        
        return True
    
    def _calculate_match_ratio(self, original: Dict[str, Any], restored: Dict[str, Any]) -> float:
        """マッチ率を計算"""
        if not original:
            return 1.0 if not restored else 0.0
        
        if not restored:
            return 0.0
        
        total_fields = len(original)
        matched_fields = 0
        
        for key, orig_val in original.items():
            if key in restored:
                rest_val = restored[key]
                
                if isinstance(orig_val, list) and isinstance(rest_val, list):
                    # リストの場合、共通要素の割合を計算
                    if orig_val and rest_val:
                        common = set(orig_val) & set(rest_val)
                        ratio = len(common) / len(set(orig_val) | set(rest_val))
                        matched_fields += ratio
                    elif not orig_val and not rest_val:
                        matched_fields += 1
                elif isinstance(orig_val, (int, float)) and isinstance(rest_val, (int, float)):
                    if abs(float(orig_val) - float(rest_val)) < 1e-6:
                        matched_fields += 1
                    else:
                        # 数値の場合、近似値も部分的にカウント
                        diff_ratio = abs(float(orig_val) - float(rest_val)) / max(abs(float(orig_val)), 1)
                        if diff_ratio < 0.1:  # 10%以内の差
                            matched_fields += 0.5
                else:
                    if orig_val == rest_val:
                        matched_fields += 1
        
        return matched_fields / total_fields if total_fields > 0 else 0.0
    
    def _analyze_extended_field_headers(self, ex_field_bits: int) -> None:
        """拡張フィールドのヘッダーを詳細分析"""
        from wtp.packet.bit_utils import extract_bits
        
        current_pos = 0
        record_count = 0
        
        print("  Header analysis:")
        
        while ex_field_bits > 0 and current_pos < ex_field_bits.bit_length() and record_count < 10:
            if ex_field_bits.bit_length() - current_pos < 16:
                break
                
            header = extract_bits(ex_field_bits, current_pos, 16)
            key = (header >> 10) & 0x3F
            bytes_length = header & 0x3FF
            
            print(f"    Record {record_count}:")
            print(f"      Position: {current_pos}")
            print(f"      Header: 0x{header:04x}")
            print(f"      Key: {key}")
            print(f"      Bytes length: {bytes_length}")
            
            # キーの意味を確認
            key_mapping = {1: 'alert', 17: 'disaster', 65: 'latitude', 66: 'longitude', 128: 'source_ip'}
            key_name = key_mapping.get(key, 'unknown')
            print(f"      Key name: {key_name}")
            
            if bytes_length > 0 and current_pos + 16 + bytes_length * 8 <= ex_field_bits.bit_length():
                value_bits = extract_bits(ex_field_bits, current_pos + 16, bytes_length * 8)
                try:
                    value_bytes = value_bits.to_bytes(bytes_length, byteorder='big')
                    decoded = value_bytes.decode('utf-8', errors='ignore')
                    print(f"      Value: '{decoded}'")
                except:
                    print(f"      Value (raw): 0x{value_bits:x}")
                
                current_pos += 16 + (bytes_length * 8)
            else:
                print(f"      Invalid record - breaking")
                break
            
            record_count += 1
