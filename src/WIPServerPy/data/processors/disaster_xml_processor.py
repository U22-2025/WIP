"""Disaster XML processing utilities."""

import xml.etree.ElementTree as ET
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Optional, Dict, List, Tuple, Any

from WIPCommonPy.clients.location_client import LocationClient
from WIPCommonPy.packet import LocationRequest, LocationResponse
from WIPCommonPy.clients.utils.packet_id_generator import PacketIDGenerator12Bit

from WIPServerPy.data.xml_base import XMLBaseProcessor

class DisasterProcessor(XMLBaseProcessor):
    """
    災害情報処理クラス
    
    気象庁の災害XMLデータを処理し、
    エリアコード別に災害情報と火山座標データを整理する。
    """
    
    def process_xml_data(self, xml_data: str) -> Dict[str, Any]:
        """
        単一XMLファイルから災害情報を抽出し、エリアコード別のマッピングと火山座標データを返す
        
        Args:
            xml_data: 処理するXMLデータ
            
        Returns:
            エリアコード別の災害情報と火山座標データを含む辞書
        """
        root = self.parse_xml(xml_data, '<Report')
        if root is None:
            return {"area_kind_mapping": {}, "volcano_coordinates": {}}
        
        area_kind_mapping = defaultdict(list)
        volcano_coordinates = defaultdict(list)
        
        # 各セクションを順次処理
        self._process_information_items(root, area_kind_mapping)
        self._process_volcano_info_items(root, area_kind_mapping, volcano_coordinates)
        self._process_ash_info_items(root, area_kind_mapping)
        
        return {
            "area_kind_mapping": dict(area_kind_mapping),
            "volcano_coordinates": dict(volcano_coordinates)
        }
    
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
    
    def _process_single_url(self, url: str) -> Optional[Dict[str, Any]]:
        """
        単一URLからXMLデータを取得し、処理するヘルパーメソッド
        
        Args:
            url: 処理対象のXML URL
            
        Returns:
            処理結果またはNone
        """
        # 基本処理を親クラスで実行
        base_result = super()._process_single_url_base(url)
        if base_result is None:
            return None
            
        # 災害特有の処理を実行
        result = self.process_xml_data(base_result["xml_data"])
        result["report_date_time"] = base_result["report_time"]
        return result

    def process_multiple_urls(self, url_list: List[str]) -> Dict[str, Any]:
        """
        複数のXMLファイルから災害情報を統合処理（並列化版）
        
        Args:
            url_list: 処理するXMLファイルURLのリスト
            
        Returns:
            統合された災害情報
        """
        all_area_kind_mapping = defaultdict(list)
        all_volcano_coordinates = defaultdict(list)
        all_area_report_times = {}
        
        with ThreadPoolExecutor(max_workers=10) as executor:
            # 各URLの処理を並列実行
            results = executor.map(self._process_single_url, url_list)
            
            # 結果を統合
            for result in results:
                if result is None:
                    continue
                
                area_mapping = result["area_kind_mapping"]
                volcano_coords = result["volcano_coordinates"]
                report_date_time = result.get("report_date_time")
                
                # エリア-災害種別マッピングの統合
                for area_code, kind_names in area_mapping.items():
                    for kind_name in kind_names:
                        if kind_name not in all_area_kind_mapping[area_code]:
                            all_area_kind_mapping[area_code].append(kind_name)
                    if report_date_time:
                        all_area_report_times[area_code] = report_date_time
                
                # 火山座標データの統合
                for area_code, coordinates in volcano_coords.items():
                    for coordinate in coordinates:
                        if coordinate not in all_volcano_coordinates[area_code]:
                            all_volcano_coordinates[area_code].append(coordinate)
                    if report_date_time:
                        all_area_report_times[area_code] = report_date_time
        
        return {
            "area_kind_mapping": dict(all_area_kind_mapping),
            "volcano_coordinates": dict(all_volcano_coordinates),
            "area_report_times": all_area_report_times,
            "disaster_pulldatetime": datetime.now().isoformat(timespec='seconds') + '+09:00',
        }


