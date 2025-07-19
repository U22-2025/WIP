"""Unified data processing controller for all types of XML data."""

import json
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime

from ..processors.disaster_xml_processor import DisasterProcessor
from ..processors.earthquake_processor import EarthquakeProcessor
from ..processors.time_utils import TimeProcessor
from ..processors.area_code_validator import AreaCodeValidator
from ..processors.volcano_processor import VolcanoCoordinateProcessor
from common.clients.location_client import LocationClient


class UnifiedDataProcessor:
    """
    統合データ処理クラス
    
    地震情報と災害情報（噴火等）を統合的に処理し、
    XMLタイプを自動判別して適切なプロセッサーを選択する。
    """
    
    def __init__(self):
        # 各専門クラスのインスタンス化
        self.disaster_processor = DisasterProcessor()
        self.earthquake_processor = EarthquakeProcessor()
        self.time_processor = TimeProcessor()
        self.validator = AreaCodeValidator()
        self.volcano_processor = VolcanoCoordinateProcessor()
    
    def get_xml_list(self) -> List[str]:
        """
        eqvol.xmlファイルからXMLファイルURLリストを取得
        
        Returns:
            XMLファイルURLのリスト
        """
        return self.disaster_processor.get_feed_entry_urls("https://www.data.jma.go.jp/developer/xml/feed/eqvol.xml")
    
    def process_unified_data(self, url_list: List[str], output_json_path: Optional[str] = None) -> Tuple[str, str]:
        """
        複数XMLファイルから地震情報と災害情報を統合処理
        
        Args:
            url_list: 処理するXMLファイルURLリスト
            output_json_path: 出力JSONファイルパス（オプション）
            
        Returns:
            (災害情報JSON, 地震情報JSON)のタプル
        """
        disaster_urls = []
        earthquake_urls = []
        
        # XMLタイプ別にURLを分類
        for url in url_list:
            xml_data = self.disaster_processor.fetch_xml(url)
            if xml_data:
                xml_type = self.disaster_processor.detect_xml_type(xml_data)
                if xml_type == 'earthquake':
                    earthquake_urls.append(url)
                elif xml_type == 'volcano':
                    disaster_urls.append(url)
                else:
                    print(f"Unknown XML type for URL: {url}")
        
        print(f"Found {len(disaster_urls)} disaster XML files to process.")
        print(f"Found {len(earthquake_urls)} earthquake XML files to process.")
        
        # 災害情報の処理
        disaster_result = {}
        if disaster_urls:
            disaster_result = self.disaster_processor.process_multiple_urls(disaster_urls)
        
        # 地震情報の処理
        earthquake_result = {}
        if earthquake_urls:
            earthquake_result = self.earthquake_processor.process_multiple_urls(earthquake_urls)
        
        # JSON形式で出力
        disaster_json = json.dumps(disaster_result, ensure_ascii=False, indent=2)
        earthquake_json = json.dumps(earthquake_result, ensure_ascii=False, indent=2)
        
        # ファイル出力（オプション）
        if output_json_path:
            output_str = str(output_json_path)
            disaster_path = output_str.replace('.json', '_disaster.json')
            earthquake_path = output_str.replace('.json', '_earthquake.json')
            
            if disaster_result:
                self.disaster_processor.save_json(disaster_result, disaster_path)
            if earthquake_result:
                self.earthquake_processor.save_json(earthquake_result, earthquake_path)
        
        return disaster_json, earthquake_json
    
    def convert_disaster_keys_to_area_codes(self, disaster_data: Dict, area_codes_data: Dict, 
                                          output_json_path: Optional[str] = None) -> Tuple[Dict, Dict]:
        """
        災害データのエリアコード変換・無効データ除去・時間統合
        
        Args:
            disaster_data: 変換対象の災害データ
            area_codes_data: エリアコード階層データ
            output_json_path: 出力JSONファイルパス（オプション）
            
        Returns:
            (変換・統合済みの災害データ, 変換済みReportDateTime)のタプル
        """
        if not disaster_data or 'area_kind_mapping' not in disaster_data:
            return {}, {}
        
        area_kind_mapping = disaster_data['area_kind_mapping']
        volcano_coordinates = disaster_data.get('volcano_coordinates', {})
        area_report_times = disaster_data.get('area_report_times', {})
        
        converted_mapping = defaultdict(list)
        converted_report_times = {}
        invalid_codes = []
        
        # 無効なエリアコードを特定
        for disaster_key in area_kind_mapping.keys():
            if not self.validator.is_valid_area_code(disaster_key, area_codes_data, volcano_coordinates):
                invalid_codes.append(disaster_key)
        
        # 無効コードの報告
        if invalid_codes:
            print(f"\nDetected {len(invalid_codes)} invalid area codes: {invalid_codes}")
        
        # エリアコード変換処理
        for disaster_key, disaster_values in area_kind_mapping.items():
            # 無効なコードをスキップ（削除）
            if disaster_key in invalid_codes:
                print(f"Removing invalid area code: {disaster_key}")
                continue
            
            # 子コードから親コードへの変換試行
            found_area_code = self.validator.find_area_code_mapping(disaster_key, area_codes_data)
            target_key = found_area_code if found_area_code else disaster_key
            
            # データの統合
            for value in disaster_values:
                if value not in converted_mapping[target_key]:
                    converted_mapping[target_key].append(value)
            
            # ReportDateTimeの転送
            if disaster_key in area_report_times:
                converted_report_times[target_key] = area_report_times[disaster_key]
            
            if not found_area_code:
                print(f"No conversion found for: {disaster_key} (keeping original key)")
        
        if invalid_codes:
            print(f"\nSuccessfully removed {len(invalid_codes)} invalid area codes from JSON data")
        
        # 時間範囲の統合処理
        result = dict(converted_mapping)
        consolidated_result = self.time_processor.consolidate_time_ranges(result)
        
        # ファイル出力（オプション）
        if output_json_path:
            self.disaster_processor.save_json(consolidated_result, output_json_path)
        
        return consolidated_result, converted_report_times
    
    def convert_earthquake_keys_to_area_codes(self, earthquake_data: Dict, area_codes_data: Dict, 
                                          output_json_path: Optional[str] = None) -> Tuple[Dict, Dict]:
        """
        地震データのエリアコード変換・無効データ除去・時間統合
        
        Args:
            earthquake_data: 変換対象の地震データ
            area_codes_data: エリアコード階層データ
            output_json_path: 出力JSONファイルパス（オプション）
            
        Returns:
            (変換・統合済みの地震データ, 変換済みReportDateTime)のタプル
        """
        if not earthquake_data or 'area_kind_mapping' not in earthquake_data:
            return {}, {}
        
        area_kind_mapping = earthquake_data['area_kind_mapping']
        area_report_times = earthquake_data.get('area_report_times', {})
        
        converted_mapping = defaultdict(list)
        converted_report_times = {}
        invalid_codes = []
        
        # 無効なエリアコードを特定
        for earthquake_key in area_kind_mapping.keys():
            if not self.validator.is_valid_area_code(earthquake_key, area_codes_data, {}):
                invalid_codes.append(earthquake_key)
        
        # 無効コードの報告
        if invalid_codes:
            print(f"\nDetected {len(invalid_codes)} invalid area codes: {invalid_codes}")
        
        # エリアコード変換処理
        for earthquake_key, earthquake_values in area_kind_mapping.items():
            # 無効なコードをスキップ（削除）
            if earthquake_key in invalid_codes:
                print(f"Removing invalid area code: {earthquake_key}")
                continue
            
            # 子コードから親コードへの変換試行
            found_area_code = self.validator.find_area_code_mapping(earthquake_key, area_codes_data)
            target_key = found_area_code if found_area_code else earthquake_key
            
            # データの統合
            for value in earthquake_values:
                if value not in converted_mapping[target_key]:
                    converted_mapping[target_key].append(value)
            
            # ReportDateTimeの転送
            if earthquake_key in area_report_times:
                converted_report_times[target_key] = area_report_times[earthquake_key]
            
            if not found_area_code:
                print(f"No conversion found for: {earthquake_key} (keeping original key)")
        
        if invalid_codes:
            print(f"\nSuccessfully removed {len(invalid_codes)} invalid area codes from JSON data")
        
        # 時間範囲の統合処理
        result = dict(converted_mapping)
        consolidated_result = self.time_processor.consolidate_time_ranges(result)
        
        # ファイル出力（オプション）
        if output_json_path:
            self.earthquake_processor.save_json(consolidated_result, output_json_path)
        
        return consolidated_result, converted_report_times
    
    def resolve_volcano_coordinates(self, disaster_data: Dict) -> Tuple[Dict, Dict]:
        """
        火山座標の解決処理
        
        Args:
            disaster_data: 災害データ
            
        Returns:
            (更新された災害データ, 火山位置情報)のタプル
        """
        if not disaster_data:
            return {}, {}
            
        volcano_keys = list(disaster_data.get('volcano_coordinates', {}).keys())
        volcano_locations = {}
        location_client = LocationClient(debug=True)
        
        try:
            for volcano_key in volcano_keys:
                if volcano_key in disaster_data.get('volcano_coordinates', {}):
                    coord_str = disaster_data['volcano_coordinates'][volcano_key][0]
                    
                    # 座標文字列を解析
                    latitude, longitude = self.volcano_processor.parse_volcano_coordinates(coord_str)
                    if latitude and longitude:
                        print(f"Resolving location for volcano {volcano_key}: lat={latitude}, lon={longitude}")
                        
                        # LocationClientで座標解決
                        response = location_client.get_area_code_from_coordinates(
                            latitude=latitude,
                            longitude=longitude
                        )
                        
                        if response:
                            area_code = response
                            volcano_locations[volcano_key] = {
                                'latitude': latitude,
                                'longitude': longitude,
                                'area_code': area_code,
                            }

                            # 火山キーに関連する災害データを新しいエリアコードに移行
                            if volcano_key in disaster_data['area_kind_mapping'] and disaster_data['area_kind_mapping'][volcano_key]:
                                values = disaster_data['area_kind_mapping'][volcano_key]
                                
                                # エリアコードキーが存在しない場合は作成
                                if area_code not in disaster_data['area_kind_mapping']:
                                    disaster_data['area_kind_mapping'][area_code] = []
                                
                                # データを移行（重複チェック付き）
                                for value in values:
                                    if value not in disaster_data['area_kind_mapping'][area_code]:
                                        disaster_data['area_kind_mapping'][area_code].append(value)

                                print(f"[OK] Volcano {volcano_key} resolved to area code: {area_code}")
                                print(f"  移行されたデータ: {len(values)}件")
                            else:
                                print(f"[OK] Volcano {volcano_key} resolved to area code: {area_code} (データなし)")
                            
                        else:
                            print(f"[FAIL] Failed to resolve location for volcano {volcano_key}")
                            volcano_locations[volcano_key] = {
                                'latitude': latitude,
                                'longitude': longitude,
                                'area_code': None,
                                'error': 'Location resolution failed'
                            }
                        
                        # 火山データの削除（成功・失敗に関わらず）
                        if volcano_key in disaster_data['area_kind_mapping']:
                            del disaster_data['area_kind_mapping'][volcano_key]
                        if volcano_key in disaster_data['volcano_coordinates']:
                            del disaster_data['volcano_coordinates'][volcano_key]

                    else:
                        print(f"[FAIL] Failed to parse coordinates for volcano {volcano_key}: {coord_str}")
        finally:
            location_client.close()
        
        return disaster_data, volcano_locations
    
    def format_to_alert_style(self, area_kind_mapping: Dict[str, List[str]], area_report_times: Dict[str, str] = None, 
                            area_codes_data: Dict = None, data_type: str = 'disaster') -> Dict[str, Any]:
        """
        データを警報・注意報データと同じフォーマットに変換
        
        Args:
            area_kind_mapping: エリアコード別のマッピング
            area_report_times: エリアコード別のReportDateTime（オプション）
            area_codes_data: エリアコード階層データ（親コードとエリア名取得用）
            data_type: データタイプ ('disaster' or 'earthquake')
            
        Returns:
            警報・注意報データと同じフォーマットの辞書
        """
        # トップレベルの構造を初期化
        final_output = {
            f"{data_type}_pulldatetime": datetime.now().isoformat(timespec='seconds') + '+09:00',
        }
        
        for area_code, data_list in area_kind_mapping.items():
            # ユーザーの例の形式に合わせる
            final_output[area_code] = {
                data_type: data_list
            }
            
        return final_output
    
    def merge_earthquake_into_disaster(self, disaster_data: Dict[str, Any], earthquake_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        地震データを災害データに統合する
        
        Args:
            disaster_data: 災害情報データ
            earthquake_data: 地震情報データ
            
        Returns:
            地震データが災害要素に統合された辞書
        """
        # 災害データのコピーを作成
        merged_data = disaster_data.copy() if disaster_data else {}
        
        # 地震データが存在しない場合は災害データをそのまま返す
        if not earthquake_data:
            return merged_data
        
        # タイムスタンプを更新（地震データのタイムスタンプがある場合）
        if 'earthquake_pulldatetime' in earthquake_data:
            merged_data['disaster_pulldatetime'] = earthquake_data['earthquake_pulldatetime']
        
        # 各エリアコードについて地震データを災害データに統合
        for area_code, earthquake_info in earthquake_data.items():
            if area_code == 'earthquake_pulldatetime':
                continue
                
            # 地震データを取得
            earthquake_list = earthquake_info.get('earthquake', [])
            
            if earthquake_list:
                # 既存の災害データがある場合は追加、ない場合は新規作成
                if area_code in merged_data:
                    if 'disaster' not in merged_data[area_code]:
                        merged_data[area_code]['disaster'] = []
                    # 地震データを災害データに追加（重複チェック）
                    for earthquake_item in earthquake_list:
                        if earthquake_item not in merged_data[area_code]['disaster']:
                            merged_data[area_code]['disaster'].append(earthquake_item)
                else:
                    # 新規エリアコードの場合
                    merged_data[area_code] = {
                        'disaster': earthquake_list.copy()
                    }
        
        return merged_data