"""
警報・注意報情報処理モジュール

気象庁の警報・注意報XMLデータを処理し、エリアコード別に情報を整理する。

主な機能:
- 警報・注意報XMLデータの取得・解析
- エリアコード別の警報・注意報情報の抽出
- 報告時刻の取得
- JSON形式での出力
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
from typing import Dict, List, Any, Optional
from WIPServerPy.data.xml_base import XMLBaseProcessor

from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import re


# JSON_DIRの定義を削除（logs/jsonフォルダは使用しない）
class AlertProcessor(XMLBaseProcessor):
    """
    警報・注意報情報処理クラス

    気象庁の警報・注意報XMLデータを処理し、
    エリアコード別に警報・注意報情報を整理する。
    """

    def __init__(self):
        super().__init__()
        self.target_type = "気象警報・注意報（一次細分区域等）"

    @staticmethod
    def _normalize_kind_name(name: str) -> str:
        """全角/半角の括弧を除去して正規化"""
        return re.sub(r"[()（）]", "", name)

    def process_xml_data(self, xml_data: str) -> Dict[str, Any]:
        """
        単一XMLファイルから警報・注意報情報を抽出し、エリアコード別のマッピングとReportDateTimeを返す

        Args:
            xml_data: 処理するXMLデータ

        Returns:
            エリアコード別の警報・注意報情報とpulldatetimeを含む辞書
        """
        root = self.parse_xml(xml_data, "<Report")
        if root is None:
            return {}

        area_alert_mapping = defaultdict(list)

        # 情報部分を走査
        for information in root.findall(
            f'.//ib:Information[@type="{self.target_type}"]', self.ns
        ):
            for item in information.findall("ib:Item", self.ns):
                # 種別を取得（複数ある可能性あり）
                kinds = self._extract_alert_kinds(item)

                # 対象エリアを取得（複数）
                area_codes = self._extract_area_codes(item)

                # エリアコード別に警報・注意報情報を格納
                for area_code in area_codes:
                    # 重複を避けて種別を追加（正規化後の文字列を使用）
                    for kind in kinds:
                        normalized = self._normalize_kind_name(kind)
                        if normalized not in area_alert_mapping[area_code]:
                            area_alert_mapping[area_code].append(normalized)

        return area_alert_mapping

    def _extract_alert_kinds(self, item: ET.Element) -> List[str]:
        """
        Item要素から警報・注意報の種別を抽出

        Args:
            item: XML Item要素

        Returns:
            警報・注意報種別のリスト
        """
        kinds = []
        for kind in item.findall("ib:Kind", self.ns):
            name_elem = kind.find("ib:Name", self.ns)
            if name_elem is not None and name_elem.text and name_elem.text != "解除":
                normalized = self._normalize_kind_name(name_elem.text)
                if normalized:
                    kinds.append(normalized)
        return kinds

    def _extract_area_codes(self, item: ET.Element) -> List[str]:
        """
        Item要素からエリアコードを抽出

        Args:
            item: XML Item要素

        Returns:
            エリアコードのリスト
        """
        area_codes = []
        for area in item.findall("ib:Areas/ib:Area", self.ns):
            code_elem = area.find("ib:Code", self.ns)
            if code_elem is not None and code_elem.text:
                area_codes.append(code_elem.text)
        return area_codes

    def _process_single_url(self, url: str) -> Optional[Dict[str, Any]]:
        """
        単一のURLから警報・注意報情報を取得・処理

        Args:
            url: 処理対象のXML URL

        Returns:
            処理結果（エリアコード別の警報・注意報情報）またはNone
        """
        # 基本処理を親クラスで実行
        base_result = super()._process_single_url_base(url)
        if base_result is None:
            return None

        # 警報特有の処理を実行
        return self.process_xml_data(base_result["xml_data"])

    def process_multiple_urls(self, url_list: List[str]) -> Dict[str, Any]:
        """
        複数のXMLファイルから警報・注意報情報を統合処理（並列化版・高速）

        Args:
            url_list: 処理するXMLファイルURLのリスト

        Returns:
            統合された警報・注意報情報
        """
        output = {
            "alert_pulldatetime": datetime.now().isoformat(timespec="seconds")
            + "+09:00",
        }

        # 並列でXMLを全て取得
        xml_results = self.fetch_xml_concurrent(url_list, max_workers=10)
        
        # 取得したXMLを並列で処理
        successful_xmls = {url: content for url, content in xml_results.items() if content is not None}
        print(f"Processing {len(successful_xmls)} alert XML files in parallel...")

        # スレッドプールで並列処理
        with ThreadPoolExecutor(max_workers=10) as executor:
            # XMLパース・処理を並列実行
            def process_xml_content(url_content_pair):
                url, xml_content = url_content_pair
                return self._process_xml_content(xml_content)
                
            results = executor.map(process_xml_content, successful_xmls.items())

            # 結果を統合
            for result in results:
                if result is None:
                    continue
                for area_code, alert_kinds in result.items():
                    if area_code not in output:
                        output[area_code] = {"alert_info": []}
                    for kind in alert_kinds:
                        if kind not in output[area_code]["alert_info"]:
                            output[area_code]["alert_info"].append(kind)
        return output

    def _process_xml_content(self, xml_content: str) -> Optional[Dict[str, Any]]:
        """
        XMLコンテンツを処理（並列処理用）
        
        Args:
            xml_content: XMLコンテンツ文字列
            
        Returns:
            処理結果辞書、エラー時はNone
        """
        try:
            # XMLのパースと処理
            base_result = self._parse_xml_get_report_time(xml_content)
            if base_result is None or base_result["xml_data"] is None:
                return None
                
            # 警報特有の処理を実行
            return self.process_xml_data(base_result["xml_data"])
        except Exception as e:
            print(f"Error processing alert XML content: {e}")
            return None

    def get_alert_xml_list(self) -> List[str]:
        """
        警報・注意報XMLファイルのURLリストを取得

        Returns:
            XMLファイルURLのリスト
        """
        return self.get_feed_entry_urls(
            "https://www.data.jma.go.jp/developer/xml/feed/extra.xml"
        )


class AlertDataProcessor:
    """
    警報・注意報データ処理統合クラス（メインコントローラー）

    役割:
    - 全体的な処理フローの制御
    - 各専門クラスの連携調整
    - ファイル入出力の管理
    - エラーハンドリング
    - データ変換・統合の統括
    """

    def __init__(self):
        self.xml_processor = AlertProcessor()

    def get_alert_info(
        self, url_list: List[str], output_json_path: Optional[str] = None
    ) -> str:
        """
        複数XMLファイルから警報・注意報情報を取得・統合

        Args:
            url_list: 処理するXMLファイルURLリスト
            output_json_path: 出力JSONファイルパス（オプション）

        Returns:
            統合された警報・注意報情報JSON文字列
        """
        result = self.xml_processor.process_multiple_urls(url_list)

        if output_json_path:
            self.xml_processor.save_json(result, output_json_path)

        return result


def main():
    """
    警報・注意報処理のメイン関数
    """
    try:
        processor = AlertDataProcessor()

        # Step 1: XMLファイルリストの取得
        print("Step 1: Getting XML file list...")
        url_list = processor.xml_processor.get_alert_xml_list()
        print(f"Found {len(url_list)} URLs")
        if not url_list:
            print("No URLs found. Exiting.")
            return

        # Step 2: 警報・注意報情報の取得・統合
        print("Step 2: Processing alert info...")
        json_result = processor.get_alert_info(url_list)
        print("\n=== Alert Info Processing Complete ===")
        print(json_result)

    except Exception as e:
        print(f"Error in main processing: {e}")
        import traceback

        traceback.print_exc()


