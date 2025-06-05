"""
拡張フィールドのbit長取得デバッグコード
パケットフォーマットの拡張フィールドのビット長解析を行います
"""
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from common.packet.format import Format
from common.packet.extended_field import ExtendedField, ExtendedFieldType
from common.packet.bit_utils import extract_bits


class ExtendedFieldBitAnalyzer:
    """拡張フィールドのビット長解析クラス"""
    
    def __init__(self, packet: Format):
        """
        初期化
        
        Args:
            packet: 解析対象のFormatパケット
        """
        self.packet = packet
        self.basic_field_bits = 128  # 基本フィールドは128ビット固定
        
        # 基本フィールドの構造情報をコピー
        self.basic_field_structure = getattr(packet, '_BIT_FIELDS', {})
    
    def analyze_bits(self) -> Dict[str, Any]:
        """
        拡張フィールドのビット長を詳細解析
        
        Returns:
            解析結果の辞書
        """
        result = {
            'basic_field_bits': self.basic_field_bits,
            'extended_field_bits': 0,
            'total_bits': self.basic_field_bits,
            'extended_field_details': [],
            'has_extended_field': self.packet.ex_flag == 1,
            'extended_field_data': {}
        }
        
        # 拡張フィールドが存在する場合の解析
        if self.packet.ex_flag == 1 and self.packet.ex_field and not self.packet.ex_field.is_empty():
            extended_data = self.packet.ex_field.to_dict()
            result['extended_field_data'] = extended_data
            
            # 各拡張フィールドのビット長を計算
            for key, value in extended_data.items():
                field_details = self._analyze_field_bits(key, value)
                result['extended_field_details'].append(field_details)
                result['extended_field_bits'] += field_details['total_field_bits']
            
            result['total_bits'] = result['basic_field_bits'] + result['extended_field_bits']
        
        return result
    
    def _analyze_field_bits(self, key: str, value: Any) -> Dict[str, Any]:
        """
        個別フィールドのビット長解析
        
        Args:
            key: フィールドキー
            value: フィールド値
            
        Returns:
            フィールドのビット長詳細
        """
        field_info = {
            'key': key,
            'key_type': ExtendedField.FIELD_MAPPING_STR.get(key, 'unknown'),
            'value': value,
            'value_type': type(value).__name__,
            'header_bits': ExtendedField.EXTENDED_HEADER_TOTAL,  # 16ビット固定
            'data_bits': 0,
            'total_field_bits': 0,
            'records': []
        }
        
        # 値をリストに正規化
        if isinstance(value, list):
            values_to_process = value
        else:
            values_to_process = [value]
        
        # 各値（レコード）のビット長を計算
        for i, single_value in enumerate(values_to_process):
            record_info = self._analyze_record_bits(key, single_value, i)
            field_info['records'].append(record_info)
            field_info['data_bits'] += record_info['data_bits']
            field_info['total_field_bits'] += record_info['total_record_bits']
        
        return field_info
    
    def _analyze_record_bits(self, key: str, value: Any, index: int = 0) -> Dict[str, Any]:
        """
        個別レコードのビット長解析
        
        Args:
            key: フィールドキー
            value: レコード値
            index: レコードのインデックス
            
        Returns:
            レコードのビット長詳細
        """
        record_info = {
            'index': index,
            'value': value,
            'header_bits': ExtendedField.EXTENDED_HEADER_TOTAL,
            'data_bits': 0,
            'total_record_bits': ExtendedField.EXTENDED_HEADER_TOTAL,
            'encoding_method': 'unknown',
            'byte_length': 0
        }
        
        try:
            # 値の種類に応じてビット長を計算
            if isinstance(value, str):
                # 文字列の場合はUTF-8エンコード
                value_bytes = value.encode('utf-8')
                record_info['encoding_method'] = 'utf-8'
                record_info['byte_length'] = len(value_bytes)
                record_info['data_bits'] = len(value_bytes) * 8
                
            elif key in ['latitude', 'longitude']:
                # 座標値の場合は4バイト固定（符号付き32ビット整数）
                coord_value = float(value)
                int_value = int(coord_value * ExtendedFieldType.COORDINATE_SCALE)
                record_info['encoding_method'] = 'coordinate_int32'
                record_info['byte_length'] = 4
                record_info['data_bits'] = 32
                record_info['scaled_value'] = int_value
                
            elif isinstance(value, (int, float)):
                # その他の数値
                if isinstance(value, float):
                    # 浮動小数点数は文字列として扱う
                    value_str = str(value)
                    value_bytes = value_str.encode('utf-8')
                    record_info['encoding_method'] = 'float_as_string'
                    record_info['byte_length'] = len(value_bytes)
                    record_info['data_bits'] = len(value_bytes) * 8
                else:
                    # 整数は最小バイト数で格納
                    byte_length = (value.bit_length() + 7) // 8 or 1
                    record_info['encoding_method'] = 'integer'
                    record_info['byte_length'] = byte_length
                    record_info['data_bits'] = byte_length * 8
            
            record_info['total_record_bits'] = record_info['header_bits'] + record_info['data_bits']
            
        except Exception as e:
            record_info['error'] = str(e)
        
        return record_info
    
    def print_analysis(self, detailed: bool = True) -> None:
        """
        解析結果を整形して出力
        
        Args:
            detailed: 詳細情報を出力するかどうか
        """
        analysis = self.analyze_bits()
        
        print("=" * 60)
        print("拡張フィールド ビット長解析結果")
        print("=" * 60)
        
        print(f"基本フィールド: {analysis['basic_field_bits']} ビット")
        print(f"拡張フィールド: {analysis['extended_field_bits']} ビット")
        print(f"総ビット長: {analysis['total_bits']} ビット")
        print(f"総バイト長: {(analysis['total_bits'] + 7) // 8} バイト")
        print(f"拡張フィールド有効: {'はい' if analysis['has_extended_field'] else 'いいえ'}")
        print()
        
        if analysis['has_extended_field'] and analysis['extended_field_details']:
            print("拡張フィールド詳細:")
            print("-" * 40)
            
            for field_detail in analysis['extended_field_details']:
                print(f"フィールド: {field_detail['key']} (タイプ: {field_detail['key_type']})")
                print(f"  値: {field_detail['value']}")
                print(f"  値タイプ: {field_detail['value_type']}")
                print(f"  総ビット長: {field_detail['total_field_bits']} ビット")
                
                if detailed and field_detail['records']:
                    print(f"  レコード数: {len(field_detail['records'])}")
                    for record in field_detail['records']:
                        print(f"    レコード {record['index']}:")
                        print(f"      値: {record['value']}")
                        print(f"      ヘッダー: {record['header_bits']} ビット")
                        print(f"      データ: {record['data_bits']} ビット ({record['byte_length']} バイト)")
                        print(f"      エンコード方法: {record['encoding_method']}")
                        if 'scaled_value' in record:
                            print(f"      スケール後値: {record['scaled_value']}")
                        if 'error' in record:
                            print(f"      エラー: {record['error']}")
                print()
    
    def get_total_bits(self) -> int:
        """総ビット長を取得"""
        analysis = self.analyze_bits()
        return analysis['total_bits']
    
    def get_extended_bits(self) -> int:
        """拡張フィールドのビット長を取得"""
        analysis = self.analyze_bits()
        return analysis['extended_field_bits']
    
    def analyze_basic_field_difference(self) -> Dict[str, Any]:
        """
        基本フィールドでの差分を詳細解析
        
        Returns:
            基本フィールドの差分解析結果
        """
        result = {
            'expected_total_bits': self.basic_field_bits,
            'actual_total_bits': 0,
            'field_analysis': [],
            'contributing_fields': [],
            'unused_bits': 0
        }
        
        # 実際のビット列を取得
        actual_bits = self.packet.to_bits()
        actual_bit_length = actual_bits.bit_length()
        result['actual_total_bits'] = actual_bit_length
        
        # 各基本フィールドを解析
        for field_name, (position, expected_length) in self.basic_field_structure.items():
            # area_codeの場合は内部値を取得
            if field_name == 'area_code':
                field_value = getattr(self.packet, f'_{field_name}', 0)
            else:
                field_value = getattr(self.packet, field_name, 0)
            
            # フィールドの実際のビット使用量を計算
            if field_value == 0:
                actual_used_bits = 0
            elif isinstance(field_value, str):
                # 文字列の場合は数値に変換してから計算
                try:
                    numeric_value = int(field_value)
                    actual_used_bits = numeric_value.bit_length() if numeric_value > 0 else 0
                except (ValueError, TypeError):
                    actual_used_bits = 0
            else:
                actual_used_bits = field_value.bit_length() if field_value > 0 else 0
            
            field_info = {
                'field_name': field_name,
                'position': position,
                'expected_bits': expected_length,
                'actual_value': field_value,
                'actual_used_bits': actual_used_bits,
                'unused_bits': expected_length - actual_used_bits,
                'efficiency': (actual_used_bits / expected_length * 100) if expected_length > 0 else 0
            }
            
            result['field_analysis'].append(field_info)
            
            # 使用されていないビットがあるフィールドを記録
            if field_info['unused_bits'] > 0:
                result['contributing_fields'].append({
                    'field_name': field_name,
                    'unused_bits': field_info['unused_bits'],
                    'value': field_value
                })
                result['unused_bits'] += field_info['unused_bits']
        
        return result
    
    def print_basic_field_analysis(self) -> None:
        """基本フィールドの詳細解析を出力"""
        analysis = self.analyze_basic_field_difference()
        
        print("基本フィールド詳細解析:")
        print("-" * 40)
        print(f"期待される総ビット長: {analysis['expected_total_bits']} ビット")
        print(f"実際の総ビット長: {analysis['actual_total_bits']} ビット")
        
        # 差分の詳細説明
        difference = abs(analysis['expected_total_bits'] - analysis['actual_total_bits'])
        if difference > 0:
            print(f"ビット長差分: {difference} ビット")
            print()
            print("🔍 差分の原因特定ガイド:")
            print("=" * 30)
            print("1. 差分の理由：")
            print("   - 「期待される総ビット長」は全フィールドの定義済みサイズの合計")
            print("   - 「実際の総ビット長」は実際の値から計算されたビット列の長さ")
            print("   - 差分は主に上位ビットの0が省略されることで発生")
            print()
            print("2. 主な原因：")
            print("   - 値が0のフィールド（ビット表現で最上位ビットが不要）")
            print("   - 小さい値のフィールド（予約されたビット幅を完全に使わない）")
            print("   - 特にtimestamp、area_code、checksumなど大きなビット幅を持つフィールド")
            print()
        
        print(f"未使用ビット数（効率性）: {analysis['unused_bits']} ビット")
        print()
        
        if analysis['contributing_fields']:
            print("効率性の観点での未使用ビットを持つフィールド:")
            for field_info in analysis['contributing_fields']:
                print(f"  {field_info['field_name']}: {field_info['unused_bits']} ビット未使用 (値: {field_info['value']})")
            print()
        
        print("各フィールドの詳細:")
        for field_info in analysis['field_analysis']:
            efficiency_str = f"{field_info['efficiency']:.1f}%" if field_info['efficiency'] < 100 else "100%"
            print(f"  {field_info['field_name']}:")
            print(f"    位置: {field_info['position']}-{field_info['position'] + field_info['expected_bits'] - 1} ビット")
            print(f"    期待ビット長: {field_info['expected_bits']} ビット")
            print(f"    実際の値: {field_info['actual_value']}")
            print(f"    使用ビット数: {field_info['actual_used_bits']} ビット")
            print(f"    効率: {efficiency_str}")
            if field_info['unused_bits'] > 0:
                print(f"    未使用: {field_info['unused_bits']} ビット")
    
    def visualize_bit_layout(self) -> Dict[str, Any]:
        """
        ビット列の配置を可視化用に解析
        
        Returns:
            ビット配置の可視化情報
        """
        # 実際のビット列を取得
        actual_bits = self.packet.to_bits()
        actual_bit_length = actual_bits.bit_length()
        
        # ビット列を2進数文字列に変換（左詰め）
        if actual_bit_length > 0:
            bit_string = format(actual_bits, f'0{actual_bit_length}b')
        else:
            bit_string = '0'
        
        # 各フィールドの情報を収集
        field_layout = []
        for field_name, (position, expected_length) in sorted(self.basic_field_structure.items(), key=lambda x: x[1][0]):
            # area_codeの場合は内部値を取得
            if field_name == 'area_code':
                field_value = getattr(self.packet, f'_{field_name}', 0)
            else:
                field_value = getattr(self.packet, field_name, 0)
            
            # フィールドのビット範囲を計算
            start_pos = position
            end_pos = position + expected_length - 1
            
            # extract_bits関数を使って正しくビットを抽出
            try:
                extracted_value = extract_bits(actual_bits, start_pos, expected_length)
                field_bits = format(extracted_value, f'0{expected_length}b')
            except Exception:
                # エラーの場合は0で埋める
                field_bits = '0' * expected_length
                extracted_value = 0
            
            field_layout.append({
                'field_name': field_name,
                'position': position,
                'length': expected_length,
                'start_bit': start_pos,
                'end_bit': end_pos,
                'value': field_value,
                'bit_representation': field_bits,
                'decimal_from_bits': int(field_bits, 2) if field_bits and '1' in field_bits else 0
            })
        
        return {
            'actual_bits': actual_bits,
            'actual_bit_length': actual_bit_length,
            'bit_string': bit_string,
            'field_layout': field_layout,
            'total_expected_bits': 128
        }
    
    def print_bit_visualization(self) -> None:
        """ビット配置の可視化を出力"""
        layout = self.visualize_bit_layout()
        
        print("📊 ビット配置可視化:")
        print("=" * 70)
        
        # 基本情報
        print(f"実際のビット長: {layout['actual_bit_length']} ビット")
        print(f"期待されるビット長: {layout['total_expected_bits']} ビット")
        print(f"16進数表現: 0x{layout['actual_bits']:X}")
        print()
        
        # 基本フィールドの可視化
        self._print_basic_field_bits(layout)
        
        # 拡張フィールドの可視化（存在する場合）
        if self.packet.ex_flag == 1 and self.packet.ex_field and not self.packet.ex_field.is_empty():
            self._print_extended_field_bits(layout)
        
        # フィールドマッピング表示
        print("フィールドマッピング:")
        print("-" * 70)
        print(f"{'フィールド名':<15} {'位置':<10} {'長さ':<4} {'値':<12} {'ビット表現':<20} {'検証'}")
        print("-" * 70)
        
        for field_info in layout['field_layout']:
            field_name = field_info['field_name']
            position_str = f"{field_info['start_bit']}-{field_info['end_bit']}"
            length = field_info['length']
            value = field_info['value']
            bit_repr = field_info['bit_representation']
            decimal_from_bits = field_info['decimal_from_bits']
            
            # 値の検証（実際の値とビット表現から復元した値が一致するか）
            verification = "✓" if decimal_from_bits == value else f"✗({decimal_from_bits})"
            
            print(f"{field_name:<15} {position_str:<10} {length:<4} {value:<12} {bit_repr:<20} {verification}")
        
        print()
        
        # ビット使用効率のサマリー
        bit_string = layout['bit_string']
        total_used_bits = sum(1 for bit in bit_string if bit == '1')
        efficiency = (total_used_bits / len(bit_string) * 100) if len(bit_string) > 0 else 0
        print(f"ビット使用効率: {total_used_bits}/{len(bit_string)} ビット ({efficiency:.1f}%)")
        
        # 各フィールドのビット効率
        print("\nフィールド別効率:")
        print("-" * 40)
        for field_info in layout['field_layout']:
            field_bits = field_info['bit_representation']
            used_bits = field_bits.count('1')
            total_bits = len(field_bits)
            efficiency = (used_bits / total_bits * 100) if total_bits > 0 else 0
            print(f"  {field_info['field_name']:<15}: {used_bits:2d}/{total_bits:2d} ビット ({efficiency:5.1f}%)")
    
    def _print_basic_field_bits(self, layout: Dict[str, Any]) -> None:
        """基本フィールドのビット列を表示"""
        bit_string = layout['bit_string']
        
        print("🔹 基本フィールド（0-127ビット）:")
        print("-" * 60)
        print("※ 左端が最下位ビット（LSB）、右端が最上位ビット（MSB）")
        print("-" * 60)
        
        # 基本フィールドは最初の128ビット
        basic_end = min(128, len(bit_string))
        
        for i in range(0, basic_end, 8):
            bit_pos_start = i
            bit_pos_end = min(i + 7, basic_end - 1)
            
            # ビット列の該当部分を取得
            start_idx = max(0, len(bit_string) - bit_pos_end - 1)
            end_idx = min(len(bit_string), len(bit_string) - bit_pos_start)
            
            if start_idx < end_idx:
                chunk = bit_string[start_idx:end_idx]
                chunk = chunk[::-1]
                chunk = chunk.ljust(8, '0')
            else:
                chunk = '00000000'
            
            pos_numbers = ""
            for j in range(len(chunk)):
                pos_numbers += str((bit_pos_start + j) % 10)
            
            # このビット範囲に対応するフィールドを特定
            field_info = self._get_fields_in_bit_range(bit_pos_start, bit_pos_end)
            
            print(f"ビット{bit_pos_start:3d}-{bit_pos_end:3d}: {chunk:8s} (0x{int(chunk, 2):02X}) {field_info}")
            print(f"{'位置番号:':<12} {pos_numbers:8s}")
            print()
    
    def _get_fields_in_bit_range(self, start_bit: int, end_bit: int) -> str:
        """指定されたビット範囲に含まれるフィールドを特定"""
        fields_in_range = []
        
        for field_name, (position, expected_length) in sorted(self.basic_field_structure.items(), key=lambda x: x[1][0]):
            field_start = position
            field_end = position + expected_length - 1
            
            # ビット範囲とフィールド範囲が重複するかチェック
            if not (end_bit < field_start or start_bit > field_end):
                # 重複している場合
                overlap_start = max(start_bit, field_start)
                overlap_end = min(end_bit, field_end)
                
                if overlap_start == field_start and overlap_end == field_end:
                    # フィールド全体が含まれる
                    fields_in_range.append(f"📌{field_name}")
                else:
                    # フィールドの一部が含まれる
                    fields_in_range.append(f"📍{field_name}[{overlap_start-field_start}:{overlap_end-field_start+1}]")
        
        if not fields_in_range:
            return ""
        elif len(fields_in_range) == 1:
            return fields_in_range[0]
        else:
            return " + ".join(fields_in_range)
    
    def _print_extended_field_bits(self, layout: Dict[str, Any]) -> None:
        """拡張フィールドのビット列を表示"""
        bit_string = layout['bit_string']
        total_bits = len(bit_string)
        
        if total_bits <= 128:
            return
        
        print("🔸 拡張フィールド（128ビット以降）:")
        print("-" * 60)
        print("※ 左端が最下位ビット（LSB）、右端が最上位ビット（MSB）")
        print("-" * 60)
        
        # 拡張フィールドの解析情報を取得
        extended_analysis = self.analyze_bits()
        
        # 128ビット以降を表示
        current_bit = 128
        
        for field_detail in extended_analysis['extended_field_details']:
            field_name = field_detail['key']
            total_field_bits = field_detail['total_field_bits']
            
            print(f"📋 フィールド: {field_name}")
            print(f"   範囲: ビット{current_bit}-{current_bit + total_field_bits - 1} ({total_field_bits}ビット)")
            print("-" * 40)
            
            # このフィールドのレコードを表示
            record_start_bit = current_bit
            for record in field_detail['records']:
                record_total_bits = record['total_record_bits']
                print(f"  📄 レコード {record['index']}: ビット{record_start_bit}-{record_start_bit + record_total_bits - 1}")
                print(f"     値: {record['value']}")
                print(f"     ヘッダー: {record['header_bits']}ビット + データ: {record['data_bits']}ビット")
                
                # このレコードのビット列を表示
                for i in range(record_start_bit, record_start_bit + record_total_bits, 8):
                    bit_pos_start = i
                    bit_pos_end = min(i + 7, record_start_bit + record_total_bits - 1, total_bits - 1)
                    
                    if bit_pos_end >= total_bits:
                        break
                    
                    # ビット列の該当部分を取得
                    start_idx = max(0, total_bits - bit_pos_end - 1)
                    end_idx = min(total_bits, total_bits - bit_pos_start)
                    
                    if start_idx < end_idx:
                        chunk = bit_string[start_idx:end_idx]
                        chunk = chunk[::-1]
                        chunk = chunk.ljust(8, '0')
                    else:
                        chunk = '00000000'
                    
                    pos_numbers = ""
                    for j in range(len(chunk)):
                        pos_numbers += str((bit_pos_start + j) % 10)
                    
                    # 拡張フィールドの詳細マッピング
                    extended_field_info = self._get_extended_field_mapping(
                        bit_pos_start, bit_pos_end, record_start_bit, record, field_name
                    )
                    
                    print(f"     ビット{bit_pos_start:3d}-{bit_pos_end:3d}: {chunk:8s} (0x{int(chunk, 2):02X}) {extended_field_info}")
                    print(f"     {'位置番号:':<12} {pos_numbers:8s}")
                    print()
                
                record_start_bit += record_total_bits
            
            current_bit += total_field_bits
            print()
    
    def _get_extended_field_mapping(self, start_bit: int, end_bit: int, record_start_bit: int, 
                                  record: Dict[str, Any], field_name: str) -> str:
        """拡張フィールドのビット範囲に対応する内容を特定"""
        mappings = []
        
        # ヘッダー部分とデータ部分の境界を計算
        header_end = record_start_bit + record['header_bits'] - 1
        data_start = record_start_bit + record['header_bits']
        data_end = record_start_bit + record['total_record_bits'] - 1
        
        # ヘッダー内部構造の境界（6bit キー + 10bit データ長）
        key_start = record_start_bit
        key_end = record_start_bit + 5  # 6ビット（0-5）
        length_start = record_start_bit + 6
        length_end = record_start_bit + 15  # 10ビット（6-15）
        
        # このビット範囲がヘッダー、データのどの部分に含まれるかチェック
        
        # ヘッダー部分のチェック（詳細構造）
        if start_bit <= header_end:
            overlap_start = max(start_bit, record_start_bit)
            overlap_end = min(end_bit, header_end)
            
            if overlap_start <= overlap_end:
                header_relative_start = overlap_start - record_start_bit
                header_relative_end = overlap_end - record_start_bit
                
                # キー部分（0-5ビット）をチェック
                if start_bit <= key_end:
                    key_overlap_start = max(start_bit, key_start)
                    key_overlap_end = min(end_bit, key_end)
                    
                    if key_overlap_start <= key_overlap_end:
                        key_relative_start = key_overlap_start - key_start
                        key_relative_end = key_overlap_end - key_start
                        
                        if key_overlap_start == key_start and key_overlap_end == key_end:
                            # キー全体
                            mappings.append("🔑キー(完全)")
                        else:
                            # キーの一部
                            mappings.append(f"🔍キー[{key_relative_start}:{key_relative_end+1}]")
                
                # データ長部分（6-15ビット）をチェック
                if end_bit >= length_start and start_bit <= length_end:
                    length_overlap_start = max(start_bit, length_start)
                    length_overlap_end = min(end_bit, length_end)
                    
                    if length_overlap_start <= length_overlap_end:
                        length_relative_start = length_overlap_start - length_start
                        length_relative_end = length_overlap_end - length_start
                        
                        if length_overlap_start == length_start and length_overlap_end == length_end:
                            # データ長全体
                            mappings.append("📏長さ(完全)")
                        else:
                            # データ長の一部
                            mappings.append(f"📐長さ[{length_relative_start}:{length_relative_end+1}]")
        
        # データ部分のチェック
        if end_bit >= data_start and start_bit <= data_end:
            overlap_start = max(start_bit, data_start)
            overlap_end = min(end_bit, data_end)
            
            if overlap_start <= overlap_end:
                data_relative_start = overlap_start - data_start
                data_relative_end = overlap_end - data_start
                data_total_bits = record['data_bits']
                
                if overlap_start == data_start and overlap_end == data_end:
                    # データ全体
                    mappings.append(f"📄{field_name}データ(完全)")
                else:
                    # データの一部
                    if data_total_bits > 0:
                        mappings.append(f"📍{field_name}データ[{data_relative_start}:{data_relative_end+1}]")
                    else:
                        mappings.append(f"📍{field_name}データ(空)")
        
        # フィールド値の情報を追加
        if len(mappings) > 0:
            value_info = ""
            if isinstance(record['value'], str):
                # 文字列の場合は一部を表示
                value_str = str(record['value'])
                if len(value_str) > 10:
                    value_info = f"'{value_str[:10]}...'"
                else:
                    value_info = f"'{value_str}'"
            elif field_name in ['latitude', 'longitude']:
                # 座標の場合
                value_info = f"={record['value']}"
            else:
                value_info = f"={record['value']}"
            
            # レコードインデックスも追加
            record_info = f"R{record['index']}"
            if len(mappings) == 1:
                return f"{mappings[0]} {record_info}{value_info}"
            else:
                return f"{' + '.join(mappings)} {record_info}{value_info}"
        
        return ""


