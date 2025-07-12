"""High level disaster data processing controller."""

import json
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime

from common.clients.location_client import LocationClient

from ..processors.disaster_xml_processor import DisasterProcessor
from ..processors.time_utils import TimeProcessor
from ..processors.area_code_validator import AreaCodeValidator
from ..processors.volcano_processor import VolcanoCoordinateProcessor

class DisasterDataProcessor:
    """
    災害データ処理統合クラス（メインコントローラー）
    
    役割:
    - 全体的な処理フローの制御
    - 各専門クラスの連携調整
    - ファイル入出力の管理
    - エラーハンドリング
    - データ変換・統合の統括
    """
    
    def __init__(self):
        # 各専門クラスのインスタンス化
        self.xml_processor = DisasterProcessor()
        self.time_processor = TimeProcessor()
        self.validator = AreaCodeValidator()
        self.volcano_processor = VolcanoCoordinateProcessor()
    
    def get_disaster_xml_list(self) -> List[str]:
        """
        disaster.xmlファイルからXMLファイルURLリストを取得
        
        Returns:
            XMLファイルURLのリスト
        """
        return self.xml_processor.get_feed_entry_urls("https://www.data.jma.go.jp/developer/xml/feed/eqvol.xml")
    
    def get_disaster_info(self, url_list: List[str], output_json_path: Optional[str] = None) -> str:
        """
        複数XMLファイルから災害情報を取得・統合
        
        Args:
            url_list: 処理するXMLファイルURLリスト
            output_json_path: 出力JSONファイルパス（オプション）
            
        Returns:
            統合された災害情報JSON文字列
        """
        result = self.xml_processor.process_multiple_urls(url_list)
        json_output = json.dumps(result, ensure_ascii=False, indent=2)
        
        # ファイル出力（オプション）
        if output_json_path:
            self.xml_processor.save_json(result, output_json_path)
        
        return json_output
    
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
        if 'area_kind_mapping' not in disaster_data:
            print("Warning: 'area_kind_mapping' key not found in disaster data")
            return {}, {}
        
        area_kind_mapping = disaster_data['area_kind_mapping']
        print(f"Debug: type of area_kind_mapping: {type(area_kind_mapping)}")
        print(f"Debug: area_kind_mapping is None: {area_kind_mapping is None}")
        if area_kind_mapping is None:
            print("Error: area_kind_mapping is None. Returning empty dicts.")
            return {}, {}
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
            self.xml_processor.save_json(consolidated_result, output_json_path)
        
        return consolidated_result, converted_report_times
    
    def format_to_alert_style(self, area_kind_mapping: Dict[str, List[str]], area_report_times: Dict[str, str] = None, area_codes_data: Dict = None) -> Dict[str, Any]:
        """
        災害データを警報・注意報データと同じフォーマットに変換
        
        Args:
            area_kind_mapping: エリアコード別の災害種別マッピング
            area_report_times: エリアコード別のReportDateTime（オプション）
            area_codes_data: エリアコード階層データ（親コードとエリア名取得用）
            
        Returns:
            警報・注意報データと同じフォーマットの辞書
        """

        # トップレベルの構造を初期化
        final_output = {
            "disaster_pulldatetime": datetime.now().isoformat(timespec='seconds') + '+09:00',
        }
        
        for area_code, disaster_list in area_kind_mapping.items():
            # ユーザーの例の形式に合わせる
            final_output[area_code] = {
                "disaster": disaster_list # 災害情報
            }
            
        print(final_output)
        return final_output
    
    def resolve_volcano_coordinates(self, disaster_data: Dict) -> Tuple[Dict, Dict]:
        """
        火山座標の解決処理
        
        Args:
            disaster_data: 災害データ
            
        Returns:
            (更新された災害データ, 火山位置情報)のタプル
        """
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

                                print(f"✓ Volcano {volcano_key} resolved to area code: {area_code}")
                                print(f"  移行されたデータ: {len(values)}件")
                            else:
                                print(f"✓ Volcano {volcano_key} resolved to area code: {area_code} (データなし)")
                            
                        else:
                            print(f"✗ Failed to resolve location for volcano {volcano_key}")
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
                        print(f"✗ Failed to parse coordinates for volcano {volcano_key}: {coord_str}")
        finally:
            location_client.close()
        
        return disaster_data, volcano_locations


