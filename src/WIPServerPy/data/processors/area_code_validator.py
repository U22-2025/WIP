"""Area code validation utilities."""

from typing import Dict, Optional


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
