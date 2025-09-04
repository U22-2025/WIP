#!/usr/bin/env python3
"""
update_weather_data.pyから風データ抽出部分だけを抜き出してテストする
"""
import requests
import json

def test_wind_extraction_logic():
    """update_weather_data.pyの風データ抽出ロジックをテスト"""
    area_code = "150000"  # 新潟県
    url = f"https://www.jma.go.jp/bosai/forecast/data/forecast/{area_code}.json"
    
    print(f"=== JMA API から風データ抽出テスト ({area_code}) ===")
    
    try:
        response = requests.get(url)
        data = response.json()
        
        # update_weather_data.pyの処理を模倣
        weather_areas = data[0]["timeSeries"][0]["areas"]
        time_defines = data[0]["timeSeries"][0]["timeDefines"]
        
        print(f"Time defines: {time_defines}")
        print(f"処理対象エリア数: {len(weather_areas)}")
        
        # 各エリアの風データを確認
        for i, area in enumerate(weather_areas):
            area_name = area.get("area", {}).get("name", "Unknown")
            code = area.get("area", {}).get("code", "Unknown")
            
            # 風データ取得 (修正版 - removed_indicesフィルタリングなし)
            winds = area.get("winds", [])
            print(f"\nエリア {i+1}: {area_name} ({code})")
            print(f"  Raw winds: {winds}")
            print(f"  Winds length: {len(winds)}")
            
            # 7日分に拡張（update_weather_data.pyの処理を模倣）
            week_days = 7
            
            # pad_list関数の処理を模倣
            def pad_list(lst, length=7):
                if len(lst) >= length:
                    return lst[:length]
                return lst + [None] * (length - len(lst))
            
            # 7日分にパディング
            winds_padded = pad_list(winds)[:7]
            
            print(f"  Final winds (padded to 7): {winds_padded}")
            
            # area_dataの作成（実際のupdate_weather_data.pyの処理）
            area_data = {
                "parent_code": area_code,
                "area_name": area_name,
                "wind": winds_padded,
            }
            
            print(f"  Area data wind field: {area_data['wind']}")
            
            # Nullでないwind値があるかチェック
            non_null_winds = [w for w in winds_padded if w is not None]
            if non_null_winds:
                print(f"  ✓ Non-null wind values: {len(non_null_winds)}")
            else:
                print(f"  ✗ All wind values are null!")
                
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_wind_extraction_logic()