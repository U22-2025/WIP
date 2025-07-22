"""Earthquake XML processing utilities."""

import xml.etree.ElementTree as ET
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Optional, Dict, List, Tuple, Any

from WIPServerPy.data.xml_base import XMLBaseProcessor


class EarthquakeProcessor(XMLBaseProcessor):
    """
    地震情報処理クラス
    
    気象庁の地震XMLデータを処理し、
    エリアコード別に地震情報を整理する。
    """
    
    def process_xml_data(self, xml_data: str) -> Dict[str, Any]:
        """
        単一XMLファイルから地震情報を抽出し、エリアコード別のマッピングを返す
        
        Args:
            xml_data: 処理するXMLデータ
            
        Returns:
            エリアコード別の地震情報を含む辞書
        """
        root = self.parse_xml(xml_data, '<Report')
        if root is None:
            return {"area_kind_mapping": {}}
        
        area_kind_mapping = defaultdict(list)
        
        # 地震情報を処理
        self._process_earthquake_info(root, area_kind_mapping)
        
        return {
            "area_kind_mapping": dict(area_kind_mapping)
        }
    
    def _process_earthquake_info(self, root: ET.Element, area_kind_mapping: defaultdict):
        """地震情報を処理"""
        # 名前空間の定義
        ns = {
            'jmaxml': 'http://xml.kishou.go.jp/jmaxml1/',
            'ib': 'http://xml.kishou.go.jp/jmaxml1/informationBasis1/',
            'body': 'http://xml.kishou.go.jp/jmaxml1/body/seismology1/',
            'jmx_eb': 'http://xml.kishou.go.jp/jmaxml1/elementBasis1/'
        }
        
        # Head情報から地震情報の種別を取得
        head = root.find('.//ib:Head', ns)
        if head is None:
            return
            
        info_kind = head.find('ib:InfoKind', ns)
        info_kind_text = info_kind.text if info_kind is not None else "地震情報"
        
        # 地震の基本情報を取得
        earthquake = root.find('.//body:Earthquake', ns)
        earthquake_info = None
        origin_time = None
        hypocenter_name = None
        
        if earthquake is not None:
            # 地震発生時刻を取得
            origin_time_elem = earthquake.find('body:OriginTime', ns)
            if origin_time_elem is not None:
                origin_time = origin_time_elem.text
                # 日時を短縮形式に変換 (例: 2025-07-18T08:20:00+09:00 → 07/18_08:20)
                try:
                    from datetime import datetime
                    dt = datetime.fromisoformat(origin_time.replace('Z', '+00:00'))
                    origin_time_short = dt.strftime('%m/%d_%H:%M')
                except:
                    origin_time_short = origin_time
            else:
                origin_time_short = "不明"
            
            magnitude_elem = earthquake.find('jmx_eb:Magnitude', ns)
            magnitude = magnitude_elem.text if magnitude_elem is not None else "不明"
            
            # 震源地情報を取得
            hypocenter = earthquake.find('body:Hypocenter', ns)
            if hypocenter is not None:
                area = hypocenter.find('body:Area', ns)
                if area is not None:
                    hypocenter_name_elem = area.find('body:Name', ns)
                    hypocenter_name = hypocenter_name_elem.text if hypocenter_name_elem is not None else "不明"
                    
                    # 震源地情報を含む地震情報を作成（日時を含む）
                    earthquake_info = f"{info_kind_text}({origin_time_short}_M{magnitude}_{hypocenter_name})"
        
        # 震度情報を処理
        intensity = root.find('.//body:Intensity', ns)
        if intensity is not None:
            observation = intensity.find('body:Observation', ns)
            if observation is not None:
                # 都道府県レベルの震度情報を処理
                prefs = observation.findall('body:Pref', ns)
                for pref in prefs:
                    pref_code_elem = pref.find('body:Code', ns)
                    pref_max_int_elem = pref.find('body:MaxInt', ns)
                    
                    if pref_code_elem is not None and pref_max_int_elem is not None:
                        pref_code = pref_code_elem.text
                        max_intensity = pref_max_int_elem.text
                        
                        # 震度情報を作成
                        intensity_info = f"震度{max_intensity}"
                        
                        # 地震情報と震度情報を統合
                        if earthquake_info:
                            combined_info = f"{earthquake_info}_{intensity_info}"
                        else:
                            combined_info = f"{info_kind_text}_{intensity_info}"
                        
                        # エリアコード別に情報を追加
                        if combined_info not in area_kind_mapping[pref_code]:
                            area_kind_mapping[pref_code].append(combined_info)
                    
                    # 細分区域レベルの震度情報を処理
                    areas = pref.findall('body:Area', ns)
                    for area in areas:
                        area_code_elem = area.find('body:Code', ns)
                        area_max_int_elem = area.find('body:MaxInt', ns)
                        
                        if area_code_elem is not None and area_max_int_elem is not None:
                            area_code = area_code_elem.text
                            max_intensity = area_max_int_elem.text
                            
                            # 震度情報を作成
                            intensity_info = f"震度{max_intensity}"
                            
                            # 地震情報と震度情報を統合
                            if earthquake_info:
                                combined_info = f"{earthquake_info}_{intensity_info}"
                            else:
                                combined_info = f"{info_kind_text}_{intensity_info}"
                            
                            # エリアコード別に情報を追加
                            if combined_info not in area_kind_mapping[area_code]:
                                area_kind_mapping[area_code].append(combined_info)
                        
                        # 市町村レベルの震度情報を処理
                        cities = area.findall('body:City', ns)
                        for city in cities:
                            city_code_elem = city.find('body:Code', ns)
                            city_max_int_elem = city.find('body:MaxInt', ns)
                            
                            if city_code_elem is not None and city_max_int_elem is not None:
                                city_code = city_code_elem.text
                                max_intensity = city_max_int_elem.text
                                
                                # 震度情報を作成
                                intensity_info = f"震度{max_intensity}"
                                
                                # 地震情報と震度情報を統合
                                if earthquake_info:
                                    combined_info = f"{earthquake_info}_{intensity_info}"
                                else:
                                    combined_info = f"{info_kind_text}_{intensity_info}"
                                
                                # エリアコード別に情報を追加
                                if combined_info not in area_kind_mapping[city_code]:
                                    area_kind_mapping[city_code].append(combined_info)
    
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
            
        # 地震特有の処理を実行
        result = self.process_xml_data(base_result["xml_data"])
        result["report_date_time"] = base_result["report_time"]
        return result

    def process_multiple_urls(self, url_list: List[str]) -> Dict[str, Any]:
        """
        複数のXMLファイルから地震情報を統合処理（並列化版）
        
        Args:
            url_list: 処理するXMLファイルURLのリスト
            
        Returns:
            統合された地震情報
        """
        all_area_kind_mapping = defaultdict(list)
        all_area_report_times = {}
        
        with ThreadPoolExecutor(max_workers=10) as executor:
            # 各URLの処理を並列実行
            results = executor.map(self._process_single_url, url_list)
            
            # 結果を統合
            for result in results:
                if result is None:
                    continue
                
                area_mapping = result["area_kind_mapping"]
                report_date_time = result.get("report_date_time")
                
                # エリア-地震情報マッピングの統合
                for area_code, kind_names in area_mapping.items():
                    for kind_name in kind_names:
                        if kind_name not in all_area_kind_mapping[area_code]:
                            all_area_kind_mapping[area_code].append(kind_name)
                    if report_date_time:
                        all_area_report_times[area_code] = report_date_time
        
        # 重複地震情報の統合処理
        consolidated_area_mapping = {}
        for area_code, kind_names in all_area_kind_mapping.items():
            consolidated_area_mapping[area_code] = self._consolidate_duplicate_earthquakes(kind_names)
        
        return {
            "area_kind_mapping": consolidated_area_mapping,
            "area_report_times": all_area_report_times,
            "disaster_pulldatetime": datetime.now().isoformat(timespec='seconds') + '+09:00',
        }
    
    def _consolidate_duplicate_earthquakes(self, earthquake_list: List[str]) -> List[str]:
        """
        重複する地震情報を統合する
        
        Args:
            earthquake_list: 地震情報のリスト
            
        Returns:
            統合された地震情報のリスト
        """
        # 地震情報を震源地別にグループ化
        earthquake_groups = defaultdict(list)
        non_earthquake_items = []
        
        for item in earthquake_list:
            if "地震情報(" in item:
                # 震源地を抽出
                location = self._extract_location(item)
                if location:
                    earthquake_groups[location].append(item)
                else:
                    non_earthquake_items.append(item)
            else:
                non_earthquake_items.append(item)
        
        # 各グループを統合
        consolidated_items = []
        for location, items in earthquake_groups.items():
            if len(items) > 1:
                # 重複がある場合は統合
                consolidated_items.append(self._merge_earthquake_entries(items, location))
            else:
                # 重複がない場合はそのまま
                consolidated_items.extend(items)
        
        # 地震情報以外の項目を追加
        consolidated_items.extend(non_earthquake_items)
        
        return consolidated_items
    
    def _extract_location(self, earthquake_entry: str) -> str:
        """
        地震情報から震源地を抽出
        
        Args:
            earthquake_entry: 地震情報文字列
            
        Returns:
            震源地名
        """
        # 例: "地震情報(07/18_22:12_M2.5_トカラ列島近海)_震度1"
        if "地震情報(" in earthquake_entry:
            start_idx = earthquake_entry.find("地震情報(")
            end_idx = earthquake_entry.find(")", start_idx)
            if start_idx != -1 and end_idx != -1:
                content = earthquake_entry[start_idx+4:end_idx]  # "地震情報("の後から")"の前まで
                parts = content.split("_")
                # 最後の部分が震源地（例: "トカラ列島近海"）
                if len(parts) >= 4:
                    return parts[-1]
        return ""
    
    def _merge_earthquake_entries(self, earthquake_entries: List[str], location: str) -> str:
        """
        同じ震源地の地震情報を統合
        
        Args:
            earthquake_entries: 統合する地震情報のリスト
            location: 震源地名
            
        Returns:
            統合された地震情報文字列
        """
        if not earthquake_entries:
            return ""
        
        # 各地震情報から日時、マグニチュード、震度を抽出
        earthquake_details = []
        
        for entry in earthquake_entries:
            details = self._extract_earthquake_details(entry)
            if details:
                earthquake_details.append(details)
        
        # 時系列順にソート
        earthquake_details.sort(key=lambda x: x['time'])
        
        # 統合された文字列を作成
        # 例: "地震情報_トカラ列島近海(07/18_20:43_M2.9_震度1)(07/18_14:29_M3.1_震度3)"
        detail_strings = []
        for detail in earthquake_details:
            detail_str = f"({detail['time']}_M{detail['magnitude']}_{detail['intensity']})"
            detail_strings.append(detail_str)
        
        combined_details = "".join(detail_strings)
        return f"地震情報_{location}{combined_details}"
    
    def _extract_earthquake_details(self, earthquake_entry: str) -> Dict[str, str]:
        """
        地震情報から詳細情報を抽出
        
        Args:
            earthquake_entry: 地震情報文字列
            
        Returns:
            詳細情報の辞書
        """
        # 例: "地震情報(07/18_22:12_M2.5_トカラ列島近海)_震度1"
        details = {'time': '', 'magnitude': '', 'intensity': ''}
        
        if "地震情報(" in earthquake_entry:
            # 括弧内の情報を抽出
            start_idx = earthquake_entry.find("地震情報(")
            end_idx = earthquake_entry.find(")", start_idx)
            if start_idx != -1 and end_idx != -1:
                content = earthquake_entry[start_idx+4:end_idx]
                parts = content.split("_")
                
                # 日時を抽出（例: "07/18_22:12"）
                if len(parts) >= 2:
                    details['time'] = f"{parts[0]}_{parts[1]}"
                
                # マグニチュードを抽出（例: "M2.5"）
                for part in parts:
                    if part.startswith("M"):
                        details['magnitude'] = part[1:]  # "M"を除く
                        break
            
            # 震度を抽出（例: "震度1"）
            if "_震度" in earthquake_entry:
                intensity_part = earthquake_entry.split("_震度")[-1]
                details['intensity'] = f"震度{intensity_part}"
        
        return details if all(details.values()) else None