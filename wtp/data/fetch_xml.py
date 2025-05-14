import requests
from typing import Optional

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
        response.raise_for_status()  # エラーチェック
        return response.text
    except requests.RequestException as e:
        print(f"Error fetching XML: {e}")
        return None

def get_regular_xml() -> Optional[str]:
    """定時更新の気象情報XMLを取得"""
    return fetch_xml("https://www.data.jma.go.jp/developer/xml/feed/regular.xml")

def get_warning_xml() -> Optional[str]:
    """気象警報・注意報XMLを取得"""
    return fetch_xml("https://www.data.jma.go.jp/developer/xml/feed/extra.xml")

def get_disaster_xml() -> Optional[str]:
    """災害情報XMLを取得"""
    return fetch_xml("https://www.data.jma.go.jp/developer/xml/feed/eqvol.xml")
