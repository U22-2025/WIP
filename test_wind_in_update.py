#!/usr/bin/env python3
import sys
import os

# プロジェクトのパスを設定
sys.path.insert(0, 'src')
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# 必要なモジュールをインポート
from WIPServerPy.scripts.update_weather_data import get_data
from WIPServerPy.data.get_codes import get_all_area_codes

def test_wind_data_extraction():
    """風データが正しく抽出されるかテスト"""
    print("=== 風データ抽出テスト ===")
    
    # 新潟県のみを対象にテスト
    test_area_codes = ["150000"]  # 新潟県
    
    print(f"テスト対象エリアコード: {test_area_codes}")
    
    # get_data関数を直接呼び出し（デバッグモード、Redisに保存しない）
    try:
        result = get_data(test_area_codes, debug=True, save_to_redis=False)
        print(f"get_data関数実行完了: スキップされたエリア = {result}")
        
    except Exception as e:
        print(f"get_data関数でエラー: {e}")
        import traceback
        traceback.print_exc()

def test_area_codes():
    """エリアコード取得のテスト"""
    print("=== エリアコード取得テスト ===")
    
    try:
        area_codes = get_all_area_codes()
        print(f"取得されたエリアコード数: {len(area_codes)}")
        print(f"最初の5つのエリアコード: {area_codes[:5] if area_codes else '(なし)'}")
        
        if "150000" in area_codes:
            print("✓ 新潟県コード(150000)が含まれています")
        else:
            print("✗ 新潟県コード(150000)が見つかりません")
            
        return area_codes
        
    except Exception as e:
        print(f"エリアコード取得でエラー: {e}")
        import traceback
        traceback.print_exc()
        return []

if __name__ == "__main__":
    # エリアコード取得テスト
    area_codes = test_area_codes()
    
    print("\n" + "="*50 + "\n")
    
    # 風データ抽出テスト
    test_wind_data_extraction()