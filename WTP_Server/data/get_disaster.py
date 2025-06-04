"""
災害情報取得スクリプト

リファクタリング済みのDisasterDataProcessorを使用して
災害情報を取得・処理します。

使用方法:
    python get_disaster.py
"""

from disaster_processor import DisasterDataProcessor


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
        json_result = processor.get_disaster_info(url_list, 'wtp/json/disaster_data.json')
        print("\n=== Disaster Info Processing Complete ===")
        
        # Step 3: 火山座標の解決処理
        import json
        result_dict = json.loads(json_result)
        result_dict, volcano_locations = processor.resolve_volcano_coordinates(result_dict)
        
        print(f"\nVolcano Location Resolution Results: {json.dumps(volcano_locations, ensure_ascii=False, indent=2)}")
        
        # Step 4: エリアコードデータの読み込み
        with open('wtp/json/area_codes.json', 'r', encoding='utf-8') as f:
            area_codes_data = json.load(f)
        
        # Step 5: エリアコード変換・統合処理
        converted_data = processor.convert_disaster_keys_to_area_codes(
            result_dict, area_codes_data, 'wtp/json/disaster_data.json'
        )
        
        # Step 6: 最終結果の保存
        updated_disaster_data = {
            "area_kind_mapping": converted_data,
            "volcano_coordinates": result_dict.get("volcano_coordinates", {}),
        }
        
        with open('wtp/json/disaster_data.json', 'w', encoding='utf-8') as f:
            json.dump(updated_disaster_data, f, ensure_ascii=False, indent=2)
        
        print("=== 災害情報取得完了 ===")
        print("Processing completed successfully.")
        
    except Exception as e:
        print(f"Error in disaster processing: {e}")


if __name__ == "__main__":
    main()
