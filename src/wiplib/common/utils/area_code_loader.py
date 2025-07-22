import json
from pathlib import Path

DEFAULT_AREA_CODES_PATH = Path(__file__).resolve().parents[2] / 'logs' / 'json' / 'area_codes.json'

def load_area_codes(path: str | Path | None = None):
    """area_codes.jsonを読み込むユーティリティ

    Args:
        path: 読み込むJSONファイルのパス。Noneの場合はデフォルト値を使用。

    Returns:
        dict: エリアコード辞書
    """
    json_path = Path(path) if path else DEFAULT_AREA_CODES_PATH
    with open(json_path, 'r', encoding='utf-8') as f:
        return json.load(f)
