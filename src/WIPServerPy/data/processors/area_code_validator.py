"""Area code validation utilities."""

from typing import Dict, Optional
from WIPCommonPy.clients.location_client import LocationClient
from WIPServerPy.data.processors.volcano_processor import VolcanoCoordinateProcessor


class AreaCodeValidator:
    """
    エリアコード検証・変換クラス

    役割:
    - エリアコードの有効性検証
    - 子コードから親コードへのマッピング
    - 火山コードとエリアコードの統合検証
    - 無効コードの特定
    """

    @staticmethod
    def is_valid_area_code(
        code: str, area_codes_data: Dict, volcano_coordinates: Dict
    ) -> bool:
        """
        エリアコードの有効性を検証

        Args:
            code: 検証対象のコード
            area_codes_data: 正式エリアコードデータ
            volcano_coordinates: 火山座標データ

        Returns:
            有効な場合True、無効な場合False
        """
        # 火山座標に存在する場合は有効
        if code in volcano_coordinates:
            return True

        # area_codes_dataに存在するかチェック
        for office_data in area_codes_data.values():
            for area_code, children_codes in office_data.items():
                if code == area_code or code in children_codes:
                    return True
        return False

    @staticmethod
    def find_area_code_mapping(child_code: str, area_codes_data: Dict) -> Optional[str]:
        """
        子コードに対応する親エリアコードを検索

        Args:
            child_code: 検索する子コード
            area_codes_data: エリアコード階層データ

        Returns:
            対応する親エリアコード、見つからない場合はNone
        """
        for office_data in area_codes_data.values():
            for area_code, children_codes in office_data.items():
                if child_code in children_codes:
                    return area_code
        return None

    @staticmethod
    def resolve_coordinate_to_area_code(
        code: str, volcano_coordinates: Dict, debug: bool = False
    ) -> Optional[str]:
        """
        3桁エリアコードの座標情報からclass10エリアコードに解決

        Args:
            code: 3桁エリアコード
            volcano_coordinates: 火山座標データ
            debug: デバッグモード

        Returns:
            解決されたclass10エリアコード、失敗時はNone
        """
        if len(code) != 3 or code not in volcano_coordinates:
            return None

        try:
            coord_list = volcano_coordinates[code]
            if not coord_list:
                return None

            # 最初の座標を使用
            coord_str = coord_list[0]
            processor = VolcanoCoordinateProcessor()
            lat, lon = processor.parse_volcano_coordinates(coord_str)

            if lat is None or lon is None:
                if debug:
                    print(f"Failed to parse coordinates for {code}: {coord_str}")
                return None

            if debug:
                print(f"Resolving coordinates for {code}: lat={lat}, lon={lon}")

            # LocationClientで座標解決
            client = LocationClient(debug=debug)
            try:
                result = client.get_location_data(lat, lon)
                if result and isinstance(result, tuple) and len(result) >= 1:
                    location_response = result[0]
                    if hasattr(location_response, 'area_code'):
                        resolved_code = str(location_response.area_code).zfill(6)
                        if debug:
                            print(f"Resolved {code} -> {resolved_code}")
                        return resolved_code
            finally:
                client.close()

        except Exception as e:
            if debug:
                print(f"Error resolving coordinates for {code}: {e}")
            return None

        return None
