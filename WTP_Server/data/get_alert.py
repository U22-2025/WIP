"""
災害情報処理システム

このモジュールは気象庁のXMLデータから災害情報を取得し、
エリアコードの変換と時間範囲の統合を行います。

主な機能:
- XMLデータの取得・解析
- エリアコードの検証・変換
- 時間範囲の統合
- 無効データの除去
"""

"""
    todo : 実行時、座標解決して災害情報を格納
            656行目
"""

import re
import sys
import os
# パスを追加して直接実行にも対応
if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import requests
from common.clients.location_client import LocationClient
from typing import Optional, Dict, List, Tuple
import xml.etree.ElementTree as ET
import json
from collections import defaultdict
from datetime import datetime
import re


class XMLProcessor:
    """
    XML処理専用クラス
    
    役割:
    - 気象庁XMLデータの取得
    - XML要素の解析・抽出
    - 災害種別とエリアコードの抽出
    - 火山座標データの抽出
    - 各XMLセクション（Information、VolcanoInfo、AshInfo）の処理
    
    処理対象:
    - Head/Information: 基本的な災害情報
    - Body/VolcanoInfo: 火山情報と座標
    - Body/AshInfo: 降灰予報の時間付き情報
    """
    
    def __init__(self):
        # XML名前空間の定義
        self.ns = {
            'jmx': 'http://xml.kishou.go.jp/jmaxml1/',
            'ib': 'http://xml.kishou.go.jp/jmaxml1/informationBasis1/',
            'body': 'http://xml.kishou.go.jp/jmaxml1/body/volcanology1/',
            'jmx_eb': 'http://xml.kishou.go.jp/jmaxml1/elementBasis1/'
        }
    
    def fetch_xml(self, url: str) -> Optional[str]:
        """
        指定URLからXMLデータを取得
        
        Args:
            url: 取得するXMLのURL
            
        Returns:
            XMLデータ（文字列）、エラー時はNone
        """
        try:
            response = requests.get(url)
            response.encoding = 'utf-8'
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            print(f"Error fetching XML: {e}")
            return None
    
    def extract_kind_and_code(self, item: ET.Element) -> Tuple[Optional[str], List[str]]:
        """
        Item要素から災害種別名とエリアコードを抽出
        
        Args:
            item: XML Item要素
            
        Returns:
            (災害種別名, エリアコードリスト)のタプル
        """
        # Kind内のNameを取得（災害種別名）
        kind = item.find('ib:Kind', self.ns)
        if kind is None:
            kind = item.find('body:Kind', self.ns)
        
        kind_name = None
        if kind is not None:
            name_elem = kind.find('ib:Name', self.ns)
            if name_elem is None:
                name_elem = kind.find('body:Name', self.ns)
            if name_elem is not None and name_elem.text:
                kind_name = name_elem.text
        
        # Areas内のArea要素のCodeを取得（エリアコード）
        areas = item.find('ib:Areas', self.ns)
        if areas is None:
            areas = item.find('body:Areas', self.ns)
        
        area_codes = []
        if areas is not None:
            area_elements = areas.findall('ib:Area', self.ns)
            if not area_elements:
                area_elements = areas.findall('body:Area', self.ns)
            
            for area in area_elements:
                code_elem = area.find('ib:Code', self.ns)
                if code_elem is None:
                    code_elem = area.find('body:Code', self.ns)
                if code_elem is not None and code_elem.text:
                    area_codes.append(code_elem.text)
        
        return kind_name, area_codes
    
    def extract_volcano_coordinates(self, item: ET.Element) -> Dict[str, str]:
        """
        火山座標データを抽出
        
        Args:
            item: XML Item要素
            
        Returns:
            {火山コード: 座標データ}の辞書
        """
        coordinates = {}
        areas = item.find('body:Areas', self.ns)
        if areas is not None and areas.get('codeType') == "火山名":
            for area in areas.findall('body:Area', self.ns):
                code_elem = area.find('body:Code', self.ns)
                coordinate_elem = area.find('body:Coordinate', self.ns)
                if code_elem is not None and coordinate_elem is not None:
                    if code_elem.text and coordinate_elem.text:
                        coordinates[code_elem.text] = coordinate_elem.text
        return coordinates
    
    def process_xml_file(self, url: str) -> Tuple[Dict[str, List[str]], Dict[str, List[str]]]:
        """
        単一XMLファイルの完全処理
        
        Args:
            url: 処理するXMLファイルのURL
            
        Returns:
            (エリア-災害種別マッピング, 火山座標データ)のタプル
        """
        xml_data = self.fetch_xml(url)
        if xml_data is None:
            return {}, {}
        
        # XMLファイルの先頭にある不要な文字列を除去
        xml_start = xml_data.find('<Report')
        if xml_start != -1:
            xml_data = xml_data[xml_start:]
        
        try:
            root = ET.fromstring(xml_data)
        except ET.ParseError as e:
            print(f"Error parsing XML from {url}: {e}")
            return {}, {}
        
        area_kind_mapping = defaultdict(list)
        volcano_coordinates = defaultdict(list)
        
        # 各セクションを順次処理
        self._process_information_items(root, area_kind_mapping)
        self._process_volcano_info_items(root, area_kind_mapping, volcano_coordinates)
        self._process_ash_info_items(root, area_kind_mapping)
        
        return dict(area_kind_mapping), dict(volcano_coordinates)
    
    def _process_information_items(self, root: ET.Element, area_kind_mapping: defaultdict):
        """Head/Information内のItem要素を処理"""
        for information in root.findall('.//ib:Information', self.ns):
            for item in information.findall('ib:Item', self.ns):
                kind_name, area_codes = self.extract_kind_and_code(item)
                if kind_name:
                    for area_code in area_codes:
                        if kind_name not in area_kind_mapping[area_code]:
                            area_kind_mapping[area_code].append(kind_name)
    
    def _process_volcano_info_items(self, root: ET.Element, area_kind_mapping: defaultdict, volcano_coordinates: defaultdict):
        """Body/VolcanoInfo内のItem要素を処理"""
        for volcano_info in root.findall('.//body:VolcanoInfo', self.ns):
            for item in volcano_info.findall('body:Item', self.ns):
                kind_name, area_codes = self.extract_kind_and_code(item)
                if kind_name:
                    for area_code in area_codes:
                        if kind_name not in area_kind_mapping[area_code]:
                            area_kind_mapping[area_code].append(kind_name)
                
                # 火山座標データを取得
                coords = self.extract_volcano_coordinates(item)
                for area_code, coordinate in coords.items():
                    if coordinate not in volcano_coordinates[area_code]:
                        volcano_coordinates[area_code].append(coordinate)
    
    def _process_ash_info_items(self, root: ET.Element, area_kind_mapping: defaultdict):
        """Body/AshInfo内のItem要素を処理（時間付き情報）"""
        for ash_info in root.findall('.//body:AshInfo', self.ns):
            start_time_elem = ash_info.find('body:StartTime', self.ns)
            start_time = start_time_elem.text if start_time_elem is not None else ""
            
            for item in ash_info.findall('body:Item', self.ns):
                kind_name, area_codes = self.extract_kind_and_code(item)
                if kind_name:
                    # 時間情報を付加した災害種別名を作成
                    time_based_kind = f"{kind_name}_{start_time}" if start_time else kind_name
                    for area_code in area_codes:
                        if time_based_kind not in area_kind_mapping[area_code]:
                            area_kind_mapping[area_code].append(time_based_kind)


