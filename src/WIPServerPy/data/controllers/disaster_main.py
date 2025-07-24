"""Entry point for disaster data processing."""

from .disaster_data_processor import DisasterDataProcessor, DisasterProcessor
import json
import os
from pathlib import Path

JSON_DIR = Path(__file__).resolve().parents[2] / "json"


def main():
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
        print(
            f"Area report times found: {len(result_dict.get('area_report_times', {}))}"
        )
        print(
            f"Sample area report times: {dict(list(result_dict.get('area_report_times', {}).items())[:3])}"
        )

        result_dict, volcano_locations = processor.resolve_volcano_coordinates(
            result_dict
        )

        print(
            f"\nVolcano Location Resolution Results: {json.dumps(volcano_locations, ensure_ascii=False, indent=2)}"
        )

        # Step 4: エリアコードデータの読み込み
        print("Step 4: Loading area codes...")
        with open(JSON_DIR / "area_codes.json", "r", encoding="utf-8") as f:
            area_codes_data = json.load(f)

        # Step 5: エリアコード変換・統合処理
        print("Step 5: Converting area codes...")
        converted_data, converted_report_times = (
            processor.convert_disaster_keys_to_area_codes(result_dict, area_codes_data)
        )
        print(f"Converted report times: {len(converted_report_times)}")
        print(
            f"Sample converted report times: {dict(list(converted_report_times.items())[:3])}"
        )

        # Step 6: ReportDateTimeを含む最終フォーマットに変換
        print("Step 6: Formatting to alert style...")
        final_data = processor.format_to_alert_style(
            converted_data,
            converted_report_times,
            area_codes_data,  # area_codes_dataを渡す
        )

        # Step 7: 処理完了
        print("Step 7: Processing complete...")

        print("Processing completed successfully.")

    except Exception as e:
        print(f"Error in main processing: {e}")
        import traceback

        traceback.print_exc()


# プロジェクトルートをパスに追加 (直接実行時のみ)
