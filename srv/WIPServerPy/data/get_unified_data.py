# -*- coding: utf-8 -*-
"""
統合データ取得スクリプト

UnifiedDataProcessorを使用して
地震情報と災害情報を自動判別・統合処理し、Redisに格納します。

使用方法:
    python get_unified_data.py
"""

import json
import sys 
import os 
from pathlib import Path
# パスを追加して直接実行にも対応
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from WIPServerPy.data.controllers.unified_data_processor import UnifiedDataProcessor
from WIPServerPy.data.redis_manager import create_redis_manager

# デフォルトのarea_codes.jsonパス
DEFAULT_AREA_CODES = Path(__file__).resolve().parent.parent / "area_codes.json"

def main(area_codes_path=None):
    """
    統合データ処理のメイン関数
    
    UnifiedDataProcessorを使用してXMLタイプを自動判別し、
    地震情報と災害情報を適切に処理します。
    """
    print("=== 統合データ取得開始 ===")
    
    # UnifiedDataProcessorのインスタンスを作成
    processor = UnifiedDataProcessor()
    
    # 統合データ処理を実行
    try:
        # Step 1: XMLファイルリストの取得
        url_list = processor.get_xml_list()
        if not url_list:
            print("No URLs found. Exiting.")
            return
        
        print(f"Found {len(url_list)} XML files to process.")
        
        # Step 2: 統合データの取得・分類処理
        disaster_json, earthquake_json = processor.process_unified_data(url_list)
        print("\n=== Unified Data Processing Complete ===")
        
        # Step 3: エリアコードデータの読み込み
        path = Path(area_codes_path) if area_codes_path else DEFAULT_AREA_CODES
        with open(path, 'r', encoding='utf-8') as f:
            area_codes_data = json.load(f)
        
        # Step 4: 災害データの処理
        disaster_result_dict = {}
        disaster_converted_data = {}
        disaster_converted_report_times = {}
        
        if disaster_json and disaster_json != '{}':
            disaster_result_dict = json.loads(disaster_json)
            
            # 火山座標解決処理（Location clientエラーの場合はスキップ）
            try:
                disaster_result_dict, volcano_locations = processor.resolve_volcano_coordinates(disaster_result_dict)
                print(f"\nVolcano Location Resolution Results: {len(volcano_locations)} locations resolved.")
            except Exception as e:
                print(f"Warning: Volcano coordinate resolution failed: {e}")
                print("Continuing without volcano coordinate resolution...")
                volcano_locations = {}
            
            # エリアコード変換・統合処理
            disaster_converted_data, disaster_converted_report_times = processor.convert_disaster_keys_to_area_codes(
                disaster_result_dict, area_codes_data
            )
            
            # 最終結果をフォーマット
            disaster_final_data = processor.format_to_alert_style(
                disaster_converted_data, disaster_converted_report_times, area_codes_data, 'disaster'
            )
            
            # 災害データ保存（ファイル出力は不要のため省略）
            
            print(f"=== 災害情報処理完了 ===")
            print(f"処理されたエリア数: {len(disaster_converted_data)}")
        
        # Step 5: 地震データの処理
        earthquake_result_dict = {}
        earthquake_converted_data = {}
        earthquake_converted_report_times = {}
        
        if earthquake_json and earthquake_json != '{}':
            earthquake_result_dict = json.loads(earthquake_json)
            
            # エリアコード変換・統合処理
            earthquake_converted_data, earthquake_converted_report_times = processor.convert_earthquake_keys_to_area_codes(
                earthquake_result_dict, area_codes_data
            )
            
            # 地震データを災害データ形式にフォーマット
            earthquake_final_data = processor.format_to_alert_style(
                earthquake_converted_data, earthquake_converted_report_times, area_codes_data, 'earthquake'
            )
            
            # 地震データ保存（ファイル出力は不要のため省略）
            
            print(f"=== 地震情報処理完了 ===")
            print(f"処理されたエリア数: {len(earthquake_converted_data)}")
            
            # Step 6: 地震データを災害データに統合
            if disaster_converted_data or earthquake_converted_data:
                print(f"\n=== 地震データを災害データに統合 ===")
                merged_disaster_data = processor.merge_earthquake_into_disaster(
                    disaster_final_data if disaster_converted_data else {}, 
                    earthquake_final_data if earthquake_converted_data else {}
                )
                
                # 統合されたデータを保存（ファイル出力は不要のため省略）
                
                print(f"統合完了: {len(merged_disaster_data) - 1}エリアの災害データ（地震データ含む）")
        
        print("=== 統合データ取得完了 ===")
        
        # Redis管理クラスを使用してデータを更新
        print("\n=== Redisデータ更新開始 ===")
        
        try:
            # Redis管理クラスのインスタンスを作成
            redis_manager = create_redis_manager(debug=True)
            
            disaster_result = {'updated': 0, 'created': 0, 'errors': 0}
            earthquake_result = {'updated': 0, 'created': 0, 'errors': 0}
            
            # 統合された災害情報（地震データ含む）を更新
            if disaster_converted_data or earthquake_converted_data:
                # 統合されたデータを使用
                if 'merged_disaster_data' in locals():
                    disaster_result = redis_manager.update_disasters(merged_disaster_data)
                elif disaster_converted_data:
                    disaster_result = redis_manager.update_disasters(disaster_final_data)
                else:
                    disaster_result = {'updated': 0, 'created': 0, 'errors': 0}
                
                print(f"\n=== 災害情報Redis更新結果（地震データ含む） ===")
                print(f"更新されたエリア: {disaster_result['updated']}件")
                print(f"新規作成されたエリア: {disaster_result['created']}件")
                print(f"エラー: {disaster_result['errors']}件")
            
            print(f"\n=== 総合更新結果 ===")
            print(f"合計更新エリア: {disaster_result['updated']}件")
            print(f"合計新規作成エリア: {disaster_result['created']}件")
            print(f"合計エラー: {disaster_result['errors']}件")
            
            # 接続を閉じる
            redis_manager.close()
            
            print("=== Redisデータ更新完了 ===")
            
        except Exception as e:
            print(f"Redis更新エラー: {e}")
        
    except Exception as e:
        print(f"Error in unified processing: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="統合データを取得してRedisに保存します")
    parser.add_argument("--area-codes-path", dest="area_codes_path", help="area_codes.json のパス", default=None)
    args = parser.parse_args()

    main(area_codes_path=args.area_codes_path)
