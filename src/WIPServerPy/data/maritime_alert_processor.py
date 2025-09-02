"""
海上警報・注意報情報処理モジュール

気象庁のother.xmlから海上警報・注意報XMLデータを処理し、エリアコード別に情報を整理する。

主な機能:
- other.xml フィードから海上警報・注意報XMLデータの取得・解析
- URL の重複排除処理
- sea.xml, all_sea.xml 形式のXMLファイルの解析
- エリアコード別の海上警報・注意報情報の抽出
- 既存の警報処理システムとの統合

使用方法:
    from maritime_alert_processor import MaritimeAlertProcessor
    processor = MaritimeAlertProcessor()
    alerts = processor.process_maritime_alerts()
"""

import sys
from pathlib import Path
import sys
import os

# プロジェクトルートをパスに追加 (モジュールとして実行時も有効)
current_file = Path(__file__).absolute()
project_root = str(current_file.parent.parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# xml_baseモジュールのインポート用に追加パス設定
sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

import xml.etree.ElementTree as ET
from collections import defaultdict
from typing import Dict, List, Any, Optional, Set
from WIPServerPy.data.xml_base import XMLBaseProcessor
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
from WIPCommonPy.clients.location_client import LocationClient


class MaritimeAlertProcessor(XMLBaseProcessor):
    """
    海上警報・注意報情報処理クラス

    気象庁のother.xmlフィードから海上警報・注意報XMLデータを処理し、
    エリアコード別に警報・注意報情報を整理する。
    """

    def __init__(self):
        super().__init__()
        # 海上警報・注意報の対象情報種別
        self.maritime_warning_types = [
            "地方海上警報",
            "地方海上予報", 
            "全般海上警報"
        ]
        
        # エリアコード構造データを読み込み
        self.area_codes_data = self._load_area_codes_data()
        
        # LocationClientの初期化（座標解決用）
        self.location_client = None
        
        # 海域コードから都道府県コードへのマッピング
        self.sea_area_code_mapping = {
            "9010": ["010000", "020000", "030000", "040000", "050000", "060000", "070000", "150000", "160000", "170000"],  # 日本海 -> 北海道〜新潟の日本海側
            "9020": ["130000", "140000", "230000", "240000"],  # ボッ海 -> 関東・中部の太平洋側
            "9030": ["260000", "270000", "280000", "290000", "300000", "310000", "320000", "330000", "340000", "350000", "360000", "370000"],  # 黄海 -> 近畿・中国・四国
            "9050": ["010000", "020000", "030000"],  # オホーツク海 -> 北海道・東北北部
        }

    def get_maritime_alert_xml_list(self) -> List[str]:
        """
        other.xmlフィードから海上警報・注意報XMLファイルのURLリストを取得

        Returns:
            XMLファイルURLのリスト（重複排除済み）
        """
        print("Fetching maritime alert XML list from other.xml feed...")
        url_list = self.get_feed_entry_urls(
            "https://www.data.jma.go.jp/developer/xml/feed/other.xml"
        )
        
        # 重複排除
        unique_urls = list(set(url_list))
        print(f"Found {len(url_list)} total URLs, {len(unique_urls)} unique URLs")
        
        return unique_urls

    def _load_area_codes_data(self) -> Dict[str, Dict[str, List[str]]]:
        """
        エリアコード構造データを読み込み

        Returns:
            エリアコード階層データ
        """
        try:
            # プロジェクトルートからarea_codes.jsonを探す
            possible_paths = [
                Path(__file__).parent.parent.parent.parent / "docs" / "area_codes.json",
                Path(__file__).parent.parent.parent.parent / "python" / "WIP_Server" / "json" / "area_codes.json"
            ]
            
            for path in possible_paths:
                if path.exists():
                    with open(path, 'r', encoding='utf-8') as f:
                        return json.load(f)
            
            print("Warning: area_codes.json not found, using empty structure")
            return {}
            
        except Exception as e:
            print(f"Error loading area codes data: {e}")
            return {}

    def _get_class10_codes_for_prefecture(self, prefecture_code: str) -> List[str]:
        """
        都道府県コードに対応するclass10コードのリストを取得

        Args:
            prefecture_code: 6桁の都道府県コード

        Returns:
            class10コードのリスト
        """
        class10_codes = []
        
        if prefecture_code in self.area_codes_data:
            # その都道府県の全てのclass10コードを取得
            class10_codes.extend(self.area_codes_data[prefecture_code].keys())
        
        return class10_codes

    def _get_location_client(self) -> LocationClient:
        """
        LocationClientのインスタンスを取得（遅延初期化）

        Returns:
            LocationClientインスタンス
        """
        if self.location_client is None:
            self.location_client = LocationClient(debug=False)
        return self.location_client

    def process_xml_data(self, xml_data: str, xml_url: str = "") -> Dict[str, Any]:
        """
        単一XMLファイルから海上警報・注意報情報を抽出し、エリアコード別のマッピングを返す

        Args:
            xml_data: 処理するXMLデータ

        Returns:
            エリアコード別の海上警報・注意報情報
        """
        root = self.parse_xml(xml_data, "<Report")
        if root is None:
            return {}

        area_alert_mapping = defaultdict(list)

        # XMLファイル形式を判定
        xml_type = self._determine_xml_type(xml_url)
        
        # Control要素から基本情報を取得（jmaxml1名前空間内）
        control = root.find("jmx:Control", self.ns)
        if control is not None:
            title_elem = control.find("jmx:Title", self.ns)
            if title_elem is not None and self._is_maritime_alert(title_elem.text):
                # 警報名をクリーンアップ
                alert_type = self._clean_maritime_alert_name(title_elem.text)

                if xml_type == "sea":
                    # sea.xml形式: URLの下6桁から都道府県コードを抽出し、そのclass10コード全てにデータを格納
                    prefecture_code = self._extract_prefecture_code_from_url(xml_url)
                    if prefecture_code:
                        class10_codes = self._get_class10_codes_for_prefecture(prefecture_code)
                        for class10_code in class10_codes:
                            if alert_type not in area_alert_mapping[class10_code]:
                                area_alert_mapping[class10_code].append(alert_type)
                            
                elif xml_type == "all_sea":
                    # all_sea.xml形式: 海域コード（9xxx）を抽出し、関連する都道府県コードにマッピング
                    sea_area_codes = self._extract_sea_area_codes(root)
                    if sea_area_codes:
                        prefecture_codes = self._map_sea_area_codes_to_prefectures(sea_area_codes)
                        for prefecture_code in prefecture_codes:
                            # 都道府県コードの全class10コードに適用
                            class10_codes = self._get_class10_codes_for_prefecture(prefecture_code)
                            for class10_code in class10_codes:
                                if alert_type not in area_alert_mapping[class10_code]:
                                    area_alert_mapping[class10_code].append(alert_type)
                    else:
                        # フォールバック: 海域コードが見つからない場合は座標解決を試行
                        coordinates = self._extract_polygon_coordinates(root)
                        if coordinates:
                            resolved_codes = self._resolve_coordinates_to_area_codes(coordinates)
                            for resolved_code in resolved_codes:
                                if alert_type not in area_alert_mapping[resolved_code]:
                                    area_alert_mapping[resolved_code].append(alert_type)

                # Body要素からも詳細な警報情報を抽出（両形式共通）
                self._process_body_elements(root, area_alert_mapping, xml_type, xml_url)

        # 最終的に各エリアの警報リストを重複排除
        for area_code in area_alert_mapping:
            area_alert_mapping[area_code] = self._deduplicate_alerts(area_alert_mapping[area_code])
        
        return area_alert_mapping

    def _is_maritime_alert(self, info_kind: str) -> bool:
        """
        InfoKindが海上警報・注意報かどうかを判定

        Args:
            info_kind: InfoKind文字列

        Returns:
            海上警報・注意報の場合True
        """
        if not info_kind:
            return False
        
        # 海上警報、海上予報、海上注意報などをすべて対象とする
        maritime_keywords = ["海上", "海域", "Maritime", "marine", "海警", "海予", "地方海上"]
        return any(keyword in info_kind for keyword in maritime_keywords)

    def _clean_maritime_alert_name(self, alert_name: str) -> str:
        """
        海上警報名から余計な情報を除去し、標準化する

        Args:
            alert_name: 元の警報名

        Returns:
            クリーンアップされた警報名
        """
        if not alert_name:
            return alert_name
        
        import re
        
        # H22, H23などの時刻情報パターンを削除
        cleaned_name = re.sub(r'\bH\d{2}\b', '', alert_name)
        
        # 括弧内の全てのコンテンツを削除（より包括的）
        cleaned_name = re.sub(r'\([^)]*\)', '', cleaned_name)  # (...) の全てを削除
        cleaned_name = re.sub(r'\[[^\]]*\]', '', cleaned_name)  # [...] の全てを削除
        cleaned_name = re.sub(r'（[^）]*）', '', cleaned_name)  # （...）の全角括弧を削除
        cleaned_name = re.sub(r'【[^】]*】', '', cleaned_name)  # 【...】を削除
        
        # 時刻関連のパターンを削除
        cleaned_name = re.sub(r'\d+時\d*分?', '', cleaned_name)
        cleaned_name = re.sub(r'\d{1,2}:\d{2}', '', cleaned_name)  # 時刻 HH:MM
        cleaned_name = re.sub(r'\d{4}年\d{1,2}月\d{1,2}日', '', cleaned_name)  # 日付
        
        # 地域コードや番号を削除
        cleaned_name = re.sub(r'\b\d{4,6}\b', '', cleaned_name)  # 4-6桁の数字
        cleaned_name = re.sub(r'第\d+号', '', cleaned_name)
        
        # 発表・更新などの情報を削除
        cleaned_name = re.sub(r'発表.*$', '', cleaned_name)
        cleaned_name = re.sub(r'更新.*$', '', cleaned_name)
        cleaned_name = re.sub(r'継続.*$', '', cleaned_name)
        cleaned_name = re.sub(r'解除.*$', '', cleaned_name)
        
        # 空の括弧を削除（残っている場合）
        cleaned_name = re.sub(r'\(\s*\)', '', cleaned_name)
        cleaned_name = re.sub(r'\[\s*\]', '', cleaned_name)
        cleaned_name = re.sub(r'（\s*）', '', cleaned_name)
        cleaned_name = re.sub(r'【\s*】', '', cleaned_name)
        
        # 特殊文字や記号を削除
        cleaned_name = re.sub(r'[◆◇★☆●○▲△▼▽■□※]', '', cleaned_name)
        
        # 複数の区切り文字を統一
        cleaned_name = re.sub(r'[・･\-\－\—\─]+', ' ', cleaned_name)
        
        # 余分な空白を削除
        cleaned_name = re.sub(r'\s+', ' ', cleaned_name).strip()
        
        # 空文字列の場合は元の名前を返す
        if not cleaned_name:
            return alert_name
        
        return cleaned_name

    def _deduplicate_alerts(self, alert_list: list) -> list:
        """
        類似の警報要素を重複排除し、統一する

        Args:
            alert_list: 警報名のリスト

        Returns:
            重複排除された警報名のリスト
        """
        if not alert_list:
            return alert_list
        
        # まずクリーンアップ
        cleaned_alerts = [self._clean_maritime_alert_name(alert) for alert in alert_list]
        
        # 重複排除（単純な文字列比較）
        seen = set()
        deduplicated = []
        
        for cleaned_alert in cleaned_alerts:
            if not cleaned_alert or cleaned_alert in seen:
                continue
            seen.add(cleaned_alert)
            deduplicated.append(cleaned_alert)
        
        return deduplicated

    def _are_alerts_similar(self, alert1: str, alert2: str) -> bool:
        """
        2つの警報が類似しているかどうかを判定

        Args:
            alert1: 警報名1
            alert2: 警報名2

        Returns:
            類似している場合True
        """
        if not alert1 or not alert2:
            return False
        
        # 完全一致
        if alert1 == alert2:
            return True
        
        # 大文字小文字を無視して比較
        if alert1.lower() == alert2.lower():
            return True
        
        # 重要なキーワードが同じかどうかをチェック
        keywords1 = set(word for word in alert1.split() if len(word) > 1)
        keywords2 = set(word for word in alert2.split() if len(word) > 1)
        
        # キーワードの重複率が高い場合は類似とみなす
        if keywords1 and keywords2:
            intersection = keywords1 & keywords2
            union = keywords1 | keywords2
            similarity = len(intersection) / len(union)
            
            # 80%以上類似している場合は同じとみなす
            if similarity >= 0.8:
                return True
        
        return False

    def _determine_xml_type(self, xml_url: str) -> str:
        """
        XMLファイル形式を判定

        Args:
            xml_url: XMLファイルのURL

        Returns:
            'sea' (sea.xml形式) または 'all_sea' (all_sea.xml形式)
        """
        if "_VPCU51_" in xml_url or "_VPCY51_" in xml_url:
            return "sea"
        elif "_VPZU52_" in xml_url:
            return "all_sea"
        else:
            return "sea"  # デフォルト

    def _extract_prefecture_code_from_url(self, xml_url: str) -> Optional[str]:
        """
        XMLのURLから都道府県コード（下6桁）を抽出

        Args:
            xml_url: XMLファイルのURL

        Returns:
            6桁の都道府県コード
        """
        import re
        patterns = [
            r"_VPCY51_(\d{6})\.xml",  # 海上予報
            r"_VPCU51_(\d{6})\.xml",  # 海上警報
        ]
        
        for pattern in patterns:
            match = re.search(pattern, xml_url)
            if match:
                return match.group(1)
        return None

    def _extract_polygon_coordinates(self, root: ET.Element) -> List[tuple]:
        """
        all_sea.xml形式からjmx_eb:Polygonタグの座標を抽出

        Args:
            root: XMLのルート要素

        Returns:
            座標のタプルリスト [(lat, lon), ...]
        """
        coordinates = []
        
        # jmx_eb:Polygon要素を探す
        jmx_eb_ns = {"jmx_eb": "http://xml.kishou.go.jp/jmaxml1/elementBasis1/"}
        polygons = root.findall(".//jmx_eb:Polygon", jmx_eb_ns)
        
        for polygon in polygons:
            coord_text = polygon.text
            if coord_text:
                # 座標文字列をパース (+37+141/+42+141/+47+152/... 形式)
                coord_pairs = coord_text.strip().split('/')
                for coord_pair in coord_pairs:
                    coord_pair = coord_pair.strip()
                    if coord_pair.startswith('+') and len(coord_pair) >= 6:
                        try:
                            # +37+141 -> lat=37, lon=141
                            lat_end = coord_pair.find('+', 1)
                            if lat_end > 1:
                                lat = float(coord_pair[1:lat_end])
                                lon = float(coord_pair[lat_end+1:])
                                coordinates.append((lat, lon))
                        except ValueError:
                            continue
        
        return coordinates

    def _extract_sea_area_codes(self, root: ET.Element) -> List[str]:
        """
        all_sea.xml形式から海域コード（9010, 9020等）を抽出

        Args:
            root: XMLのルート要素

        Returns:
            海域コードのリスト
        """
        sea_area_codes = []
        
        # Body内のArea要素から海域コードを抽出
        areas = root.findall(".//{http://xml.kishou.go.jp/jmaxml1/body/meteorology1/}Area")
        
        for area in areas:
            code_elem = area.find("{http://xml.kishou.go.jp/jmaxml1/body/meteorology1/}Code")
            name_elem = area.find("{http://xml.kishou.go.jp/jmaxml1/body/meteorology1/}Name")
            
            if code_elem is not None and code_elem.text:
                code = code_elem.text
                # 海域コードは9xxx形式
                if code.startswith('9') and len(code) == 4:
                    sea_area_codes.append(code)
                    if name_elem is not None:
                        print(f"Found sea area: {name_elem.text} (Code: {code})")
        
        return sea_area_codes

    def _map_sea_area_codes_to_prefectures(self, sea_area_codes: List[str]) -> List[str]:
        """
        海域コードを都道府県コードにマッピング

        Args:
            sea_area_codes: 海域コードのリスト

        Returns:
            都道府県コードのリスト
        """
        prefecture_codes = set()
        
        for sea_code in sea_area_codes:
            if sea_code in self.sea_area_code_mapping:
                prefecture_codes.update(self.sea_area_code_mapping[sea_code])
        
        return list(prefecture_codes)

    def _resolve_coordinates_to_area_codes(self, coordinates: List[tuple]) -> List[str]:
        """
        座標リストからエリアコードを解決

        Args:
            coordinates: 座標のタプルリスト [(lat, lon), ...]

        Returns:
            解決されたエリアコードのリスト
        """
        resolved_codes = set()
        client = self._get_location_client()
        
        # サンプリング: 座標が多すぎる場合は一定間隔で処理
        sample_coords = coordinates[::max(1, len(coordinates) // 20)]  # 最大20ポイント
        
        for lat, lon in sample_coords:
            try:
                result = client.get_location_data(lat, lon)
                if result and isinstance(result, tuple) and len(result) >= 1:
                    location_response = result[0]
                    if hasattr(location_response, 'area_code'):
                        area_code = str(location_response.area_code).zfill(6)
                        resolved_codes.add(area_code)
            except Exception as e:
                print(f"Error resolving coordinates ({lat}, {lon}): {e}")
                continue
        
        return list(resolved_codes)

    def _process_body_elements(self, root: ET.Element, area_alert_mapping: defaultdict, xml_type: str, xml_url: str):
        """
        Body要素から詳細な警報情報を抽出（共通処理）

        Args:
            root: XMLのルート要素
            area_alert_mapping: 結果を格納する辞書
            xml_type: XMLファイル形式 ('sea' または 'all_sea')
            xml_url: XMLファイルのURL
        """
        body = root.find(".//{http://xml.kishou.go.jp/jmaxml1/body/meteorology1/}Body")
        if body is not None:
            # MeteorologicalInfos から詳細情報を取得
            for meteo_info in body.findall(".//{http://xml.kishou.go.jp/jmaxml1/body/meteorology1/}MeteorologicalInfo"):
                items = meteo_info.findall(".//{http://xml.kishou.go.jp/jmaxml1/body/meteorology1/}Item")
                for item in items:
                    # Kind要素から警報種別を取得
                    kinds = item.findall(".//{http://xml.kishou.go.jp/jmaxml1/body/meteorology1/}Kind")
                    
                    for kind in kinds:
                        name_elem = kind.find("{http://xml.kishou.go.jp/jmaxml1/body/meteorology1/}Name")
                        if name_elem is not None and name_elem.text:
                            # 警報名をクリーンアップ
                            alert_name = self._clean_maritime_alert_name(name_elem.text)
                            
                            if xml_type == "sea":
                                # sea.xml形式: 都道府県コードの全class10コードに適用
                                prefecture_code = self._extract_prefecture_code_from_url(xml_url)
                                if prefecture_code:
                                    class10_codes = self._get_class10_codes_for_prefecture(prefecture_code)
                                    for class10_code in class10_codes:
                                        if alert_name not in area_alert_mapping[class10_code]:
                                            area_alert_mapping[class10_code].append(alert_name)
                                            
                            elif xml_type == "all_sea":
                                # all_sea.xml形式: 海域コードから都道府県コードを抽出してclass10コードに適用
                                sea_area_codes = self._extract_sea_area_codes(root)
                                if sea_area_codes:
                                    prefecture_codes = self._map_sea_area_codes_to_prefectures(sea_area_codes)
                                    for prefecture_code in prefecture_codes:
                                        class10_codes = self._get_class10_codes_for_prefecture(prefecture_code)
                                        for class10_code in class10_codes:
                                            if alert_name not in area_alert_mapping[class10_code]:
                                                area_alert_mapping[class10_code].append(alert_name)
                                else:
                                    # フォールバック: 座標解決を試行
                                    coordinates = self._extract_polygon_coordinates(root)
                                    if coordinates:
                                        resolved_codes = self._resolve_coordinates_to_area_codes(coordinates)
                                        for resolved_code in resolved_codes:
                                            if alert_name not in area_alert_mapping[resolved_code]:
                                                area_alert_mapping[resolved_code].append(alert_name)

    def _extract_maritime_area_code(self, head: ET.Element, xml_url: str) -> Optional[str]:
        """
        XMLから海域エリアコードを抽出

        Args:
            head: XML Head要素
            xml_url: XMLファイルのURL（パターンマッチング用）

        Returns:
            エリアコード（見つからない場合はNone）
        """
        # URLからエリアコードを抽出する方法
        import re
        patterns = [
            r"_VPCY51_(\d{6})\.xml",  # 海上予報
            r"_VPCU51_(\d{6})\.xml",  # 海上警報
            r"_VPZU52_(\d{6})\.xml"   # 全般海上警報
        ]
        
        for pattern in patterns:
            match = re.search(pattern, xml_url)
            if match:
                return match.group(1)

        # ReportingOffice から推定
        reporting_office = head.find("ib:ReportingOffice", self.ns)
        if reporting_office is not None and reporting_office.text:
            office_name = reporting_office.text
            return self._map_office_to_area_code(office_name)

        return None

    def _map_office_to_area_code(self, office_name: str) -> Optional[str]:
        """
        気象台名からエリアコードを推定

        Args:
            office_name: 気象台名

        Returns:
            エリアコード
        """
        office_mapping = {
            "札幌管区気象台": "016000",
            "函館海上気象": "017000", 
            "仙台管区気象台": "040000",
            "気象庁": "130000",  # 東京
            "新潟地方気象台": "150000",
            "名古屋地方気象台": "230000",
            "大阪管区気象台": "260020",
            "高松地方気象台": "280000",
            "福岡管区気象台": "400000",
            "長崎海上気象": "420000",
            "鹿児島地方気象台": "460100",
            "沖縄気象台": "471000"
        }
        
        for office, code in office_mapping.items():
            if office in office_name:
                return code
                
        return None

    def close(self):
        """
        リソースをクリーンアップ
        """
        if self.location_client:
            self.location_client.close()
            self.location_client = None

    def process_multiple_urls(self, url_list: List[str]) -> Dict[str, Any]:
        """
        複数のXMLファイルから海上警報・注意報情報を統合処理（並列化版）

        Args:
            url_list: 処理するXMLファイルURLのリスト

        Returns:
            統合された海上警報・注意報情報
        """
        output = {
            "alert_pulldatetime": datetime.now().isoformat(timespec="seconds") + "+09:00",
        }

        if not url_list:
            print("No URLs to process")
            return output

        # 並列でXMLを全て取得
        print(f"Fetching {len(url_list)} maritime XML files...")
        xml_results = self.fetch_xml_concurrent(url_list, max_workers=10)
        
        # 取得したXMLを並列で処理
        successful_xmls = {url: content for url, content in xml_results.items() if content is not None}
        print(f"Processing {len(successful_xmls)} maritime XML files in parallel...")

        # スレッドプールで並列処理
        with ThreadPoolExecutor(max_workers=10) as executor:
            # XMLパース・処理を並列実行
            def process_xml_content(url_content_pair):
                url, xml_content = url_content_pair
                try:
                    return self.process_xml_data(xml_content, url)
                except Exception as e:
                    print(f"Error processing maritime XML {url}: {e}")
                    return None
                
            results = executor.map(process_xml_content, successful_xmls.items())

            # 結果を統合
            processed_count = 0
            for result in results:
                if result is None:
                    continue
                processed_count += 1
                for area_code, alert_kinds in result.items():
                    if area_code not in output:
                        output[area_code] = {"alert_info": []}
                    for kind in alert_kinds:
                        if kind not in output[area_code]["alert_info"]:
                            output[area_code]["alert_info"].append(kind)
            
            print(f"Successfully processed {processed_count} maritime XML files")

        return output

    def get_maritime_alerts(self, output_json_path: Optional[str] = None) -> Dict[str, Any]:
        """
        海上警報・注意報情報を取得・統合処理

        Args:
            output_json_path: 出力JSONファイルパス（オプション）

        Returns:
            統合された海上警報・注意報情報
        """
        print("=== 海上警報・注意報情報取得開始 ===")
        
        try:
            # Step 1: other.xmlからURLリストを取得
            url_list = self.get_maritime_alert_xml_list()
            
            if not url_list:
                print("No maritime alert URLs found.")
                return {"alert_pulldatetime": datetime.now().isoformat(timespec="seconds") + "+09:00"}

            # Step 2: 海上警報・注意報情報の取得・統合
            print("Processing maritime alert info...")
            result = self.process_multiple_urls(url_list)
            
            if output_json_path:
                self.save_json(result, output_json_path)
            
            print("=== 海上警報・注意報情報取得完了 ===")
            return result
            
        except Exception as e:
            print(f"Error in maritime alert processing: {e}")
            import traceback
            traceback.print_exc()
            return {"alert_pulldatetime": datetime.now().isoformat(timespec="seconds") + "+09:00"}
        finally:
            # リソースをクリーンアップ
            self.close()


def main():
    """
    海上警報・注意報処理のメイン関数（テスト用）
    """
    try:
        processor = MaritimeAlertProcessor()
        
        # 海上警報・注意報情報を取得
        result = processor.get_maritime_alerts()
        
        print("\n=== Maritime Alert Processing Result ===")
        print(f"Processed areas: {len([k for k in result.keys() if k != 'alert_pulldatetime'])}")
        
        for area_code, data in result.items():
            if area_code != 'alert_pulldatetime':
                print(f"Area {area_code}: {len(data.get('alert_info', []))} maritime alerts")
                
    except Exception as e:
        print(f"Error in main processing: {e}")
        import traceback
        traceback.print_exc()
    finally:
        processor.close()


if __name__ == "__main__":
    main()