"""
拡張フィールドの独立クラス
"""
from typing import Optional, Dict, Any, List, Union, Callable
from .exceptions import BitFieldError
from .bit_utils import extract_bits


class ExtendedFieldType:
    """拡張フィールドタイプの定数定義"""
    ALERT = 1
    DISASTER = 2
    LATITUDE = 33
    LONGITUDE = 34
    SOURCE = 40
    
    # フィールドタイプ分類
    STRING_LIST_FIELDS = {ALERT, DISASTER}
    COORDINATE_FIELDS = {LATITUDE, LONGITUDE}
    STRING_FIELDS = {SOURCE}
    
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


class ExtendedField:
    """
    拡張フィールドの独立したクラス
    拡張フィールドのデータを管理し、ビット列との相互変換を提供します
    """
    
    # 拡張フィールドのヘッダー
    EXTENDED_HEADER_LENGTH = 10  # バイト長フィールドのビット数
    EXTENDED_HEADER_KEY = 6      # キーフィールドのビット数
    EXTENDED_HEADER_TOTAL = EXTENDED_HEADER_LENGTH + EXTENDED_HEADER_KEY  # 合計ビット数
    
    # 拡張フィールドの最大値
    MAX_EXTENDED_LENGTH = (1 << EXTENDED_HEADER_LENGTH) - 1  # 最大バイト長
    MAX_EXTENDED_KEY = (1 << EXTENDED_HEADER_KEY) - 1       # 最大キー値
    
    # 拡張フィールドのキーと値のマッピング
    FIELD_MAPPING_INT = {
        ExtendedFieldType.ALERT: 'alert',
        ExtendedFieldType.DISASTER: 'disaster',
        ExtendedFieldType.LATITUDE: 'latitude',
        ExtendedFieldType.LONGITUDE: 'longitude',
        ExtendedFieldType.SOURCE: 'source',
    }
    
    FIELD_MAPPING_STR = {
        'alert': ExtendedFieldType.ALERT,
        'disaster': ExtendedFieldType.DISASTER,
        'latitude': ExtendedFieldType.LATITUDE,
        'longitude': ExtendedFieldType.LONGITUDE,
        'source': ExtendedFieldType.SOURCE,
    }
    
    def __init__(self, data: Optional[Dict[str, Any]] = None) -> None:
        """
        初期化
        
        Args:
            data: 初期データの辞書
        """
        self._data: Dict[str, Any] = {}
        self._observers: List[Callable[[], None]] = []
        
        # 初期データを設定
        if data:
            self.update(data)
    
    def set(self, key: str, value: Any) -> None:
        """
        フィールド値を設定（検証付き）
        
        Args:
            key: フィールドキー
            value: 設定する値
            
        Raises:
            ValueError: 不正なキーまたは値の場合
        """
        # キーの検証
        if key not in self.FIELD_MAPPING_STR:
            raise ValueError(f"不正なキー: '{key}'")
        
        # 値の検証
        self._validate_value(key, value)
        
        # 値を設定
        self._data[key] = value
        
        # 変更を通知
        self._notify_observers()
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        フィールド値を取得
        
        Args:
            key: フィールドキー
            default: デフォルト値
            
        Returns:
            フィールド値（存在しない場合はdefault）
        """
        return self._data.get(key, default)
    
    def update(self, data: Dict[str, Any]) -> None:
        """
        複数のフィールドを一度に更新
        
        Args:
            data: 更新するデータの辞書
        """
        for key, value in data.items():
            self.set(key, value)
    
    def clear(self) -> None:
        """全てのフィールドをクリア"""
        self._data.clear()
        self._notify_observers()
    
    def contains(self, key: str) -> bool:
        """
        キーの存在確認
        
        Args:
            key: 確認するキー
            
        Returns:
            キーが存在する場合True
        """
        return key in self._data
    
    def keys(self) -> List[str]:
        """全てのキーを取得"""
        return list(self._data.keys())
    
    def to_dict(self) -> Dict[str, Any]:
        """
        辞書形式で取得（読み取り専用）
        
        Returns:
            フィールドデータのコピー
        """
        return self._data.copy()
    
    def add_observer(self, callback: Callable[[], None]) -> None:
        """
        変更通知のオブザーバーを追加
        
        Args:
            callback: 変更時に呼び出される関数
        """
        self._observers.append(callback)
    
    def remove_observer(self, callback: Callable[[], None]) -> None:
        """
        オブザーバーを削除
        
        Args:
            callback: 削除する関数
        """
        if callback in self._observers:
            self._observers.remove(callback)
    
    def _notify_observers(self) -> None:
        """オブザーバーに変更を通知"""
        for callback in self._observers:
            try:
                callback()
            except Exception:
                # オブザーバーのエラーは無視
                pass
    
    def _validate_value(self, key: str, value: Any) -> None:
        """
        値の検証
        
        Args:
            key: フィールドキー
            value: 検証する値
            
        Raises:
            ValueError: 値が不正な場合
        """
        # alert/disasterフィールドの検証
        if key in ['alert', 'disaster']:
            if isinstance(value, list):
                for item in value:
                    if not isinstance(item, str):
                        raise ValueError(f"{key}の要素は文字列である必要があります")
            elif not isinstance(value, str):
                raise ValueError(f"{key}は文字列またはリストである必要があります")
        
        # 座標フィールドの検証
        elif key == 'latitude':
            if not isinstance(value, (int, float)):
                raise ValueError("緯度は数値である必要があります")
            if not (ExtendedFieldType.LATITUDE_MIN <= value <= ExtendedFieldType.LATITUDE_MAX):
                raise ValueError(f"緯度が範囲外です: {value}")
        
        elif key == 'longitude':
            if not isinstance(value, (int, float)):
                raise ValueError("経度は数値である必要があります")
            if not (ExtendedFieldType.LONGITUDE_MIN <= value <= ExtendedFieldType.LONGITUDE_MAX):
                raise ValueError(f"経度が範囲外です: {value}")
        
        # sourceフィールドの検証
        elif key == 'source':
            if not isinstance(value, str):
                raise ValueError("sourceは文字列である必要があります")
    
    def to_bits(self) -> int:
        """
        拡張フィールドをビット列に変換
        
        Returns:
            ビット列表現
            
        Raises:
            BitFieldError: 変換中にエラーが発生した場合
        """
        result_bits = 0
        current_pos = 0
        
        for key, value in self._data.items():
            # キーを整数に変換
            key_int = self.FIELD_MAPPING_STR.get(key)
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
                        # 座標値の変換
                        coord_value = float(single_value)
                        # 10^6倍して整数化
                        int_value = int(coord_value * ExtendedFieldType.COORDINATE_SCALE)
                        value_bytes = int_value.to_bytes(4, byteorder='little', signed=True)
                    elif isinstance(single_value, (int, float)):
                        # その他の数値
                        if isinstance(single_value, float):
                            value_bytes = str(single_value).encode('utf-8')
                        else:
                            value_bytes = single_value.to_bytes((single_value.bit_length() + 7) // 8 or 1, byteorder='little')
                    else:
                        raise BitFieldError(f"サポートされていない値の型: {type(single_value)}")
                    
                    # バイト数とビット長を計算
                    bytes_needed = len(value_bytes)
                    if bytes_needed > self.MAX_EXTENDED_LENGTH:
                        raise BitFieldError(f"値が大きすぎます: {bytes_needed} バイト")
                    
                    # ヘッダー構造（バイト長を上位、キーを下位）
                    header = ((bytes_needed & self.MAX_EXTENDED_LENGTH) << self.EXTENDED_HEADER_KEY) | (key_int & self.MAX_EXTENDED_KEY)
                    value_bits = int.from_bytes(value_bytes, byteorder='little')
                    
                    # 値を上位ビットに、ヘッダーを下位ビットに配置
                    value_bit_width = bytes_needed * 8
                    record_bits = (value_bits << self.EXTENDED_HEADER_TOTAL) | header
                    result_bits |= (record_bits << current_pos)
                    
                    current_pos += self.EXTENDED_HEADER_TOTAL + (bytes_needed * 8)
                
            except Exception as e:
                raise BitFieldError(f"キー '{key}' の処理中にエラー: {e}")
        
        return result_bits
    
    @classmethod
    def from_bits(cls, bitstr: int, total_bits: Optional[int] = None) -> 'ExtendedField':
        """
        ビット列から拡張フィールドを生成
        
        Args:
            bitstr: 解析対象のビット列
            total_bits: ビット列全体の長さ
            
        Returns:
            ExtendedFieldインスタンス
            
        Raises:
            BitFieldError: 解析中にエラーが発生した場合
        """
        try:
            instance = cls()
            result = []
            current_pos = 0
            
            # ビット長を計算（最低でもヘッダー分必要）
            total_bits = total_bits if total_bits is not None else bitstr.bit_length()
            
            while current_pos < total_bits:
                if total_bits - current_pos < cls.EXTENDED_HEADER_TOTAL:
                    break
                
                header = extract_bits(bitstr, current_pos, cls.EXTENDED_HEADER_TOTAL)
                # ビット配置を統一（バイト長を上位、キーを下位）
                bytes_length = (header >> cls.EXTENDED_HEADER_KEY) & cls.MAX_EXTENDED_LENGTH
                key = header & cls.MAX_EXTENDED_KEY
                bits_length = bytes_length * 8
                
                # ヘッダーが0の場合（無効なレコード）はスキップ
                if header == 0 or bytes_length == 0:
                    current_pos += cls.EXTENDED_HEADER_TOTAL
                    continue
                
                required_bits = cls.EXTENDED_HEADER_TOTAL + bits_length
                if current_pos + required_bits > total_bits:
                    break
                
                value_bits = extract_bits(bitstr, current_pos + cls.EXTENDED_HEADER_TOTAL, bits_length)
                
                try:
                    value_bytes = value_bits.to_bytes(bytes_length, byteorder='little')
                    if key in ExtendedFieldType.STRING_LIST_FIELDS or key == ExtendedFieldType.SOURCE:
                        # 文字列の末尾の余分な文字を削除
                        value = value_bytes.decode('utf-8').rstrip('\x00#')
                    elif key in ExtendedFieldType.COORDINATE_FIELDS:
                        # 4バイト符号付き整数として復元し、10^6で割って浮動小数点数に戻す
                        if bytes_length == 4:
                            int_value = int.from_bytes(value_bytes, byteorder='little', signed=True)
                            value = int_value / ExtendedFieldType.COORDINATE_SCALE
                        else:
                            # 互換性のため、従来の文字列形式もサポート
                            try:
                                decoded_str = value_bytes.decode('utf-8').rstrip('\x00#')
                                value = float(decoded_str)
                            except (UnicodeDecodeError, ValueError):
                                value = int.from_bytes(value_bytes, byteorder='little')
                    else:
                        value = value_bits
                except UnicodeDecodeError:
                    value = value_bits
                
                if field_key := cls.FIELD_MAPPING_INT.get(key):
                    result.append({field_key: value})
                
                current_pos += required_bits
            
            # 結果を辞書に変換
            converted_dict = cls._extended_field_to_dict(result)
            instance._data = converted_dict
            
            return instance
            
        except Exception as e:
            raise BitFieldError(f"拡張フィールドの解析中にエラーが発生しました: {e}")
    
    @classmethod
    def _extended_field_to_dict(cls, extended_field: List[Dict[str, Any]]) -> Dict[str, Union[str, int, List[str]]]:
        """
        拡張フィールドを辞書に変換
        
        Args:
            extended_field: 拡張フィールドのリスト
            
        Returns:
            変換された辞書
            
        Raises:
            BitFieldError: 不正なフォーマットの場合
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
    
    def __repr__(self) -> str:
        """デバッグ用の文字列表現"""
        return f"ExtendedField({self._data})"
    
    def __eq__(self, other: Any) -> bool:
        """等価性の判定"""
        if isinstance(other, ExtendedField):
            return self._data == other._data
        elif isinstance(other, dict):
            return self._data == other
        return False
