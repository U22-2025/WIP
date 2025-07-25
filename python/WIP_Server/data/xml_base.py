"""
XML処理基底クラス

気象庁XMLデータの共通処理機能を提供する基底クラス。
警報・注意報、災害情報などの各種XMLデータ処理で共通して使用される機能を集約。

主な機能:
- XMLデータの取得
- 共通名前空間の定義
- エラーハンドリング
- JSONファイル出力
"""

import xml.etree.ElementTree as ET
import json
import requests
from typing import Optional, Dict, Any
from abc import ABC, abstractmethod


class XMLBaseProcessor(ABC):
    """
    XML処理の基底クラス
    
    各種気象庁XMLデータ処理の共通機能を提供。
    継承先で具体的な処理ロジックを実装する。
    """
    
    def __init__(self):
        # 共通XML名前空間の定義
        self.ns = {
            'jmx': 'http://xml.kishou.go.jp/jmaxml1/',
            'ib': 'http://xml.kishou.go.jp/jmaxml1/informationBasis1/',
            'add': 'http://xml.kishou.go.jp/jmaxml1/addition1/',
            'body': 'http://xml.kishou.go.jp/jmaxml1/body/volcanology1/',
            'jmx_eb': 'http://xml.kishou.go.jp/jmaxml1/elementBasis1/',
            'atom': 'http://www.w3.org/2005/Atom'
        }
    
    def fetch_xml(self, url: str) -> Optional[str]:
        """
        指定されたURLからXMLデータを取得
        
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
            print(f"Error fetching XML from {url}: {e}")
            return None
    
    def parse_xml(self, xml_data: str, clean_start_tag: Optional[str] = None) -> Optional[ET.Element]:
        """
        XML文字列をパースしてElementオブジェクトを返す
        
        Args:
            xml_data: XML文字列
            clean_start_tag: XMLの開始タグ（クリーニング用）
            
        Returns:
            XMLのルート要素、エラー時はNone
        """
        try:
            # XMLファイルの先頭にある不要な文字列を除去
            if clean_start_tag:
                xml_start = xml_data.find(clean_start_tag)
                if xml_start != -1:
                    xml_data = xml_data[xml_start:]
            
            return ET.fromstring(xml_data)
        except ET.ParseError as e:
            print(f"Error parsing XML: {e}")
            return None
    
    def get_report_time(self, root: ET.Element) -> str:
        """
        XMLから報告時刻を取得
        
        Args:
            root: XMLのルート要素
            
        Returns:
            報告時刻文字列
        """
        head = root.find('ib:Head', self.ns)
        if head is not None:
            report_dt_elem = head.find('ib:ReportDateTime', self.ns)
            if report_dt_elem is not None and report_dt_elem.text:
                return report_dt_elem.text
        return ""
    
    def save_json(self, data: Dict[str, Any], file_path: str) -> bool:
        """
        データをJSONファイルとして保存
        
        Args:
            data: 保存するデータ
            file_path: 保存先ファイルパス
            
        Returns:
            保存成功時True、失敗時False
        """
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"JSON data saved to: {file_path}")
            return True
        except Exception as e:
            print(f"Error saving JSON file {file_path}: {e}")
            return False
    
    def get_feed_entry_urls(self, feed_url: str) -> list[str]:
        """
        Atomフィードから各エントリのURLリストを取得
        
        Args:
            feed_url: AtomフィードのURL
            
        Returns:
            エントリURLのリスト
        """
        xml_data = self.fetch_xml(feed_url)
        if not xml_data:
            return []
        
        root = self.parse_xml(xml_data, '<feed')
        if root is None:
            return []
        
        url_list = []
        for entry in root.findall('atom:entry', self.ns):
            id_elem = entry.find('atom:id', self.ns)
            if id_elem is not None and id_elem.text:
                url_list.append(id_elem.text)
        
        return url_list
    
    @abstractmethod
    def process_xml_data(self, xml_data: str) -> Dict[str, Any]:
        """
        XMLデータの具体的な処理（継承先で実装）
        
        Args:
            xml_data: 処理するXMLデータ
            
        Returns:
            処理結果の辞書
        """
        pass
    
    @abstractmethod
    def process_multiple_urls(self, url_list: list[str]) -> Dict[str, Any]:
        """
        複数URLの処理（継承先で実装）

        Args:
            url_list: 処理するURLのリスト
            
        Returns:
            統合された処理結果
        """
        pass

    def _process_single_url_base(self, url: str) -> Optional[Dict[str, Any]]:
        """
        単一URL処理の共通実装 (基底クラス)

        Args:
            url: 処理対象のXML URL
            
        Returns:
            基本処理結果 (xml_dataを含む辞書) またはNone
        """
        xml_data = self.fetch_xml(url)
        if xml_data is None:
            return None
            
        return {
            "xml_data": xml_data,
            "report_time": self.get_report_time(self.parse_xml(xml_data))
        }
