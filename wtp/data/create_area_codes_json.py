import json
import requests
from typing import Optional, List, Dict

# area_codes.jsonを作成する
# このファイルは初回のみ実行

def fetch_json_from_url() -> Optional[dict]:
    """
    気象庁のエリアコードJSONを取得する
    
    Returns:
        Optional[dict]: エリアコードの辞書データ、失敗時はNone
    """
    try:
        url = "https://www.jma.go.jp/bosai/common/const/area.json"
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"エリアコードJSONの取得に失敗しました: {e}")
        return None


def _map_office_code(offices_code: str) -> str:
    """
    オフィスコードのマッピングを行う
    
    Args:
        offices_code (str): 元のオフィスコード
        
    Returns:
        str: マッピング後のオフィスコード
    """
    mapping = {
        "014030": "014100",
        "460040": "460100"
    }
    return mapping.get(offices_code, offices_code)


def _process_area_code(area_code: str, area_json: dict, result: Dict[str, Dict[str, List[str]]], mapped_offices_code: str) -> None:
    """
    エリアコードを処理して結果辞書に追加する
    
    Args:
        area_code (str): エリアコード
        area_json (dict): エリアコードJSONデータ
        result (Dict[str, Dict[str, List[str]]]): 結果を格納する辞書
        mapped_offices_code (str): マッピング後のオフィスコード
    """
    # class10sのデータを取得
    area_data = area_json.get('class10s', {}).get(area_code)
    if not area_data:
        return
        
    # class10_codeのキーが存在しない場合は空配列を作成
    if area_code not in result[mapped_offices_code]:
        result[mapped_offices_code][area_code] = []

    # class10sの子要素（class20s）を処理
    children_codes = area_data.get('children', [])
    for child_code in children_codes:
        class15_data = area_json.get('class15s', {}).get(child_code)
        if class15_data:
            grandchildren = class15_data.get('children', [])
            result[mapped_offices_code][area_code].extend(grandchildren)


def map_area_code_to_children(offices_code: str, area_json: dict, result: Dict[str, Dict[str, List[str]]]) -> None:
    """
    オフィスコードに対応する階層構造を結果辞書に追加する
    
    Args:
        offices_code (str): オフィスコード
        area_json (dict): エリアコードJSONデータ
        result (Dict[str, Dict[str, List[str]]]): 結果を格納する辞書
    """
    try:
        if not area_json:
            print("エリアコードJSONの取得に失敗したため、処理を中止します")
            return
        
        # officesのデータを取得
        office_data = area_json.get('offices', {}).get(offices_code)
        if not office_data:
            print(f"指定されたofficeコード {offices_code} が見つかりません")
            return

        # officeコードの変換
        mapped_offices_code = _map_office_code(offices_code)

        # 結果辞書にofficeコードのエントリを初期化（必要なら）
        if mapped_offices_code not in result:
            result[mapped_offices_code] = {}
        
        # officeの子要素（class10s）を処理
        for area_code in office_data.get('children', []):
            _process_area_code(area_code, area_json, result, mapped_offices_code)
            
        print(f"officeコード {offices_code} の階層構造を追加しました")

    except Exception as e:
        print(f"エラーが発生しました: {e}")


def generate_area_codes_file() -> None:
    """
    エリアコードファイルを生成する
    """
    area_json = fetch_json_from_url()
    if not area_json:
        print("エリアコードJSONの取得に失敗したため、ファイル生成を中止します")
        return
        
    result = {}
    offices_codes = list(area_json.get('offices', {}).keys())
    
    print(f"エリアコードを取得しました: {len(offices_codes)}件")
    
    for code in offices_codes:
        map_area_code_to_children(code, area_json, result)

    try:
        with open("wtp/data/area_codes.json", "w", encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=4)
        print("area_codes.jsonファイルを生成しました")
    except IOError as e:
        print(f"ファイルの書き込みに失敗しました: {e}")


def main() -> None:
    """
    メイン処理：エリアコードファイルを生成する
    """
    generate_area_codes_file()


if __name__ == "__main__":
    main()
