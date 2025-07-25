# -*- coding: utf-8 -*-
"""
地震情報取得デバッグ用スクリプト

少数のURLで手軽に地震情報取得をテストできます。
"""

import json
import sys
import os
from pathlib import Path

# パスを追加して直接実行にも対応
sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

from WIPServerPy.data.controllers.earthquake_data_processor import (
    EarthquakeDataProcessor,
)

JSON_DIR = Path(__file__).resolve().parent.parent / "json"


def main():
    """
    地震情報処理のデバッグ用メイン関数

    少数のURLで地震情報取得をテストし、
    統合処理の動作を確認します。
    """
    print("=== 地震情報取得デバッグ開始 ===")

    # EarthquakeDataProcessorのインスタンスを作成
    processor = EarthquakeDataProcessor()

    try:
        # Step 1: XMLファイルリストの取得（制限付き）
        url_list = processor.get_earthquake_xml_list()
        if not url_list:
            print("No URLs found. Exiting.")
            return

        # デバッグ用に最初の20URLに制限
        debug_url_list = url_list[:20]
        print(
            f"Debug mode: Using {len(debug_url_list)} URLs (out of {len(url_list)} total)"
        )

        # URLリストを表示
        print("\nProcessing URLs:")
        for i, url in enumerate(debug_url_list, 1):
            print(f"  {i:2d}. {url}")

        # Step 2: 地震情報の取得・統合
        json_result = processor.get_earthquake_info(debug_url_list)
        print("\n=== Earthquake Info Processing Complete ===")

        # Step 3: JSONデータの解析
        try:
            result_dict = json.loads(json_result)
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON: {e}")
            return

        # Step 4: 結果の詳細表示
        print("\n=== 処理結果詳細 ===")
        area_mapping = result_dict.get("area_kind_mapping", {})
        print(f"処理されたエリア数: {len(area_mapping)}")

        # 各エリアの地震情報を表示
        for area_code, disasters in area_mapping.items():
            print(f"\nエリアコード: {area_code}")
            print(f"  災害情報数: {len(disasters)}")
            for disaster in disasters:
                print(f"    - {disaster}")

        # Step 5: エリアコードデータの読み込み
        area_codes_file = JSON_DIR / "area_codes.json"
        if area_codes_file.exists():
            with open(area_codes_file, "r", encoding="utf-8") as f:
                area_codes_data = json.load(f)

            # Step 6: エリアコード変換・統合処理
            converted_data, converted_report_times = (
                processor.convert_earthquake_keys_to_area_codes(
                    result_dict, area_codes_data
                )
            )

            # Step 7: 最終結果を新しいフォーマットで保存
            final_formatted_data = processor.format_to_alert_style(
                converted_data, converted_report_times, area_codes_data
            )

            print(f"\n=== 処理完了 ===")
            print(f"最終データのエリア数: {len(final_formatted_data)}")

            # 統合処理の結果を確認
            print("\n=== 統合処理結果確認 ===")
            for area_code, area_data in final_formatted_data.items():
                # area_codeが特別なキー（disaster_pulldatetime等）の場合はスキップ
                if area_code in ["disaster_pulldatetime"]:
                    continue

                # area_dataが辞書型かどうかチェック
                if not isinstance(area_data, dict):
                    print(
                        f"Warning: area_data for {area_code} is not a dict: {type(area_data)}"
                    )
                    continue

                disasters = area_data.get("disaster", [])
                earthquake_count = sum(1 for d in disasters if "地震情報" in d)
                if earthquake_count > 0:
                    print(f"\nエリア {area_code}:")
                    print(f"  地震情報数: {earthquake_count}")
                    for disaster in disasters:
                        if "地震情報" in disaster:
                            print(f"    - {disaster}")
        else:
            print(f"Warning: area_codes.json not found at {area_codes_file}")

        print("\n=== デバッグ処理完了 ===")

    except Exception as e:
        print(f"Error in earthquake debug processing: {e}")
        import traceback

        traceback.print_exc()


