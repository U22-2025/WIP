"""エリアコード取得用の補助関数群"""

import json
import os
from pathlib import Path
from typing import List


def get_all_area_codes() -> List[str]:
    """
    docs/area_codes.jsonから全てのエリアコード（都道府県コード）を取得
    
    Returns:
        List[str]: エリアコードのリスト
    """
    try:
        # ファイルパスを解決（srcからプロジェクトルートを基準にする）
        current_file = Path(__file__).resolve()
        src_dir = current_file.parent.parent.parent  # src/WIPServerPy/data -> src
        project_root = src_dir.parent  # src -> project root
        area_codes_file = project_root / "docs" / "area_codes.json"
        
        if not area_codes_file.exists():
            print(f"Warning: area_codes.json not found at {area_codes_file}")
            return []
            
        with open(area_codes_file, 'r', encoding='utf-8') as f:
            area_data = json.load(f)
            
        # トップレベルキー（都道府県コード）を取得
        area_codes = list(area_data.keys())
        
        print(f"Loaded {len(area_codes)} area codes from {area_codes_file}")
        return area_codes
        
    except Exception as e:
        print(f"Error loading area codes: {e}")
        return []
