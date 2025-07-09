import json
from typing import Optional, List

# グローバル変数としてarea_codes.jsonの内容を格納
area_data: Optional[dict] = None

def fetch_json_from_file() -> Optional[dict]:
    """
    area_codes.jsonファイルからエリアコードデータを取得する
    
    Returns:
        Optional[dict]: エリアコードの辞書データ、失敗時はNone
    """
    try:
        with open('python/logs/json//area_codes.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"エリアコードJSONの取得に失敗しました: {e}")
        return None

def get_office_codes() -> List[str]:
    """
    都道府県コード（office_code）を配列で返す
    
    Returns:
        List[str]: オフィスコードのリスト
    """
    global area_data
    if area_data is None:
        area_data = fetch_json_from_file()
    
    if not area_data:
        print("エリアコードJSONの取得に失敗したため、処理を中止します")
        return []

    try:
        office_codes = list(area_data.keys())
        print(f"officeコードを取得しました: {len(office_codes)}件")
        return office_codes
        
    except Exception as e:
        print(f"エラーが発生しました: {e}")
        return []

def get_area_codes() -> List[str]:
    """
    area_codes.jsonから一番上の階層のバリューとなっている値（各オフィスコード内のエリアコード）を配列として取得する
    
    Returns:
        List[str]: 一番上の階層のバリューに含まれるエリアコードのリスト（重複なし）
    """
    global area_data
    try:
        if area_data is None:
            area_data = fetch_json_from_file()
        
        if not area_data:
            return []
        
        # 一番上の階層のバリューとなっているエリアコードを取得
        area_codes_set = set()
        for office_code, office_data in area_data.items():
            # 各オフィスコード内のエリアコード（キー）を取得
            area_codes_set.update(office_data.keys())
        
        area_codes_list = list(area_codes_set)
        print(f"エリアコードを取得しました: {len(area_codes_list)}件")
        return area_codes_list
        
    except Exception as e:
        print(f"Unexpected error: {e}")
        return []

def find_area_key_by_children_code(target_code: str) -> str:
    """
    引数でコードが渡されたときに、area_codes.jsonを参照し、
    最下位の階層のバリューから同じ値を探索、見つけたらキー値を返す
    
    Args:
        target_code (str): 検索対象のコード
        
    Returns:
        str: 見つかった場合はキー値、見つからない場合は元のコード
    """
    global area_deta
    try:
        # 初回のみファイル読み取り
        if area_data is None:
            area_data = fetch_json_from_file()
        
        if not area_data:
            return target_code
        
        # 全ての階層を探索
        for office_code, office_data in area_data.items():
            for area_code, children_codes in office_data.items():
                # 最下位の階層（class15_codes配列）で検索
                if target_code in children_codes:
                    return area_code
        
        # 見つからない場合は元のコードを返す
        return target_code
        
    except Exception as e:
        print(f"Unexpected error: {e}")
        return target_code