"""Entry point for disaster data processing."""

from .disaster_data_processor import DisasterDataProcessor, DisasterProcessor
import json
import os
from pathlib import Path

# デフォルトのarea_codes.jsonパス
DEFAULT_AREA_CODES = Path(__file__).resolve().parents[1] / "area_codes.json"

def main(area_codes_path=None):
    """
    メイン処理関数
    """
    try:
        processor = DisasterDataProcessor()
        
        # Step 1: XMLファイルリストの取得
        print("Step 1: Getting XML file list...")
        url_list = processor.get_disaster_xml_list()
        print(f"Found {len(url_list)} URLs")
        if not url_list:
            print("No URLs found. Exiting.")
            return
        
        # Step 2: 災害情報の取得・統合
        print("Step 2: Processing disaster info...")
        json_result = processor.get_disaster_info(url_list)
        print("\n=== Disaster Info Processing Complete ===")
        
        # Step 3: 火山座標の解決処理
        print("Step 3: Resolving volcano coordinates...")
        result_dict = json.loads(json_result)
        print(f"Area report times found: {len(result_dict.get('area_report_times', {}))}")
        print(f"Sample area report times: {dict(list(result_dict.get('area_report_times', {}).items())[:3])}")
        
        result_dict, volcano_locations = processor.resolve_volcano_coordinates(result_dict)
        
        print(f"\nVolcano Location Resolution Results: {json.dumps(volcano_locations, ensure_ascii=False, indent=2)}")
        
        # Step 4: エリアコードデータの読み込み
        print("Step 4: Loading area codes...")
        path = Path(area_codes_path) if area_codes_path else DEFAULT_AREA_CODES
        with open(path, 'r', encoding='utf-8') as f:
            area_codes_data = json.load(f)
        
        # Step 5: エリアコード変換・統合処理
        print("Step 5: Converting area codes...")
        converted_data, converted_report_times = processor.convert_disaster_keys_to_area_codes(
            result_dict, area_codes_data
        )
        print(f"Converted report times: {len(converted_report_times)}")
        print(f"Sample converted report times: {dict(list(converted_report_times.items())[:3])}")
        
        # Step 6: ReportDateTimeを含む最終フォーマットに変換
        print("Step 6: Formatting to alert style...")
        final_data = processor.format_to_alert_style(
            converted_data, converted_report_times, area_codes_data # area_codes_dataを渡す
        )
        
        # Step 7: 最終結果の保存
        print("Step 7: Saving final data... (skipped)")
        
        print("Processing completed successfully.")
        
    except Exception as e:
        print(f"Error in main processing: {e}")
        import traceback
        traceback.print_exc()

# プロジェクトルートをパスに追加 (直接実行時のみ)
if __name__ == "__main__":
    current_file = Path(__file__).absolute()
    project_root = str(current_file.parent.parent.parent)
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    
    # xml_baseモジュールのインポート用に追加パス設定
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    
if __name__ == "__main__":
    import sys
    import argparse

    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        # 簡易テストモード
        if len(sys.argv) < 3:
            print("テストURLを指定してください")
            print("使用例: python disaster_main.py --test [URL]")
            sys.exit(1)
            
        processor = DisasterProcessor()
        result = processor._process_single_url(sys.argv[2])
        print(f"テスト結果:\n{json.dumps(result, ensure_ascii=False, indent=2)}")
    else:
        parser = argparse.ArgumentParser(description="災害データ処理を実行します")
        parser.add_argument("--area-codes-path", dest="area_codes_path", help="area_codes.json のパス", default=None)
        args = parser.parse_args()

        # 通常のmain関数実行
        main(area_codes_path=args.area_codes_path)


