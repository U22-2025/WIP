"""
拡張フィールド管理クラス

拡張フィールドのデータを管理し、ビット列との相互変換を提供します。

新しいプロパティアクセス方式:
    # プロパティとして直接アクセス (推奨)
    ex_field.alert = ["津波警報"]
    alerts = ex_field.alert

非推奨のget/setメソッド:
    # 非推奨: 将来のバージョンで削除予定
    ex_field.set('alert', ["津波警報"])
    alerts = ex_field.get('alert')

注意:
    get()/set()メソッドを使用するとDeprecationWarningが発生します。
    新しいプロパティアクセス方式に移行してください。
"""
from typing import Optional, Dict, Any, List, Union, Callable, Tuple
from .exceptions import BitFieldError
from .bit_utils import extract_bits

import csv
import io
import warnings

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

    @classmethod
    def update_mapping(cls, entries: List[Dict[str, int]]) -> None:
        """YAML定義からマッピングを更新"""
        cls.FIELD_MAPPING_INT = {e['id']: e['name'] for e in entries}
        cls.FIELD_MAPPING_STR = {e['name']: e['id'] for e in entries}
    
    def __init__(self, data: Optional[Dict[str, Any]] = None) -> None:
        """
        初期化
        
        Args:
            data: 初期データの辞書
        """
        self._data: Dict[str, Any] = {}
        self._observers: List[Callable[[], None]] = []
        self.flag: int = 1  # 拡張フィールドフラグ（1=有効、0=無効）
        
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
        warnings.warn(
            "set()メソッドは非推奨です。プロパティ代入を使用してください",
            DeprecationWarning,
            stacklevel=2
        )
        # キーの検証
        if key not in self.FIELD_MAPPING_STR:
            raise ValueError(f"不正なキー: '{key}'")
        
        # 値の検証と正規化
        validated_value = self._validate_value(key, value)
        
        # 値を設定
        self._data[key] = validated_value
        
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
        warnings.warn(
            "get()メソッドは非推奨です。プロパティアクセスを使用してください",
            DeprecationWarning,
            stacklevel=2
        )
        return self._data.get(key, default)
    
    def update(self, data: Dict[str, Any]) -> None:
        """
        複数のフィールドを一度に更新
        
        Args:
            data: 更新するデータの辞書
        """
        for key, value in data.items():
            if hasattr(self.__class__, key):
                setattr(self, key, value)
            else:
                self._set_field(key, value)
    
    def clear(self) -> None:
        """全てのフィールドをクリア"""
        self._data.clear()
        self._notify_observers()
    
    def remove(self, key: str) -> None:
        """
        指定されたキーのフィールドを削除
        
        Args:
            key: 削除するキー
        """
        if key in self._data:
            del self._data[key]
            self._notify_observers()
    
    def is_empty(self) -> bool:
        """
        拡張フィールドが空かどうかを確認
        
        Returns:
            拡張フィールドが空の場合True
        """
        return len(self._data) == 0
    
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

    def _get_field(self, key: str, default: Any = None) -> Any:
        """内部データから値を取得"""
        return self._data.get(key, default)

    def _set_field(self, key: str, value: Any) -> None:
        """検証後に値を設定し、オブザーバーへ通知"""
        validated_value = self._validate_value(key, value)
        self._data[key] = validated_value
        self._notify_observers()
    
    @property
    def alert(self) -> Optional[str]:
        return self._get_field('alert')

    @alert.setter
    def alert(self, value: Union[List[str], str]) -> None:
        self._set_field('alert', value)

    @property
    def disaster(self) -> Optional[str]:
        return self._get_field('disaster')

    @disaster.setter
    def disaster(self, value: Union[List[str], str]) -> None:
        self._set_field('disaster', value)

    @property
    def latitude(self) -> Union[float, None]:
        return self._get_field('latitude')

    @latitude.setter
    def latitude(self, value: float) -> None:
        self._set_field('latitude', value)

    @property
    def longitude(self) -> Union[float, None]:
        return self._get_field('longitude')

    @longitude.setter
    def longitude(self, value: float) -> None:
        self._set_field('longitude', value)

    @property
    def source(self) -> Optional[tuple[str, int]]:
        """sourceフィールドのゲッター
        Returns:
            tuple: (ip, port)形式のタプル
            None: 未設定の場合
        """
        value = self._get_field('source')
        if value is None:
            return None
        if isinstance(value, tuple):
            return value
        if isinstance(value, str) and ":" in value:
            ip, port = value.split(":")
            return (ip, int(port))
        raise ValueError(f"Invalid source format: {value}")

    @source.setter
    def source(self, value: Union[str, tuple[str, Union[str, int]]]) -> None:
        """sourceフィールドのセッター
        Args:
            value: 設定する値
                str: "ip:port"形式の文字列
                tuple: (ip, port)形式のタプル（portは文字列または数値）
        """
        if isinstance(value, str):
            if ":" not in value:
                raise ValueError("source文字列は'ip:port'形式である必要があります")
            ip, port_str = value.split(":")
            try:
                port = int(port_str)
            except ValueError:
                raise ValueError(f"無効なポート番号: {port_str}")
            value = (ip, port)
        
        if not isinstance(value, tuple) or len(value) != 2:
            raise ValueError("sourceは(ip, port)形式のタプルである必要があります")
        
        ip, port = value
        if not isinstance(ip, str) or not ip:
            raise ValueError("IPアドレスは空でない文字列である必要があります")
        
        try:
            port = int(port)
            if not (0 <= port <= 65535):
                raise ValueError("ポート番号は0-65535の範囲である必要があります")
        except ValueError:
            raise ValueError(f"無効なポート番号: {port}")
        
        self._set_field('source', (ip, port))

    def _validate_value(self, key: str, value: Any) -> Any:
        """
        値の検証と正規化
        
        Args:
            key: フィールドキー
            value: 検証する値
            
        Returns:
            正規化された値
            
        Raises:
            ValueError: 値が不正な場合
        """
        # alert/disasterフィールドの検証と結合
        if key in ['alert', 'disaster']:
            if isinstance(value, list):
                # リストの要素を結合
                processed_value = ExtendedField.to_csv_line(value)
                
            elif isinstance(value, str):
                processed_value = value.strip()
            else:
                raise ValueError(f"{key}は文字列または文字列のリストである必要があります")
            
            if not processed_value:
                raise ValueError(f"{key}は空文字列であってはなりません")
            return processed_value
        
        # 座標フィールドの検証
        elif key == 'latitude':
            if not isinstance(value, (int, float)):
                raise ValueError("緯度は数値である必要があります")
            if not (ExtendedFieldType.LATITUDE_MIN <= value <= ExtendedFieldType.LATITUDE_MAX):
                raise ValueError(f"緯度が範囲外です: {value}")
            return value
        
        elif key == 'longitude':
            if not isinstance(value, (int, float)):
                raise ValueError("経度は数値である必要があります")
            if not (ExtendedFieldType.LONGITUDE_MIN <= value <= ExtendedFieldType.LONGITUDE_MAX):
                raise ValueError(f"経度が範囲外です: {value}")
            return value
        
        # sourceフィールドの検証
        elif key == 'source':
            if isinstance(value, str):
                if ":" not in value:
                    raise ValueError("source文字列は'ip:port'形式である必要があります")
                ip, port_str = value.split(":")
                try:
                    port = int(port_str)
                except ValueError:
                    raise ValueError(f"無効なポート番号: {port_str}")
                value = (ip, port)
            
            if not isinstance(value, tuple) or len(value) != 2:
                raise ValueError("sourceは(ip, port)形式のタプルである必要があります")
            
            ip, port = value
            if not isinstance(ip, str) or not ip:
                raise ValueError("IPアドレスは空でない文字列である必要があります")
            
            try:
                port = int(port)
                if not (0 <= port <= 65535):
                    raise ValueError("ポート番号は0-65535の範囲である必要があります")
            except ValueError:
                raise ValueError(f"無効なポート番号: {port}")
            
            return (ip, port)
        
        # その他の未知のキーはそのまま返す
        return value

    # CSVとして安全にカンマ区切り文字列に変換
    @staticmethod
    def to_csv_line(value):
        output = io.StringIO()
        writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)
        writer.writerow([str(item).strip() for item in value if str(item).strip()])
        return output.getvalue().strip()  # .strip()で末尾の改行削除
    
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
                # _validate_valueで既に正規化されているため、直接valueを使用
                values_to_process = value
                
                if key == 'source':
                    # sourceフィールドは"ip:port"形式でシリアライズ
                    ip, port = values_to_process
                    value_str = f"{ip}:{port}"
                    value_bytes = value_str.encode('utf-8')
                elif isinstance(values_to_process, str):
                    value_bytes = values_to_process.encode('utf-8')
                elif key in ['latitude', 'longitude']:
                    # 座標値の変換
                    coord_value = float(values_to_process)
                    # 10^6倍して整数化
                    int_value = int(coord_value * ExtendedFieldType.COORDINATE_SCALE)
                    value_bytes = int_value.to_bytes(4, byteorder='little', signed=True)
                elif isinstance(values_to_process, (int, float)):
                    # その他の数値
                    if isinstance(values_to_process, float):
                        value_bytes = str(values_to_process).encode('utf-8')
                    else:
                        value_bytes = values_to_process.to_bytes((values_to_process.bit_length() + 7) // 8 or 1, byteorder='little')
                else:
                    raise BitFieldError(f"サポートされていない値の型: {type(values_to_process)}")
                
                # バイト数とビット長を計算
                bytes_needed = len(value_bytes)
                if bytes_needed > self.MAX_EXTENDED_LENGTH:
                    raise BitFieldError(f"値が大きすぎます: {bytes_needed} バイト")
                
                # ヘッダー構造（キーを上位、バイト長を下位）
                header = ((key_int & self.MAX_EXTENDED_KEY) << self.EXTENDED_HEADER_LENGTH) | (bytes_needed & self.MAX_EXTENDED_LENGTH)
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
    def _parse_header(cls, bitstr: int, pos: int, total_bits: int) -> Optional[Tuple[Optional[int], int, int]]:
        """ヘッダー情報を解析してキーとバイト長を取得"""
        if total_bits - pos < cls.EXTENDED_HEADER_TOTAL:
            return None

        header = extract_bits(bitstr, pos, cls.EXTENDED_HEADER_TOTAL)
        key = (header >> cls.EXTENDED_HEADER_LENGTH) & cls.MAX_EXTENDED_KEY
        bytes_length = header & cls.MAX_EXTENDED_LENGTH
        bits_length = bytes_length * 8

        if header == 0 or bytes_length == 0:
            return (None, bytes_length, bits_length)

        required_bits = cls.EXTENDED_HEADER_TOTAL + bits_length
        if pos + required_bits > total_bits:
            return None

        return key, bytes_length, bits_length

    @classmethod
    def _decode_value(cls, key: int, value_bits: int, bytes_length: int) -> Any:
        """値部分のビット列をデコード"""
        try:
            value_bytes = value_bits.to_bytes(bytes_length, byteorder='little')
            if key in ExtendedFieldType.STRING_LIST_FIELDS:
                return value_bytes.decode('utf-8').rstrip('\x00#')
            if key == ExtendedFieldType.SOURCE:
                value_str = value_bytes.decode('utf-8').rstrip('\x00#')
                if ':' in value_str:
                    ip, port_str = value_str.split(':')
                    try:
                        return (ip, int(port_str))
                    except ValueError:
                        return value_str
                return value_str
            if key in ExtendedFieldType.COORDINATE_FIELDS:
                if bytes_length == 4:
                    int_value = int.from_bytes(value_bytes, byteorder='little', signed=True)
                    return int_value / ExtendedFieldType.COORDINATE_SCALE
                try:
                    decoded_str = value_bytes.decode('utf-8').rstrip('\x00#')
                    return float(decoded_str)
                except (UnicodeDecodeError, ValueError):
                    return int.from_bytes(value_bytes, byteorder='little')
        except UnicodeDecodeError:
            return value_bits

        return value_bits
    
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
                parsed = cls._parse_header(bitstr, current_pos, total_bits)
                if not parsed:
                    break

                key, bytes_length, bits_length = parsed
                if key is None:
                    current_pos += cls.EXTENDED_HEADER_TOTAL
                    continue

                value_bits = extract_bits(bitstr, current_pos + cls.EXTENDED_HEADER_TOTAL, bits_length)
                value = cls._decode_value(key, value_bits, bytes_length)

                if field_key := cls.FIELD_MAPPING_INT.get(key):
                    result.append({field_key: value})

                current_pos += cls.EXTENDED_HEADER_TOTAL + bits_length
            
            # 結果を辞書に変換
            converted_dict = cls._extended_field_to_dict(result)
            instance._data = converted_dict
            
            # 拡張フィールドが空の場合はフラグを0に設定
            if instance.is_empty():
                instance.flag = 0
            
            return instance
            
        except Exception as e:
            raise BitFieldError(f"拡張フィールドの解析中にエラーが発生しました: {e}")
    
    @classmethod
    def _extended_field_to_dict(cls, extended_field: List[Dict[str, Any]]) -> Dict[str, Union[str, int]]:
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
            result: Dict[str, Union[str, int]] = {}
            
            for item in extended_field:
                if not item or len(item) != 1:
                    raise BitFieldError("不正な拡張フィールド形式")
                
                key = next(iter(item))
                value = item[key]
                
                # alert/disasterは単一の文字列として結合して扱う
                if key in ["alert", "disaster"]:
                    if not isinstance(value, (str, int)):
                        raise BitFieldError(f"不正な値の型: {type(value)}")
                    stripped_value = str(value).strip()
                    if not stripped_value: # 空文字列は追加しない
                        continue # 空文字列の場合はスキップして次の要素へ
                    
                    if key in result:
                        # 既存の値があれば結合
                        result[key] = f"{result[key]}, {stripped_value}"
                    else:
                        # なければそのまま設定
                        result[key] = stripped_value
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