class TimeProcessor:
    """
    時間処理専用クラス
    
    役割:
    - 災害種別名からの時間情報抽出
    - 複数時間の範囲統合
    - 時間フォーマットの変換
    - 時間ベースのデータ統合
    
    処理パターン:
    - 個別時間: "降灰_2025-06-01T12:00:00+09:00"
    - 時間範囲: "降灰_2025/06/01-12:00から2025/06/01-15:00まで"
    - 時間なし: "降灰予報（定時）"
    """
    
    @staticmethod
    def parse_time_from_kind_name(kind_name: str) -> Tuple[Optional[str], Optional[str]]:
        """
        災害種別名から基本名と時間情報を分離
        
        Args:
            kind_name: 災害種別名（時間付きの可能性あり）
            
        Returns:
            (基本災害名, 時間情報)のタプル、時間なしの場合は(None, None)
        """
        time_pattern = r'^(.+)_(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\+\d{2}:\d{2})$'
        time_match = re.match(time_pattern, kind_name)
        if time_match:
            return time_match.group(1), time_match.group(2)
        return None, None
    
    @staticmethod
    def create_time_range(times: List[str]) -> str:
        """
        時間リストから統合された時間範囲文字列を作成
        
        Args:
            times: ISO形式の時間文字列リスト
            
        Returns:
            統合された時間範囲文字列
        """
        if len(times) == 1:
            return times[0]
        
        try:
            parsed_times = [datetime.fromisoformat(time_str) for time_str in times]
            parsed_times.sort()
            
            earliest_str = parsed_times[0].strftime("%Y/%m/%d-%H:%M")
            latest_str = parsed_times[-1].strftime("%Y/%m/%d-%H:%M")
            
            return f"{earliest_str}から{latest_str}まで"
        except Exception:
            return times[0]  # エラー時は最初の時間を返す
    
    @staticmethod
    def consolidate_time_ranges(area_kind_mapping: Dict[str, List[str]]) -> Dict[str, List[str]]:
        """
        エリア別災害種別データの時間範囲統合
        
        Args:
            area_kind_mapping: {エリアコード: [災害種別名リスト]}
            
        Returns:
            時間統合済みの{エリアコード: [統合災害種別名リスト]}
        """
        consolidated_mapping = {}
        
        for area_code, kind_names in area_kind_mapping.items():
            kind_groups = defaultdict(list)  # 災害種別ごとの時間グループ
            non_time_kinds = []  # 時間情報なしの災害種別
            
            # 災害種別を時間付きと時間なしに分類
            for kind_name in kind_names:
                base_name, time_info = TimeProcessor.parse_time_from_kind_name(kind_name)
                
                if base_name and time_info:
                    kind_groups[base_name].append(time_info)
                else:
                    non_time_kinds.append(kind_name)
            
            consolidated_kinds = []
            time_based_kinds = set(kind_groups.keys())
            
            # 時間なしの災害種別を追加（重複回避）
            for non_time_kind in non_time_kinds:
                if non_time_kind not in time_based_kinds:
                    consolidated_kinds.append(non_time_kind)
            
            # 時間付きの災害種別を統合処理
            for base_name, time_list in kind_groups.items():
                unique_times = list(set(time_list))  # 重複時間を除去
                time_range = TimeProcessor.create_time_range(unique_times)
                consolidated_kinds.append(f"{base_name}_{time_range}")
            
            consolidated_mapping[area_code] = consolidated_kinds
        
        return consolidated_mapping


