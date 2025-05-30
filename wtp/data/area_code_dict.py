import requests

def fetch_area_json() -> dict:
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

