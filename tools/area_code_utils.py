import json
from typing import Optional, List

AREA_CODE_PATH = 'python/logs/json/area_codes.json'

area_data: Optional[dict] = None

def fetch_json_from_file(path: str = AREA_CODE_PATH) -> Optional[dict]:
    """area_codes.json を読み込んで辞書を返す"""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f'エリアコードJSONの取得に失敗しました: {e}')
        return None

def get_office_codes() -> List[str]:
    """オフィスコードの一覧を返す"""
    global area_data
    if area_data is None:
        area_data = fetch_json_from_file()
    if not area_data:
        return []
    return list(area_data.keys())

def get_area_codes() -> List[str]:
    """全エリアコードの一覧を返す"""
    global area_data
    if area_data is None:
        area_data = fetch_json_from_file()
    if not area_data:
        return []
    codes = set()
    for office_data in area_data.values():
        codes.update(office_data.keys())
    return list(codes)

def find_area_key_by_children_code(target_code: str) -> str:
    """子コードから親エリアコードを探索する"""
    global area_data
    if area_data is None:
        area_data = fetch_json_from_file()
    if not area_data:
        return target_code
    for office_data in area_data.values():
        for area_code, children in office_data.items():
            if target_code in children:
                return area_code
    return target_code
