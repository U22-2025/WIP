import requests
from typing import Optional
import json

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


# def add_child_code_to_postgre(parent_code):
#     with open('wtp/resources/area.json', 'r', encoding='utf-8') as f:
#         area_json = json.load(f)
    
#     # parent_codeに一致するデータを抽出してJSONを作成
#     result = {}
#     if parent_code in area_json:
#         result[parent_code] = {
#             "children": area_json[parent_code].get('children', [])
#         }
    
#     # 結果をJSON文字列として返す
#     return json.dumps(result, ensure_ascii=False)

import psycopg2
import json
from typing import Dict, Any

def add_child_code_to_postgre(parent_code: str) -> None:
    try:
        with open('wtp/resources/area.json', 'r', encoding='utf-8') as f:
            area_json = json.load(f)
            print(f"親コード: {parent_code}")

        processed_codes = set()

        def find_in_json(code: str) -> tuple[dict, str]:
            """officesとclass10s、class15sからコードを検索"""
            if code in area_json.get('offices', {}):
                print(f"officesで発見: {code}")
                return area_json['offices'][code], 'offices'
            
            if code in area_json.get('class10s', {}):
                print(f"class10sで発見: {code}")
                return area_json['class10s'][code], 'class10s'
            
            if code in area_json.get('class15s', {}):
                print(f"class15sで発見: {code}")
                return area_json['class15s'][code], 'class15s'
            
            print(f"コード {code} が見つかりません")
            return None, None

        def build_hierarchy(code: str) -> dict:
            """再帰的に階層構造を構築"""
            if code in processed_codes:
                print(f"コード {code} は既に処理済み")
                return {}
            
            print(f"\n階層構築開始: {code}")
            node, source = find_in_json(code)
            if not node:
                return {}
            
            processed_codes.add(code)
            
            print(f"ノードの内容: {node}")
            result = {}
            children = node.get('children', [])
            print(f"子コード: {children}")
            
            if children:
                # class15sから取得したコードの場合
                if source == 'class15s':
                    result[code] = children  # 子コードを配列として格納
                else:
                    result[code] = {}
                    for child in children:
                        print(f"子コード処理中: {child}")
                        child_hierarchy = build_hierarchy(child)
                        if child_hierarchy:
                            result[code].update(child_hierarchy)
                        else:
                            result[code][child] = []
            return result

        hierarchy_dict = build_hierarchy(parent_code)
        print(f"\n最終的な階層構造: {hierarchy_dict}")
        
        with open('wtp/resources/postgre_child_code.json', 'w', encoding='utf-8') as f:
            json.dump(hierarchy_dict, f, ensure_ascii=False, indent=4)

        print(f"親コード {parent_code} の階層構造を正常に保存しました")

    except Exception as e:
        print(f"エラーが発生しました: {e}")

add_child_code_to_postgre("150000")