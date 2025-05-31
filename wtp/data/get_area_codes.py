import json
import requests

def fetch_json() -> dict:
    """
    気象庁のエリアコードJSONを取得する
    
    Returns:
        dict: エリアコードの辞書データ
    """
    try:
        url = "https://www.jma.go.jp/bosai/common/const/area.json"
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"エリアコードJSONの取得に失敗しました: {e}")
        return None

import json

def get_offices_codes():
    """area.jsonからofficesのキーを取得してグローバル変数に格納"""
    try:
        # area.jsonをURLから取得
        global area_json
        if not area_json:
            print("エリアコードJSONの取得に失敗したため、処理を中止します")
            offices_codes = []
            return

        # officesのキーを取得
        offices_codes = list(area_json.get('offices', {}).keys())
        print(f"エリアコードを取得しました: {len(offices_codes)}件")
        
    except Exception as e:
        print(f"エラーが発生しました: {e}")
        offices_codes = []

    return offices_codes


def map_area_code_to_children(offices_code: str, result: dict) -> None:
    try:
        global area_json
        if not area_json:
            print("エリアコードJSONの取得に失敗したため、処理を中止します")
            return
        
        # officesのデータを取得
        office_data = area_json.get('offices', {}).get(offices_code)
        if not office_data:
            print(f"指定されたofficeコード {offices_code} が見つかりません")
            return

        # officeコードの変換
        mapped_offices_code = offices_code
        if offices_code == "014030":
            mapped_offices_code = "014100"
        elif offices_code == "460040":
            mapped_offices_code = "460100"

        # 結果辞書にofficeコードのエントリを初期化（必要なら）
        if mapped_offices_code not in result:
            result[mapped_offices_code] = {}
        
        # officeの子要素（class10s）を処理
        for area_code in office_data.get('children', []):
            # class10sのデータを取得
            area_data = area_json.get('class10s', {}).get(area_code)
            if area_data:
                # class10_codeのキーが存在しない場合は空配列を作成
                if area_code not in result[mapped_offices_code]:
                    result[mapped_offices_code][area_code] = []

                # class10sの子要素（class20s）を配列として保存
                children_codes = area_data.get('children', [])

                for child_code in children_codes:
                    grandchilds = area_json.get('class15s', {}).get(child_code).get('children',[])
                    result[mapped_offices_code][area_code].extend(grandchilds)
        print(f"officeコード {offices_code} の階層構造を追加しました")

    except Exception as e:
        print(f"エラーが発生しました: {e}")

area_json = fetch_json()
result = {}
offices_codes = get_offices_codes()
for code in offices_codes:
    map_area_code_to_children(code,result)

with open("wtp/data/area_codes.json","w",encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False, indent=4)