# import requests
# from typing import Optional

# def fetch_xml(url: str) -> Optional[str]:
#     """
#     指定されたURLからXMLデータを取得する
    
#     Args:
#         url (str): 取得するXMLのURL
        
#     Returns:
#         Optional[str]: 取得したXMLデータ。エラー時はNone
#     """
#     try:
#         response = requests.get(url)
#         response.raise_for_status()  # エラーチェック
#         return response.text
#     except requests.RequestException as e:
#         print(f"Error fetching XML: {e}")
#         return None

# def get_regular_xml() -> Optional[str]:
#     """定時更新の気象情報XMLを取得"""
#     return fetch_xml("https://www.data.jma.go.jp/developer/xml/feed/regular.xml")

# def get_warning_xml() -> Optional[str]:
#     """気象警報・注意報XMLを取得"""
#     return fetch_xml("https://www.data.jma.go.jp/developer/xml/feed/extra.xml")

# def get_disaster_xml() -> Optional[str]:
#     """災害情報XMLを取得"""
#     return fetch_xml("https://www.data.jma.go.jp/developer/xml/feed/eqvol.xml")

import requests
from typing import Optional
import time
import xml.etree.ElementTree as ET

# def get_regular_xml() -> Optional[str]:
#     """定時更新の気象情報XMLを取得"""
#     return fetch_xml("https://www.data.jma.go.jp/developer/xml/feed/regular.xml")

# def get_warning_xml() -> Optional[str]:
#     """気象警報・注意報XMLを取得"""
#     return fetch_xml("https://www.data.jma.go.jp/developer/xml/feed/extra.xml")

# def get_disaster_xml() -> Optional[str]:
#     """災害情報XMLを取得"""
#     return fetch_xml("https://www.data.jma.go.jp/developer/xml/feed/eqvol.xml")

# 個々の注意報が格納されたXMLファイルを読み取り、json形式に変換する
def fetch_xml(url: str) -> Optional[str]:
    """
    指定されたURLからXMLデータを取得する
    
    Args:
        url (str): 取得するXMLのURL
        
    Returns:
        Optional[str]: 取得したXMLデータ。エラー時はNone
    """
    try:
        response = requests.get(url)
        response.encoding = 'utf-8'
        response.raise_for_status()  # エラーチェック
        return response.text
    except requests.RequestException as e:
        print(f"Error fetching XML: {e}")
        return None


import xml.etree.ElementTree as ET
import json
from collections import defaultdict

def get_alert_info( url_list:str) -> Optional[str]:
    # 名前空間の定義
    ns = {
        'jmx': 'http://xml.kishou.go.jp/jmaxml1/',
        'ib': 'http://xml.kishou.go.jp/jmaxml1/informationBasis1/',
        'add': 'http://xml.kishou.go.jp/jmaxml1/addition1/'
    }
    info_key = "警報・注意報"
    time_key = "disaster_reportdatetime"
    type = "気象警報・注意報（一次細分区域等）"
    # 結果格納用辞書（area-codeをキーとする）
    result = defaultdict(lambda: {info_key: [], time_key: ""})

    for url in url_list:
        # XMLファイル読み込み（必要に応じて変更）
        tree = fetch_xml(url)
        root = ET.fromstring(tree)

        # 報告時刻を取得
        disaster_reportdatetime = get_report_time(root,ns)

        # 情報部分を走査
        for information in root.findall(f'.//ib:Information[@type="{type}"]', ns):
            for item in information.findall('ib:Item', ns):
                # 種別を取得（複数ある可能性あり）
                kinds = [kind.find('ib:Name', ns).text for kind in item.findall('ib:Kind', ns)
                        if kind.find('ib:Name', ns) is not None and kind.find('ib:Name', ns).text != "解除"]
                
                # 対象エリアを取得（複数）
                for area in item.findall('ib:Areas/ib:Area', ns):
                    code_elem = area.find('ib:Code', ns)
                    if code_elem is not None:
                        area_code = code_elem.text
                        print(area_code)
                        _ = result[area_code]
                        result[area_code][time_key] = disaster_reportdatetime
                        # 重複を避けて種別を追加
                        for kind in kinds:
                            if kind not in result[area_code][info_key]:
                                result[area_code][info_key].append(kind)

        time.sleep(1)  # 待つ
                
    # JSONとして出力
    json_output = json.dumps(result, ensure_ascii=False, indent=2)
    print (json_output)

def get_report_time(root,ns):
    # ⏰ ReportDateTime（例：11時）を取得
    head = root.find('ib:Head', ns)
    if head is not None:
        report_dt_elem = head.find('ib:ReportDateTime', ns)
        if report_dt_elem is not None and report_dt_elem.text:
            # 時だけを抽出（例："2025-05-23T09:52:00+09:00" → "09時"）
            report_hour = report_dt_elem.text
        else:
            report_hour = ""
    else:
        report_hour = ""
    return report_hour

def get_alert_list():
    xml_data =fetch_xml("https://www.data.jma.go.jp/developer/xml/feed/extra.xml")
    # 名前空間を定義
    ns = {'atom': 'http://www.w3.org/2005/Atom'}

    # XMLのパース
    root = ET.fromstring(xml_data)

    # entry 内の id タグをリスト化
    entry_ids = [entry.find('atom:id', ns).text for entry in root.findall('atom:entry', ns)]

    # 結果の表示
    print(entry_ids)
    return entry_ids


def get_disaster_info():
    
    return

URL_list = get_alert_list()
get_alert_info ( URL_list )