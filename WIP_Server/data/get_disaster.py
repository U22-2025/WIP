# -*- coding: utf-8 -*-
"""
災害情報取得スクリプト

リファクタリング済みのDisasterDataProcessorを使用して
災害情報を取得・処理し、Redisに格納します。

使用方法:
    python get_disaster.py
"""

import json
from disaster_processor import DisasterDataProcessor
from redis_manager import create_redis_manager


def main():
    """
    災害情報処理のメイン関数
    
    DisasterDataProcessorを使用して災害情報を取得し、
    エリアコード変換、火山座標解決、時間統合を行います。
    """
    print("=== 災害情報取得開始 ===")
    
    # DisasterDataProcessorのインスタンスを作成
    processor = DisasterDataProcessor()
    
    # 災害情報処理を実行
    try:
        # Step 1: XMLファイルリストの取得
        url_list = processor.get_disaster_xml_list()
        if not url_list:
            print("No URLs found. Exiting.")
            return
        
        print(f"Found {len(url_list)} disaster XML files to process.")
        
        # Step 2: 災害情報の取得・統合
        json_result = processor.get_disaster_info(url_list, 'wip/json/disaster_data.json')
        print("\n=== Disaster Info Processing Complete ===")
        print(f"Debug: json_result type: {type(json_result)}")
        # print(f"Debug: json_result content (first 100 chars): {json_result[:100]}") # エンコーディングエラー回避のためコメントアウト
        
        # Step 3: 火山座標の解決処理
        try:
            result_dict = json.loads(json_result)
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON: {e}")
            print(f"Problematic JSON: {json_result}")
            return # 処理を中断
        result_dict, volcano_locations = processor.resolve_volcano_coordinates(result_dict)
        
        print(f"\nVolcano Location Resolution Results: {len(volcano_locations)} locations resolved.") # 簡潔な表示に変更
        
        # Step 4: エリアコードデータの読み込み
        with open('wip/json/area_codes.json', 'r', encoding='utf-8') as f:
            area_codes_data = json.load(f)
        print(f"Debug: area_codes_data type: {type(area_codes_data)}")
        print(f"Debug: area_codes_data is None: {area_codes_data is None}")
        
        # Step 5: エリアコード変換・統合処理
        converted_data, converted_report_times = processor.convert_disaster_keys_to_area_codes(
            result_dict, area_codes_data
        )
        print(f"Debug: converted_data type: {type(converted_data)}")
        print(f"Debug: converted_data is None: {converted_data is None}")
        print(f"Debug: converted_report_times type: {type(converted_report_times)}")
        print(f"Debug: converted_report_times is None: {converted_report_times is None}")
        
        # Step 6: 最終結果を新しいフォーマットで保存（ReportDateTime付き）
        final_formatted_data = processor.format_to_alert_style(converted_data, converted_report_times, area_codes_data)
        
        with open('wip/json/disaster_data.json', 'w', encoding='utf-8') as f:
            json.dump(final_formatted_data, f, ensure_ascii=False, indent=2)
        
        print("=== 災害情報取得完了 ===")
        print("Processing completed successfully.")
        
        # Redis管理クラスを使用してデータを更新
        print("\n=== Redisデータ更新開始 ===")
        
        try:
            # Redis管理クラスのインスタンスを作成
            redis_manager = create_redis_manager(debug=True)
            
            # 災害情報を更新
            result = redis_manager.update_disasters(final_formatted_data)
            
            # 結果を表示
            print(f"\n=== Redis更新結果 ===")
            print(f"更新されたエリア: {result['updated']}件")
            print(f"新規作成されたエリア: {result['created']}件")
            print(f"エラー: {result['errors']}件")
            print(f"合計処理エリア: {result['updated'] + result['created']}件")
            
            # 接続を閉じる
            redis_manager.close()
            
            print("=== Redisデータ更新完了 ===")
            
        except Exception as e:
            print(f"Redis更新エラー: {e}")
        
    except Exception as e:
        print(f"Error in disaster processing: {e}")


if __name__ == "__main__":
    main()
