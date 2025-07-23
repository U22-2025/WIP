"""Volcano coordinate processing utilities."""

import re
from typing import Optional, Tuple


class VolcanoCoordinateProcessor:
    """
    火山座標処理クラス

    役割:
    - 火山座標文字列の解析
    - 緯度経度への変換
    - LocationClientとの連携
    """

    @staticmethod
    def parse_volcano_coordinates(
        coord_str: str,
    ) -> Tuple[Optional[float], Optional[float]]:
        """
        火山座標文字列を緯度経度に変換

        Args:
            coord_str: 座標文字列 (例: "+2938.30+12942.83+796/")

        Returns:
            (緯度, 経度)のタプル、解析失敗時は(None, None)
        """
        try:
            # 座標文字列の形式: "+DDMM.MM+DDDMM.MM+標高/"
            # 最後の「/」を除去
            coord_str = coord_str.rstrip("/")

            # 正規表現で緯度、経度、標高を抽出
            pattern = r"([+-]\d{4}\.\d{2})([+-]\d{5}\.\d{2})([+-]\d+)"
            match = re.match(pattern, coord_str)

            if not match:
                print(f"座標文字列の形式が不正です: {coord_str}")
                return None, None

            lat_str, lon_str, alt_str = match.groups()

            # 緯度の変換 (DDMM.MM -> DD.DDDD)
            lat_sign = 1 if lat_str[0] == "+" else -1
            lat_abs = lat_str[1:]
            lat_degrees = int(lat_abs[:2])
            lat_minutes = float(lat_abs[2:])
            latitude = lat_sign * (lat_degrees + lat_minutes / 60.0)
            latitude = round(latitude, 6)

            # 経度の変換 (DDDMM.MM -> DDD.DDDD)
            lon_sign = 1 if lon_str[0] == "+" else -1
            lon_abs = lon_str[1:]
            lon_degrees = int(lon_abs[:3])
            lon_minutes = float(lon_abs[3:])
            longitude = lon_sign * (lon_degrees + lon_minutes / 60.0)
            longitude = round(longitude, 6)

            return latitude, longitude

        except Exception as e:
            print(f"座標解析エラー: {e}, 座標文字列: {coord_str}")
            return None, None