class AreaCodeValidator:
    """
    エリアコード検証・変換クラス
    
    役割:
    - エリアコードの有効性検証
    - 子コードから親コードへのマッピング
    - 火山コードとエリアコードの統合検証
    - 無効コードの特定
    
    検証対象:
    - area_codes.json内の正式エリアコード
    - volcano_coordinates内の火山コード
    - 子コードから親コードへの変換
    """
    
    @staticmethod
    def is_valid_area_code(code: str, area_codes_data: Dict, volcano_coordinates: Dict) -> bool:
        """
        エリアコードの有効性を検証
        
        Args:
            code: 検証対象のコード
            area_codes_data: 正式エリアコードデータ
            volcano_coordinates: 火山座標データ
            
        Returns:
            有効な場合True、無効な場合False
        """
        # 火山座標に存在する場合は有効
        if code in volcano_coordinates:
            return True
        
        # area_codes_dataに存在するかチェック
        for office_data in area_codes_data.values():
            for area_code, children_codes in office_data.items():
                if code == area_code or code in children_codes:
                    return True
        return False
    
    @staticmethod
    def find_area_code_mapping(child_code: str, area_codes_data: Dict) -> Optional[str]:
        """
        子コードに対応する親エリアコードを検索
        
        Args:
            child_code: 検索する子コード
            area_codes_data: エリアコード階層データ
            
        Returns:
            対応する親エリアコード、見つからない場合はNone
        """
        for office_data in area_codes_data.values():
            for area_code, children_codes in office_data.items():
                if child_code in children_codes:
                    return area_code
        return None


