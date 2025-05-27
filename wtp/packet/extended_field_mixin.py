"""
拡張フィールド処理のミックスインクラス
"""
from typing import Optional, Dict, Any, List, Union
from .exceptions import BitFieldError
from .bit_utils import extract_bits, extract_rest_bits


class ExtendedFieldType:
    """拡張フィールドタイプの定数定義"""
    ALERT = 1
    DISASTER = 2
    LATITUDE = 33
    LONGITUDE = 34
    SOURCE_IP = 40
    
    # フィールドタイプ分類
    STRING_LIST_FIELDS = {ALERT, DISASTER}
    COORDINATE_FIELDS = {LATITUDE, LONGITUDE}
    STRING_FIELDS = {SOURCE_IP}
    
    # 座標値の範囲制限
    LATITUDE_MIN = -90.0
    LATITUDE_MAX = 90.0
    LONGITUDE_MIN = -180.0
    LONGITUDE_MAX = 180.0
    
    # 座標精度（10^6倍で整数化）
    COORDINATE_SCALE = 1_000_000
    
    # 32ビット符号付き整数の範囲
    INT32_MIN = -2_147_483_648
    INT32_MAX = 2_147_483_647


class ExtendedFieldMixin:
    """
    拡張フィールド処理のミックスインクラス
    拡張フィールドの構造を定義し、ビット操作のユーティリティを提供します
    """

    # 拡張フィールドのヘッダー
    EXTENDED_HEADER_LENGTH = 10  # バイト長フィールドのビット数
    EXTENDED_HEADER_KEY = 6      # キーフィールドのビット数
    EXTENDED_HEADER_TOTAL = EXTENDED_HEADER_LENGTH + EXTENDED_HEADER_KEY  # 合計ビット数

    # 拡張フィールドの最大値
    MAX_EXTENDED_LENGTH = (1 << EXTENDED_HEADER_LENGTH) - 1  # 最大バイト長
    MAX_EXTENDED_KEY = (1 << EXTENDED_HEADER_KEY) - 1       # 最大キー値

    # 拡張フィールドのキーと値のマッピング
    EXTENDED_FIELD_MAPPING_INT = {
        ExtendedFieldType.ALERT: 'alert',
        ExtendedFieldType.DISASTER: 'disaster',
        ExtendedFieldType.LATITUDE: 'latitude',
        ExtendedFieldType.LONGITUDE: 'longitude',
        ExtendedFieldType.SOURCE_IP: 'source_ip',
    }

    EXTENDED_FIELD_MAPPING_STR = {
        'alert': ExtendedFieldType.ALERT,
        'disaster': ExtendedFieldType.DISASTER,
        'latitude': ExtendedFieldType.LATITUDE,
        'longitude': ExtendedFieldType.LONGITUDE,
        'source_ip': ExtendedFieldType.SOURCE_IP,
    }

    def fetch_ex_field(self, bitstr: int, total_bits: Optional[int] = None) -> None:
        """
        拡張フィールド (ex_field) のデータを解析します。
        
        ビット列は次のフォーマットとなっています：
        ・先頭6ビット：キー
        ・次の10ビット：バイト数を示す
        ・その後 (バイト数 * 8) ビット分：値
        これらのレコードが連続していると想定し、全レコードを解析します。
        
        Args:
            bitstr: 解析対象のビット列（整数として与えられる）
            total_bits: ビット列全体の長さ。送信ビット列が固定長で先頭の0が有意な場合、この値を指定。
                      Noneの場合はbitstr.bit_length()を利用。
                      
        Raises:
            BitFieldError: ビット列の解析中にエラーが発生した場合
        """
        try:
            result = []
            current_pos = 0
            
            # ビット長を計算（最低でもヘッダー分必要）
            total_bits = total_bits if total_bits is not None else bitstr.bit_length()
            
            while current_pos < total_bits:
                if total_bits - current_pos < self.EXTENDED_HEADER_TOTAL:
                    break
                    
                header = extract_bits(bitstr, current_pos, self.EXTENDED_HEADER_TOTAL)
                # 修正：ビット配置を統一（バイト長を上位、キーを下位）
                bytes_length = (header >> self.EXTENDED_HEADER_KEY) & self.MAX_EXTENDED_LENGTH
                key = header & self.MAX_EXTENDED_KEY
                bits_length = bytes_length * 8
                
                # ヘッダーが0の場合（無効なレコード）はスキップ
                if header == 0 or bytes_length == 0:
                    current_pos += self.EXTENDED_HEADER_TOTAL
                    continue
                
                required_bits = self.EXTENDED_HEADER_TOTAL + bits_length
                if current_pos + required_bits > total_bits:
                    break
                
                value_bits = extract_bits(bitstr, current_pos + self.EXTENDED_HEADER_TOTAL, bits_length)
                
                try:
                    value_bytes = value_bits.to_bytes(bytes_length, byteorder='big')
                    if key in ExtendedFieldType.STRING_LIST_FIELDS or key == ExtendedFieldType.SOURCE_IP:
                        # 文字列の末尾の余分な文字を削除
                        value = value_bytes.decode('utf-8').rstrip('\x00#')
                    elif key in ExtendedFieldType.COORDINATE_FIELDS:
                        # 修正：4バイト符号付き整数として復元し、10^6で割って浮動小数点数に戻す
                        if bytes_length == 4:
                            int_value = int.from_bytes(value_bytes, byteorder='big', signed=True)
                            value = int_value / ExtendedFieldType.COORDINATE_SCALE
                        else:
                            # 互換性のため、従来の文字列形式もサポート
                            try:
                                decoded_str = value_bytes.decode('utf-8').rstrip('\x00#')
                                value = float(decoded_str)
                            except (UnicodeDecodeError, ValueError):
                                value = int.from_bytes(value_bytes, byteorder='big')
                    else:
                        value = value_bits
                except UnicodeDecodeError:
                    value = value_bits
                
                if field_key := self._get_extended_field_key(key):
                    result.append({field_key: value})
                
                current_pos += required_bits
            
            self.ex_field = self._extended_field_to_dict(result)
            
        except Exception as e:
            raise BitFieldError(f"拡張フィールドの解析中にエラーが発生しました: {e}")

    def _dict_to_ex_field_bits(self, ex_field_dict: Dict[str, Any]) -> int:
        """
        ex_field辞書をビット列に変換する
        
        Args:
            ex_field_dict: 変換する辞書
            
        Returns:
            ビット列表現
            
        Raises:
            BitFieldError: キーが不正、または値の型がサポートされていない場合
        """
        result_bits = 0
        current_pos = 0
        
        for key, value in ex_field_dict.items():
            # キーを整数に変換
            key_int = (self._get_extended_field_key_from_str(key) if isinstance(key, str) else key)
            if key_int is None:
                raise BitFieldError(f"不正なキー: '{key}'")
                
            try:
                # 値をリストに正規化（リストでない場合は単一要素のリストにする）
                if isinstance(value, list):
                    values_to_process = value
                else:
                    values_to_process = [value]
                
                # 各値を個別のレコードとして処理
                for single_value in values_to_process:
                    if isinstance(single_value, str):
                        value_bytes = single_value.encode('utf-8')
                    elif key in ['latitude', 'longitude']:
                        # 座標値の範囲チェックと変換
                        coord_value = float(single_value)
                        
                        # 範囲チェック
                        if key == 'latitude':
                            if not (ExtendedFieldType.LATITUDE_MIN <= coord_value <= ExtendedFieldType.LATITUDE_MAX):
                                raise BitFieldError(f"緯度が範囲外です: {coord_value} (範囲: {ExtendedFieldType.LATITUDE_MIN}～{ExtendedFieldType.LATITUDE_MAX})")
                        elif key == 'longitude':
                            if not (ExtendedFieldType.LONGITUDE_MIN <= coord_value <= ExtendedFieldType.LONGITUDE_MAX):
                                raise BitFieldError(f"経度が範囲外です: {coord_value} (範囲: {ExtendedFieldType.LONGITUDE_MIN}～{ExtendedFieldType.LONGITUDE_MAX})")
                        
                        # 10^6倍して整数化
                        int_value = int(coord_value * ExtendedFieldType.COORDINATE_SCALE)
                        
                        # 32ビット符号付き整数の範囲チェック
                        if not (ExtendedFieldType.INT32_MIN <= int_value <= ExtendedFieldType.INT32_MAX):
                            raise BitFieldError(f"座標値が32ビット整数範囲を超えています: {int_value}")
                        
                        value_bytes = int_value.to_bytes(4, byteorder='big', signed=True)
                    elif isinstance(single_value, (int, float)):
                        # その他の数値
                        if isinstance(single_value, float):
                            # 浮動小数点数を文字列として保存（座標以外）
                            value_bytes = str(single_value).encode('utf-8')
                        else:
                            value_bytes = single_value.to_bytes((single_value.bit_length() + 7) // 8 or 1, byteorder='big')
                    else:
                        raise BitFieldError(f"サポートされていない値の型: {type(single_value)}")

                    # バイト数とビット長を計算
                    bytes_needed = len(value_bytes)
                    if bytes_needed > self.MAX_EXTENDED_LENGTH:
                        raise BitFieldError(f"値が大きすぎます: {bytes_needed} バイト")
                        
                    # 修正：ヘッダー構造を統一（バイト長を上位、キーを下位）
                    header = ((bytes_needed & self.MAX_EXTENDED_LENGTH) << self.EXTENDED_HEADER_KEY) | (key_int & self.MAX_EXTENDED_KEY)
                    value_bits = int.from_bytes(value_bytes, byteorder='big')
                    
                    # 値を上位ビットに、ヘッダーを下位ビットに配置
                    # 値のビット数を正確に指定（bytes_needed * 8ビット）
                    value_bit_width = bytes_needed * 8
                    record_bits = (value_bits << self.EXTENDED_HEADER_TOTAL) | header
                    result_bits |= (record_bits << current_pos)
                    
                    current_pos += self.EXTENDED_HEADER_TOTAL + (bytes_needed * 8)
                
            except Exception as e:
                raise BitFieldError(f"キー '{key}' の処理中にエラー: {e}")
        
        return result_bits

    def _extended_field_to_dict(self, extended_field: List[Dict[str, Any]]) -> Dict[str, Union[str, int, List[str]]]:
        """
        拡張フィールドを辞書に変換する
        
        Args:
            extended_field: 拡張フィールドのリスト。各要素は1つのキーと値のペアを持つ辞書。
            
        Returns:
            変換された辞書。alert/disasterは配列、その他は単一の値となる。
            
        Raises:
            BitFieldError: 不正なフォーマットの拡張フィールドを検出した場合
        """
        try:
            result: Dict[str, Union[str, int, List[str]]] = {}
            
            for item in extended_field:
                if not item or len(item) != 1:
                    raise BitFieldError("不正な拡張フィールド形式")
                    
                key = next(iter(item))
                value = item[key]
                
                # alert/disasterは配列として扱う
                if key in ["alert", "disaster"]:
                    if not isinstance(value, (str, int)):
                        raise BitFieldError(f"不正な値の型: {type(value)}")
                    # 空文字列は追加しない
                    if str(value).strip():
                        result.setdefault(key, []).append(str(value))
                else:
                    result[key] = value
                    
            return result
            
        except Exception as e:
            raise BitFieldError(f"拡張フィールドの辞書変換中にエラー: {e}")
        
    def _get_extended_field_key(self, key: int) -> Optional[str]:
        """
        拡張フィールドのキーを文字列に変換する
        """
        return self.EXTENDED_FIELD_MAPPING_INT.get(key, None)
    
    def _get_extended_field_key_from_str(self, key: str) -> Optional[int]:
        """
        拡張フィールドのキーを整数に変換する
        """
        return self.EXTENDED_FIELD_MAPPING_STR.get(key, None)