def debug_packet_bits(packet: Format, detailed: bool = True) -> ExtendedFieldBitAnalyzer:
    """
    パケットのビット長をデバッグ出力
    
    Args:
        packet: 解析対象のパケット
        detailed: 詳細情報を出力するかどうか
        
    Returns:
        解析クラスのインスタンス
    """
    analyzer = ExtendedFieldBitAnalyzer(packet)
    analyzer.print_analysis(detailed)
    return analyzer


def create_sample_packets() -> List[Tuple[str, Format]]:
    """サンプルパケットを作成"""
    samples = []
    
    # 1. 基本パケット（拡張フィールドなし）
    basic_packet = Format(
        version=1,
        packet_id=1,
        type=0,
        weather_flag=1,
        timestamp=int(datetime.now().timestamp()),
        area_code=13101  # 東京都千代田区
    )
    samples.append(("基本パケット（拡張フィールドなし）", basic_packet))
    
    # 2. 警報情報のみ
    alert_packet = Format(
        version=1,
        packet_id=2,
        type=0,
        ex_flag=1,
        timestamp=int(datetime.now().timestamp()),
        area_code=27100,  # 大阪府
        ex_field={
            'alert': ["津波警報", "大雨警報"]
        }
    )
    samples.append(("警報情報パケット", alert_packet))
    
    # 3. 座標情報のみ
    location_packet = Format(
        version=1,
        packet_id=3,
        type=0,
        ex_flag=1,
        timestamp=int(datetime.now().timestamp()),
        area_code=14100,  # 神奈川県
        ex_field={
            'latitude': 35.6895,
            'longitude': 139.6917
        }
    )
    samples.append(("座標情報パケット", location_packet))
    
    # 4. 全フィールド
    full_packet = Format(
        version=1,
        packet_id=4,
        type=0,
        ex_flag=1,
        weather_flag=1,
        temperature_flag=1,
        alert_flag=1,
        disaster_flag=1,
        timestamp=int(datetime.now().timestamp()),
        area_code=13101,
        ex_field={
            'alert': ["津波警報", "土砂災害警戒情報"],
            'disaster': ["土砂崩れ", "河川氾濫"],
            'latitude': 35.6895,
            'longitude': 139.6917,
            'source': "気象庁データセンター"
        }
    )
    samples.append(("全フィールドパケット", full_packet))
    
    return samples


def main():
    """メイン関数 - サンプル実行"""
    print("拡張フィールド ビット長解析デバッグツール")
    print("=" * 60)
    
    samples = create_sample_packets()
    
    for name, packet in samples:
        print(f"\n【{name}】")
        analyzer = debug_packet_bits(packet, detailed=True)
        
        # 実際のビット列との比較
        actual_bits = packet.to_bits()
        actual_bit_length = actual_bits.bit_length()
        calculated_bit_length = analyzer.get_total_bits()
        
        print(f"計算されたビット長: {calculated_bit_length}")
        print(f"実際のビット長: {actual_bit_length}")
        print(f"一致: {'はい' if calculated_bit_length >= actual_bit_length else 'いいえ'}")
        
        if calculated_bit_length != actual_bit_length:
            print(f"差分: {abs(calculated_bit_length - actual_bit_length)} ビット")
            print()
            
            # 差分の原因を特定するため基本フィールドの詳細解析を実行
            analyzer.print_basic_field_analysis()
            print()
            
            # ビット配置の可視化を実行
            analyzer.print_bit_visualization()


if __name__ == "__main__":
    main()