class DisasterDataProcessor:
    """
    災害データ処理統合クラス（メインコントローラー）
    
    役割:
    - 全体的な処理フローの制御
    - 各専門クラスの連携調整
    - ファイル入出力の管理
    - エラーハンドリング
    - データ変換・統合の統括
    
    処理フロー:
    1. XMLファイルリストの取得
    2. 各XMLファイルの処理・統合
    3. エリアコードの検証・変換
    4. 時間範囲の統合
    5. 結果ファイルの出力
    """
    
    def __init__(self):
        # 各専門クラスのインスタンス化
        self.xml_processor = XMLProcessor()
        self.time_processor = TimeProcessor()
        self.validator = AreaCodeValidator()
    
    def get_disaster_xml_list(self) -> List[str]:
        """
        disaster.xmlファイルからXMLファイルURLリストを取得
        
        Returns:
            XMLファイルURLのリスト
        """
        try:
            url = "https://www.data.jma.go.jp/developer/xml/feed/eqvol.xml"
            response = requests.get(url)
            response.encoding = 'utf-8'
            response.raise_for_status()
            xml_data = response.text
            
            # XMLファイルの先頭調整
            xml_start = xml_data.find('<feed')
            if xml_start != -1:
                xml_data = xml_data[xml_start:]
            
            ns = {'atom': 'http://www.w3.org/2005/Atom'}
            root = ET.fromstring(xml_data)
            
            url_list = []
            for entry in root.findall('atom:entry', ns):
                id_elem = entry.find('atom:id', ns)
                if id_elem is not None and id_elem.text:
                    url_list.append(id_elem.text)
            
            print(f"Found {len(url_list)} entry IDs")
            return url_list
            
        except (FileNotFoundError, ET.ParseError) as e:
            print(f"Error reading disaster.xml: {e}")
            return []
    
    def get_disaster_info(self, url_list: List[str], output_json_path: Optional[str] = None) -> str:
        """
        複数XMLファイルから災害情報を取得・統合
        
        Args:
            url_list: 処理するXMLファイルURLリスト
            output_json_path: 出力JSONファイルパス（オプション）
            
        Returns:
            統合された災害情報JSON文字列
        """
        all_area_mapping = defaultdict(list)
        all_volcano_coords = defaultdict(list)
        
        # 各XMLファイルを順次処理
        for url in url_list:
            area_mapping, volcano_coords = self.xml_processor.process_xml_file(url)
            
            # エリア-災害種別マッピングの統合
            for area_code, kind_names in area_mapping.items():
                for kind_name in kind_names:
                    if kind_name not in all_area_mapping[area_code]:
                        all_area_mapping[area_code].append(kind_name)
            
            # 火山座標データの統合
            for area_code, coordinates in volcano_coords.items():
                for coordinate in coordinates:
                    if coordinate not in all_volcano_coords[area_code]:
                        all_volcano_coords[area_code].append(coordinate)
        
        # 最終データの構築
        result = {
            "area_kind_mapping": dict(all_area_mapping),
            "volcano_coordinates": dict(all_volcano_coords)
        }
        
        json_output = json.dumps(result, ensure_ascii=False, indent=2)
        
        # ファイル出力（オプション）
        if output_json_path:
            try:
                with open(output_json_path, 'w', encoding='utf-8') as json_file:
                    json_file.write(json_output)
                print(f"JSON data saved to: {output_json_path}")
            except Exception as e:
                print(f"Error saving JSON file: {e}")
        
        return json_output
    
    def convert_disaster_keys_to_area_codes(self, disaster_data: Dict, area_codes_data: Dict, 
                                          output_json_path: Optional[str] = None) -> Dict:
        """
        災害データのエリアコード変換・無効データ除去・時間統合
        
        Args:
            disaster_data: 変換対象の災害データ
            area_codes_data: エリアコード階層データ
            output_json_path: 出力JSONファイルパス（オプション）
            
        Returns:
            変換・統合済みの災害データ
        """
        if 'area_kind_mapping' not in disaster_data:
            print("Warning: 'area_kind_mapping' key not found in disaster data")
            return {}
        
        area_kind_mapping = disaster_data['area_kind_mapping']
        volcano_coordinates = disaster_data.get('volcano_coordinates', {})
        converted_mapping = defaultdict(list)
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
            
            if not found_area_code:
                print(f"No conversion found for: {disaster_key} (keeping original key)")
        
        if invalid_codes:
            print(f"\nSuccessfully removed {len(invalid_codes)} invalid area codes from JSON data")
        
        # 時間範囲の統合処理
        result = dict(converted_mapping)
        consolidated_result = self.time_processor.consolidate_time_ranges(result)
        
        # ファイル出力（オプション）
        if output_json_path:
            try:
                with open(output_json_path, 'w', encoding='utf-8') as json_file:
                    json.dump(consolidated_result, json_file, ensure_ascii=False, indent=2)
            except Exception as e:
                print(f"Error saving converted JSON file: {e}")
        
        return consolidated_result
    
    @staticmethod
    def convert_child_to_area(json_data: Dict) -> List[str]:
        """
        火山座標データからキーリストを取得
        
        Args:
            json_data: 災害データJSON
            
        Returns:
            火山コードのリスト
        """
        if 'volcano_coordinates' not in json_data:
            print("Warning: 'volcano_coordinates' key not found in JSON data")
            return []
        return list(json_data['volcano_coordinates'].keys())
    
    @staticmethod
    def parse_volcano_coordinates(coord_str: str) -> Tuple[Optional[float], Optional[float]]:
        """
        火山座標文字列を緯度経度に変換
        
        Args:
            coord_str: 座標文字列 (例: "+2938.30+12942.83+796/")
            
        Returns:
            (緯度, 経度)のタプル、解析失敗時は(None, None)
        """
        try:
            # 座標文字列の形式: "+DDMM.MM+DDDMM.MM+標高/"
            # 最後の「/」を除去
            coord_str = coord_str.rstrip('/')
            
            # 正規表現で緯度、経度、標高を抽出
            pattern = r'([+-]\d{4}\.\d{2})([+-]\d{5}\.\d{2})([+-]\d+)'
            match = re.match(pattern, coord_str)
            
            if not match:
                print(f"座標文字列の形式が不正です: {coord_str}")
                return None, None
            
            lat_str, lon_str, alt_str = match.groups()
            
            # 緯度の変換 (DDMM.MM -> DD.DDDD)
            lat_sign = 1 if lat_str[0] == '+' else -1
            lat_abs = lat_str[1:]
            lat_degrees = int(lat_abs[:2])
            lat_minutes = float(lat_abs[2:])
            latitude = lat_sign * (lat_degrees + lat_minutes / 60.0)
            # 緯度を6桁の精度に丸める
            latitude = round(latitude, 6)
            
            # 経度の変換 (DDDMM.MM -> DDD.DDDD)
            lon_sign = 1 if lon_str[0] == '+' else -1
            lon_abs = lon_str[1:]
            lon_degrees = int(lon_abs[:3])
            lon_minutes = float(lon_abs[3:])
            longitude = lon_sign * (lon_degrees + lon_minutes / 60.0)
            # 経度を6桁の精度に丸める
            longitude = round(longitude, 6)
            
            return latitude, longitude
            
        except Exception as e:
            print(f"座標解析エラー: {e}, 座標文字列: {coord_str}")
            return None, None


