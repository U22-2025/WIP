"""
警報・注意報情報処理モジュール

気象庁の警報・注意報XMLデータを処理し、エリアコード別に情報を整理する。

主な機能:
- 警報・注意報XMLデータの取得・解析
- エリアコード別の警報・注意報情報の抽出
- 報告時刻の取得
- JSON形式での出力
"""

import xml.etree.ElementTree as ET
import json
from collections import defaultdict
from typing import Dict, List, Any, Optional
from xml_base import XMLBaseProcessor


class AlertProcessor(XMLBaseProcessor):
    """
    警報・注意報情報処理クラス
    
    気象庁の警報・注意報XMLデータを処理し、
    エリアコード別に警報・注意報情報を整理する。
    """
    
    def __init__(self):
        super().__init__()
        self.info_key = "warnings"
        self.time_key = "alert_reportdatetime"
        self.target_type = "気象警報・注意報（一次細分区域等）"
    
    def process_xml_data(self, xml_data: str) -> Dict[str, Any]:
        """
        単一XMLファイルから警報・注意報情報を抽出
        
        Args:
            xml_data: 処理するXMLデータ
            
        Returns:
            エリアコード別の警報・注意報情報
        """
        root = self.parse_xml(xml_data, '<Report')
        if root is None:
            return {}
        
        # 報告時刻を取得
        alert_reportdatetime = self.get_report_time(root)
        
        # 結果格納用辞書（area-codeをキーとする）
        result = defaultdict(lambda: {self.info_key: [], self.time_key: ""})
        
        # 情報部分を走査
        for information in root.findall(f'.//ib:Information[@type="{self.target_type}"]', self.ns):
            for item in information.findall('ib:Item', self.ns):
                # 種別を取得（複数ある可能性あり）
                kinds = self._extract_alert_kinds(item)
                
                # 対象エリアを取得（複数）
                area_codes = self._extract_area_codes(item)
                
                # エリアコード別に警報・注意報情報を格納
                for area_code in area_codes:
                    result[area_code][self.time_key] = alert_reportdatetime
                    # 重複を避けて種別を追加
                    for kind in kinds:
                        if kind not in result[area_code][self.info_key]:
                            result[area_code][self.info_key].append(kind)
        
        return dict(result)
    
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
    
    def process_multiple_urls(self, url_list: List[str]) -> Dict[str, Any]:
        """
        複数のXMLファイルから警報・注意報情報を統合処理
        
        Args:
            url_list: 処理するXMLファイルURLのリスト
            
        Returns:
            統合された警報・注意報情報
        """
        # 結果格納用辞書（area-codeをキーとする）
        result = defaultdict(lambda: {self.info_key: [], self.time_key: ""})
        
        for url in url_list:
            xml_data = self.fetch_xml(url)
            if xml_data is None:
                continue
            
            file_result = self.process_xml_data(xml_data)
            
            # 結果を統合
            for area_code, data in file_result.items():
                # 時刻情報を更新（最新のものを保持）
                if data[self.time_key]:
                    result[area_code][self.time_key] = data[self.time_key]
                
                # 警報・注意報情報を統合（重複回避）
                for kind in data[self.info_key]:
                    if kind not in result[area_code][self.info_key]:
                        result[area_code][self.info_key].append(kind)
        
        return dict(result)
    
    def get_alert_xml_list(self) -> List[str]:
        """
        警報・注意報XMLファイルのURLリストを取得
        
        Returns:
            XMLファイルURLのリスト
        """
        return self.get_feed_entry_urls("https://www.data.jma.go.jp/developer/xml/feed/extra.xml")
    
    def process_all_alerts(self, output_file: Optional[str] = None) -> str:
        """
        全ての警報・注意報情報を処理
        
        Args:
            output_file: 出力JSONファイルパス（オプション）
            
        Returns:
            処理結果のJSON文字列
        """
        # XMLファイルリストを取得
        url_list = self.get_alert_xml_list()
        if not url_list:
            print("No alert XML URLs found.")
            return "{}"
        
        print(f"Processing {len(url_list)} alert XML files...")
        
        # 全XMLファイルを処理
        result = self.process_multiple_urls(url_list)
        
        # JSON文字列として出力
        json_output = json.dumps(result, ensure_ascii=False, indent=2)
        
        # ファイル出力（オプション）
        if output_file:
            self.save_json(result, output_file)
        
        return json_output


def main():
    """
    警報・注意報処理のメイン関数
    """
    processor = AlertProcessor()
    
    # 全ての警報・注意報情報を処理
    json_result = processor.process_all_alerts('wtp/json/alert_data.json')
    
    print("=== Alert Processing Complete ===")
    print(json_result)


if __name__ == "__main__":
    main()
