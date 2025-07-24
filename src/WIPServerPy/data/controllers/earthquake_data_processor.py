"""High level earthquake data processing controller."""

import json
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime

from WIPServerPy.data.processors.earthquake_processor import EarthquakeProcessor
from WIPServerPy.data.processors.time_utils import TimeProcessor
from WIPServerPy.data.processors.area_code_validator import AreaCodeValidator


class EarthquakeDataProcessor:
    """
    地震データ処理統合クラス（メインコントローラー）

    役割:
    - 地震情報の処理フローの制御
    - 各専門クラスの連携調整
    - ファイル入出力の管理
    - エラーハンドリング
    - データ変換・統合の統括
    """

    def __init__(self):
        # 各専門クラスのインスタンス化
        self.xml_processor = EarthquakeProcessor()
        self.time_processor = TimeProcessor()
        self.validator = AreaCodeValidator()

    def get_earthquake_xml_list(self) -> List[str]:
        """
        eqvol.xmlファイルからXMLファイルURLリストを取得

        Returns:
            XMLファイルURLのリスト
        """
        return self.xml_processor.get_feed_entry_urls(
            "https://www.data.jma.go.jp/developer/xml/feed/eqvol.xml"
        )

    def get_earthquake_info(
        self, url_list: List[str], output_json_path: Optional[str] = None
    ) -> str:
        """
        複数XMLファイルから地震情報を取得・統合

        Args:
            url_list: 処理するXMLファイルURLリスト
            output_json_path: 出力JSONファイルパス（オプション）

        Returns:
            統合された地震情報JSON文字列
        """
        result = self.xml_processor.process_multiple_urls(url_list)
        json_output = json.dumps(result, ensure_ascii=False, indent=2)

        # ファイル出力（オプション）
        if output_json_path:
            self.xml_processor.save_json(result, output_json_path)

        return json_output

    def convert_earthquake_keys_to_area_codes(
        self,
        earthquake_data: Dict,
        area_codes_data: Dict,
        output_json_path: Optional[str] = None,
    ) -> Tuple[Dict, Dict]:
        """
        地震データのエリアコード変換・無効データ除去・時間統合

        Args:
            earthquake_data: 変換対象の地震データ
            area_codes_data: エリアコード階層データ
            output_json_path: 出力JSONファイルパス（オプション）

        Returns:
            (変換・統合済みの地震データ, 変換済みReportDateTime)のタプル
        """
        if "area_kind_mapping" not in earthquake_data:
            print("Warning: 'area_kind_mapping' key not found in earthquake data")
            return {}, {}

        area_kind_mapping = earthquake_data["area_kind_mapping"]
        print(f"Debug: type of area_kind_mapping: {type(area_kind_mapping)}")
        print(f"Debug: area_kind_mapping is None: {area_kind_mapping is None}")
        if area_kind_mapping is None:
            print("Error: area_kind_mapping is None. Returning empty dicts.")
            return {}, {}

        area_report_times = earthquake_data.get("area_report_times", {})

        converted_mapping = defaultdict(list)
        converted_report_times = {}
        invalid_codes = []

        # 無効なエリアコードを特定
        for earthquake_key in area_kind_mapping.keys():
            if not self.validator.is_valid_area_code(
                earthquake_key, area_codes_data, {}
            ):
                invalid_codes.append(earthquake_key)

        # 無効コードの報告
        if invalid_codes:
            print(
                f"\nDetected {len(invalid_codes)} invalid area codes: {invalid_codes}"
            )

        # エリアコード変換処理
        for earthquake_key, earthquake_values in area_kind_mapping.items():
            # 無効なコードをスキップ（削除）
            if earthquake_key in invalid_codes:
                print(f"Removing invalid area code: {earthquake_key}")
                continue

            # 子コードから親コードへの変換試行
            found_area_code = self.validator.find_area_code_mapping(
                earthquake_key, area_codes_data
            )
            target_key = found_area_code if found_area_code else earthquake_key

            # データの統合
            for value in earthquake_values:
                if value not in converted_mapping[target_key]:
                    converted_mapping[target_key].append(value)

            # ReportDateTimeの転送
            if earthquake_key in area_report_times:
                converted_report_times[target_key] = area_report_times[earthquake_key]

            if not found_area_code:
                print(
                    f"No conversion found for: {earthquake_key} (keeping original key)"
                )

        if invalid_codes:
            print(
                f"\nSuccessfully removed {len(invalid_codes)} invalid area codes from JSON data"
            )

        # 時間範囲の統合処理
        result = dict(converted_mapping)
        consolidated_result = self.time_processor.consolidate_time_ranges(result)

        # ファイル出力（オプション）
        if output_json_path:
            self.xml_processor.save_json(consolidated_result, output_json_path)

        return consolidated_result, converted_report_times

    def _consolidate_earthquakes_for_area(self, earthquake_list: List[str]) -> str:
        """
        一つのエリアコードの複数地震を一つの文字列に統合

        Args:
            earthquake_list: 地震情報のリスト

        Returns:
            統合された地震情報文字列
        """
        if not earthquake_list:
            return ""

        if len(earthquake_list) == 1:
            return earthquake_list[0]

        # 地震情報から詳細を抽出してソート
        earthquake_details = []
        for earthquake in earthquake_list:
            detail = self._extract_earthquake_detail(earthquake)
            if detail:
                earthquake_details.append(detail)

        # 時系列順にソート
        earthquake_details.sort(key=lambda x: x.get("datetime", ""))

        # 統合文字列を作成
        # 例: "地震情報(07/18_08:20_M5.2_震度4)(07/18_14:29_M3.1_震度3)"
        if earthquake_details:
            consolidated_parts = []
            for detail in earthquake_details:
                datetime_part = detail.get("datetime", "")
                magnitude_part = detail.get("magnitude", "")
                intensity_part = detail.get("intensity", "")

                if datetime_part and magnitude_part and intensity_part:
                    part = f"({datetime_part}_{magnitude_part}_{intensity_part})"
                    consolidated_parts.append(part)

            if consolidated_parts:
                return f"地震情報{''.join(consolidated_parts)}"

        # フォールバック: 既存の地震情報をそのまま結合
        return " | ".join(earthquake_list)

    def _extract_earthquake_detail(self, earthquake_info: str) -> Dict[str, str]:
        """
        地震情報から詳細情報を抽出

        Args:
            earthquake_info: 地震情報文字列

        Returns:
            詳細情報の辞書
        """
        # 例: "地震情報(07/18_08:20_M5.2_東京都23区)_震度4"
        details = {}

        try:
            # 括弧内の情報を抽出
            if "地震情報(" in earthquake_info and ")" in earthquake_info:
                start_idx = earthquake_info.find("地震情報(")
                end_idx = earthquake_info.find(")", start_idx)
                if start_idx != -1 and end_idx != -1:
                    content = earthquake_info[
                        start_idx + 4 : end_idx
                    ]  # "地震情報("の後から")"の前まで
                    parts = content.split("_")

                    # 日時を抽出（例: "07/18_08:20"）
                    datetime_parts = []
                    for part in parts:
                        if "/" in part or ":" in part:  # 日時情報
                            datetime_parts.append(part)
                        elif part.startswith("M"):  # マグニチュード情報
                            details["magnitude"] = part

                    if datetime_parts:
                        details["datetime"] = "_".join(datetime_parts)

            # 震度情報を抽出
            if "_震度" in earthquake_info:
                intensity_part = earthquake_info.split("_震度")[-1]
                details["intensity"] = f"震度{intensity_part}"

        except:
            pass

        return details if all(details.values()) else {}

    def format_to_alert_style(
        self,
        area_kind_mapping: Dict[str, List[str]],
        area_report_times: Dict[str, str] = None,
        area_codes_data: Dict = None,
    ) -> Dict[str, Any]:
        """
        地震データを警報・注意報データと同じフォーマットに変換

        Args:
            area_kind_mapping: エリアコード別の地震種別マッピング
            area_report_times: エリアコード別のReportDateTime（オプション）
            area_codes_data: エリアコード階層データ（親コードとエリア名取得用）

        Returns:
            警報・注意報データと同じフォーマットの辞書
        """

        # トップレベルの構造を初期化
        final_output = {
            "disaster_pulldatetime": datetime.now().isoformat(timespec="seconds")
            + "+09:00",
        }

        for area_code, earthquake_list in area_kind_mapping.items():
            # 複数の地震がある場合は一つの文字列に統合
            if len(earthquake_list) > 1:
                consolidated_earthquake = self._consolidate_earthquakes_for_area(
                    earthquake_list
                )
                final_output[area_code] = {
                    "disaster": [consolidated_earthquake]  # 統合された地震情報
                }
            else:
                final_output[area_code] = {
                    "disaster": earthquake_list  # 単一の地震情報
                }

        print(final_output)
        return final_output