def main():
    """
    メイン処理関数
    
    処理フロー:
    1. 災害XMLファイルリストの取得
    2. 各XMLファイルからの災害情報抽出・統合
    3. 火山座標の解決処理
    4. エリアコードデータの読み込み
    5. エリアコード変換・無効データ除去
    6. 時間範囲統合
    7. 結果ファイルの出力
    """
    try:
        processor = DisasterDataProcessor()
        
        # Step 1: XMLファイルリストの取得
        url_list = processor.get_disaster_xml_list()
        if not url_list:
            print("No URLs found. Exiting.")
            return
        
        # Step 2: 災害情報の取得・統合
        json_result = processor.get_disaster_info(url_list, 'wtp/json/disaster_data.json')
        print("\n=== Disaster Info Processing Complete ===")
        
        # Step 3: 火山座標キーの取得
        result_dict = json.loads(json_result)
        volcano_keys = processor.convert_child_to_area(result_dict)
        print(f"Volcano Coordinate Keys: {volcano_keys}")

        ### volcano_keyの座標解決処理
        
        # Step 3.1: 火山座標の解決処理
        location_client = LocationClient(debug=True)
        volcano_locations = {}
        
        try:
            for volcano_key in volcano_keys:
                if volcano_key in result_dict.get('volcano_coordinates', {}):
                    coord_str = result_dict['volcano_coordinates'][volcano_key][0]
                    
                    # 座標文字列を解析 (例: "+2938.30+12942.83+796/")
                    latitude, longitude = processor.parse_volcano_coordinates(coord_str)
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
                            if volcano_key in result_dict['area_kind_mapping'] and result_dict['area_kind_mapping'][volcano_key]:
                                values = result_dict['area_kind_mapping'][volcano_key]
                                
                                # エリアコードキーが存在しない場合は作成
                                if area_code not in result_dict['area_kind_mapping']:
                                    result_dict['area_kind_mapping'][area_code] = []
                                
                                # データを移行（重複チェック付き）
                                for value in values:
                                    if value not in result_dict['area_kind_mapping'][area_code]:
                                        result_dict['area_kind_mapping'][area_code].append(value)

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
                        if volcano_key in result_dict['area_kind_mapping']:
                            del result_dict['area_kind_mapping'][volcano_key]
                        if volcano_key in result_dict['volcano_coordinates']:
                            del result_dict['volcano_coordinates'][volcano_key]


                    else:
                        print(f"✗ Failed to parse coordinates for volcano {volcano_key}: {coord_str}")
        finally:
            location_client.close()
        
        print(f"\nVolcano Location Resolution Results: {json.dumps(volcano_locations, ensure_ascii=False, indent=2)}")
        
        # Step 4: エリアコードデータの読み込み
        with open('wtp/json/area_codes.json', 'r', encoding='utf-8') as f:
            area_codes_data = json.load(f)
        
        # Step 5: エリアコード変換・統合処理
        converted_data = processor.convert_disaster_keys_to_area_codes(
            result_dict, area_codes_data, 'wtp/json/disaster_data.json'
        )
        
        # Step 6: 最終結果の保存（火山位置情報を追加）
        updated_disaster_data = {
            "area_kind_mapping": converted_data,
            "volcano_coordinates": result_dict.get("volcano_coordinates", {}),
        }
        
        with open('wtp/json/disaster_data.json', 'w', encoding='utf-8') as f:
            json.dump(updated_disaster_data, f, ensure_ascii=False, indent=2)
        
        print("Processing completed successfully.")
        
    except Exception as e:
        print(f"Error in main processing: {e}")


if __name__ == "__main__":
    main()
