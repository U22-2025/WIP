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
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import xml.etree.ElementTree as ET
from collections import defaultdict
from typing import Dict, List, Any, Optional
from WIP_Server.data.xml_base import XMLBaseProcessor

from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

class AlertProcessor(XMLBaseProcessor):
    """
    警報・注意報情報処理クラス
    
    気象庁の警報・注意報XMLデータを処理し、
    エリアコード別に警報・注意報情報を整理する。
    """
    
    def __init__(self):
        super().__init__()
        self.target_type = "気象警報・注意報（一次細分区域等）"
    
    def process_xml_data(self, xml_data: str) -> Dict[str, Any]:
        """
        単一XMLファイルから警報・注意報情報を抽出し、エリアコード別のマッピングとReportDateTimeを返す
        
        Args:
            xml_data: 処理するXMLデータ
            
        Returns:
            エリアコード別の警報・注意報情報とpulldatetimeを含む辞書
        """
        root = self.parse_xml(xml_data, '<Report')
        if root is None:
            return {}
        
        area_alert_mapping = defaultdict(list)
        
        # 情報部分を走査
        for information in root.findall(f'.//ib:Information[@type="{self.target_type}"]', self.ns):
            for item in information.findall('ib:Item', self.ns):
                # 種別を取得（複数ある可能性あり）
                kinds = self._extract_alert_kinds(item)
                
                # 対象エリアを取得（複数）
                area_codes = self._extract_area_codes(item)
                
                # エリアコード別に警報・注意報情報を格納
                for area_code in area_codes:
                    # 重複を避けて種別を追加
                    for kind in kinds:
                        if kind not in area_alert_mapping[area_code]:
                            area_alert_mapping[area_code].append(kind)
        
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
        for kind in item.findall('ib:Kind', self.ns):
            name_elem = kind.find('ib:Name', self.ns)
            if name_elem is not None and name_elem.text and name_elem.text != "解除":
                kinds.append(name_elem.text)
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
        for area in item.findall('ib:Areas/ib:Area', self.ns):
            code_elem = area.find('ib:Code', self.ns)
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
        複数のXMLファイルから警報・注意報情報を統合処理（並列化版）
        
        Args:
            url_list: 処理するXMLファイルURLのリスト
            
        Returns:
            統合された警報・注意報情報
        """
        output = {
            "alert_pulldatetime": datetime.now().isoformat(timespec='seconds') + '+09:00',
        }
        
        # スレッドプールで並列処理
        with ThreadPoolExecutor(max_workers=10) as executor:
            # 各URLの処理を非同期で実行
            results = executor.map(self._process_single_url, url_list)
            
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

    def get_alert_xml_list(self) -> List[str]:
        """
        警報・注意報XMLファイルのURLリストを取得
        
        Returns:
            XMLファイルURLのリスト
        """
        return self.get_feed_entry_urls("https://www.data.jma.go.jp/developer/xml/feed/extra.xml")


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

    def get_alert_info(self, url_list: List[str], output_json_path: Optional[str] = None) -> str:
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
        json_result = processor.get_alert_info(url_list, 'wip/json/alert_data.json')
        print("\n=== Alert Info Processing Complete ===")
        print(json_result)

    except Exception as e:
        print(f"Error in main processing: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()