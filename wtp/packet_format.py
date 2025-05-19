"""
パケットフォーマット処理クラス
このモジュールは、特定のバイナリパケットフォーマットの処理を行うクラスを提供します。
"""
from typing import Optional, Union, Dict, Any
import struct


class BitFieldError(Exception):
    """ビットフィールド操作に関連するエラー"""
    pass


class Format:
    """
    パケットフォーマットの基底クラス
    共通ヘッダー部分の構造を定義し、ビット操作のユーティリティを提供します
    
    ビットフィールド構造:
    - version:          1-4bit   (4ビット)
    - packet_ID:        5-16bit  (12ビット)
    - type:             17-19bit (3ビット)
    - weather_flag:     20bit    (1ビット)
    - temperature_flag: 21bit    (1ビット)
    - pops_flag:        22bit    (1ビット)
    - alert_flag:       23bit    (1ビット)
    - disaster_flag:    24bit    (1ビット)
    - ex_flag:          25bit    (1ビット)
    - day:              26-28bit (3ビット)
    - reserved:         29-32bit (4ビット)
    - timestamp:        33-96bit (64ビット)
    - area_code:        97-116bit (20ビット)
    - checksum:         117-128bit (12ビット)
    """
    
    # ビットフィールド定義 (位置, 長さ)
    _BIT_FIELDS = {
        'version': (0, 4),
        'packet_ID': (4, 12),
        'type': (16, 3),
        'weather_flag': (19, 1),
        'temperature_flag': (20, 1),
        'pops_flag': (21, 1),
        'alert_flag': (22, 1),
        'disaster_flag': (23, 1),
        'ex_flag': (24, 1),
        'day': (25, 3),
        'reserved': (28, 4),
        'timestamp': (32, 64),
        'area_code': (96, 20),
        'checksum': (116, 12),
    }
    
    # フィールドの有効範囲
    _FIELD_RANGES = {
        'version': (0, (1 << 4) - 1),
        'packet_ID': (0, (1 << 12) - 1),
        'type': (0, (1 << 3) - 1),
        'weather_flag': (0, 1),
        'temperature_flag': (0, 1),
        'pops_flag': (0, 1),
        'alert_flag': (0, 1),
        'disaster_flag': (0, 1),
        'ex_flag': (0, 1),
        'day': (0, (1 << 3) - 1),
        'reserved': (0, (1 << 4) - 1),
        'timestamp': (0, (1 << 64) - 1),
        'area_code': (0, (1 << 20) - 1),
        'checksum': (0, (1 << 12) - 1),
    }

    def __init__(self, **kwargs):
        """
        共通フィールドの初期化
        
        Args:
            **kwargs: 各フィールドの初期値または'bitstr'からの変換
        """
        # フィールドの初期化
        self.version = 0
        self.packet_ID = 0
        self.type = 0
        self.weather_flag = 0
        self.temperature_flag = 0
        self.pops_flag = 0
        self.alert_flag = 0
        self.disaster_flag = 0
        self.ex_flag = 0
        self.day = 0
        self.reserved = 0
        self.timestamp = 0
        self.area_code = 0
        self.checksum = 0
        
        # 'bitstr'が提供された場合はそれを解析
        if 'bitstr' in kwargs:
            self.from_bits(kwargs['bitstr'])
            # bitstrが処理されたので、それ以外のキーワード引数は無視
            return
            
        # 各フィールドをキーワード引数から設定
        for field, (_, _) in self._BIT_FIELDS.items():
            if field in kwargs:
                self._set_validated_field(field, kwargs[field])

    def _set_validated_field(self, field: str, value: int) -> None:
        """
        フィールド値を検証して設定する
        
        Args:
            field: 設定するフィールド名
            value: 設定する値
            
        Raises:
            BitFieldError: 値が有効範囲外の場合
        """
        if field in self._FIELD_RANGES:
            min_val, max_val = self._FIELD_RANGES[field]
            if not (min_val <= value <= max_val):
                raise BitFieldError(
                    f"フィールド '{field}' の値 {value} が有効範囲 {min_val}～{max_val} 外です"
                )
        setattr(self, field, value)

    @staticmethod
    def extract_bits(bitstr: int, start: int, length: int) -> int:
        """
        指定したビット列(bitstr)から、startビット目（0始まり）からlengthビット分を取り出す
        
        Args:
            bitstr: 元のビット列
            start: 開始位置（0始まり）
            length: 取り出すビット長
            
        Returns:
            取り出されたビット値
            
        Examples:
            >>> Format.extract_bits(0b110110, 1, 3)
            0b101
        """
        if length <= 0:
            raise BitFieldError(f"長さは正の整数である必要があります: {length}")
            
        mask = (1 << length) - 1
        return (bitstr >> start) & mask

    @staticmethod
    def extract_rest_bits(bitstr: int, start: int) -> int:
        """
        指定したビット列(bitstr)から、startビット目（0始まり）以降の全てのビットを取り出す
        
        Args:
            bitstr: 元のビット列
            start: 開始位置（0始まり）
            
        Returns:
            取り出されたビット値
            
        Examples:
            >>> Format.extract_rest_bits(0b110110, 2)
            0b110
        """
        return bitstr >> start

    def from_bits(self, bitstr: int) -> None:
        """
        ビット列から全フィールドを設定する
        
        Args:
            bitstr: 解析するビット列
        """
        try:
            for field, (start, length) in self._BIT_FIELDS.items():
                value = self.extract_bits(bitstr, start, length)
                setattr(self, field, value)
        except Exception as e:
            raise BitFieldError(f"ビット列の解析中にエラーが発生しました: {e}")

    def to_bits(self) -> int:
        """
        全フィールドをビット列に変換する
        
        Returns:
            ビット列表現
        """
        try:
            bitstr = 0
            for field, (start, length) in self._BIT_FIELDS.items():
                value = getattr(self, field)
                # 値の範囲を確認
                max_val = (1 << length) - 1
                if value > max_val:
                    raise BitFieldError(
                        f"フィールド '{field}' の値 {value} が最大値 {max_val} を超えています"
                    )
                bitstr |= (value & max_val) << start
            return bitstr
        except Exception as e:
            raise BitFieldError(f"ビット列への変換中にエラーが発生しました: {e}")
            
    def to_bytes(self) -> bytes:
        """
        ビット列をバイト列に変換する
        
        Returns:
            バイト列表現
        """
        bitstr = self.to_bits()
        # 必要なバイト数を計算（128ビット = 16バイト）
        num_bytes = (max(bit_pos + bit_len for bit_pos, bit_len in self._BIT_FIELDS.values()) + 7) // 8
        return bitstr.to_bytes(num_bytes, byteorder='big')
        
    @classmethod
    def from_bytes(cls, data: bytes) -> 'Format':
        """
        バイト列からインスタンスを生成する
        
        Args:
            data: バイト列
            
        Returns:
            生成されたインスタンス
        """
        bitstr = int.from_bytes(data, byteorder='big')
        return cls(bitstr=bitstr)
        
    def __str__(self) -> str:
        """人間が読める形式で表示する"""
        fields = []
        for field in self._BIT_FIELDS:
            value = getattr(self, field)
            # フラグの場合は真偽値で表示
            if field.endswith('_flag'):
                fields.append(f"{field}={'True' if value else 'False'}")
            else:
                fields.append(f"{field}={value}")
        return f"{self.__class__.__name__}({', '.join(fields)})"
        
    def __repr__(self) -> str:
        """デバッグ用の表示"""
        return self.__str__()
        
    def as_dict(self) -> Dict[str, Any]:
        """
        全フィールドを辞書形式で返す
        
        Returns:
            フィールド名と値の辞書
        """
        return {field: getattr(self, field) for field in self._BIT_FIELDS}


class Request(Format):
    """
    リクエストパケット
    基本フォーマットのみを使用します
    """
    pass


class Response(Format):
    """
    レスポンスパケット
    
    拡張フィールド:
    - weather_code:   129-144bit (16ビット)
    - temperature:    145-152bit (8ビット)
    - pops:           153-160bit (8ビット)
    - ex_field:       161-ビット
    """
    
    # 拡張ビットフィールド定義 (位置, 長さ)
    _EXTENDED_BIT_FIELDS = {
        'weather_code': (128, 16),
        'temperature': (144, 8),
        'pops': (152, 8),
    }
    
    # 拡張フィールドの有効範囲
    _EXTENDED_FIELD_RANGES = {
        'weather_code': (0, (1 << 16) - 1),
        'temperature': (0, (1 << 8) - 1),
        'pops': (0, (1 << 8) - 1),
    }

    def __init__(self, **kwargs):
        """
        レスポンスパケットの初期化
        
        Args:
            **kwargs: 各フィールドの初期値または'bitstr'からの変換
        """
        # 拡張フィールドの初期化
        self.weather_code = 0
        self.temperature = 0
        self.pops = 0
        self.ex_field = 0
        
        # 親クラスの初期化
        super().__init__(**kwargs)
        
        # bitstrが既に処理されていれば終了
        if 'bitstr' in kwargs:
            return
            
        # 拡張フィールドをキーワード引数から設定
        for field, (_, _) in self._EXTENDED_BIT_FIELDS.items():
            if field in kwargs:
                self._set_validated_extended_field(field, kwargs[field])
                
        # ex_fieldを設定
        if 'ex_field' in kwargs:
            self.ex_field = kwargs['ex_field']

    def _set_validated_extended_field(self, field: str, value: int) -> None:
        """
        拡張フィールド値を検証して設定する
        
        Args:
            field: 設定するフィールド名
            value: 設定する値
            
        Raises:
            BitFieldError: 値が有効範囲外の場合
        """
        if field in self._EXTENDED_FIELD_RANGES:
            min_val, max_val = self._EXTENDED_FIELD_RANGES[field]
            if not (min_val <= value <= max_val):
                raise BitFieldError(
                    f"フィールド '{field}' の値 {value} が有効範囲 {min_val}～{max_val} 外です"
                )
        setattr(self, field, value)

    def from_bits(self, bitstr: int) -> None:
        """
        ビット列から全フィールドを設定する
        
        Args:
            bitstr: 解析するビット列
        """
        # 親クラスのフィールドを設定
        super().from_bits(bitstr)
        
        try:
            # 拡張フィールドを設定
            for field, (start, length) in self._EXTENDED_BIT_FIELDS.items():
                value = self.extract_bits(bitstr, start, length)
                setattr(self, field, value)
                
            # ex_fieldを設定（残りのビット）
            ex_field_start = max(start + length for start, length in self._EXTENDED_BIT_FIELDS.items())
            self.ex_field = self.extract_rest_bits(bitstr, ex_field_start)
        except Exception as e:
            raise BitFieldError(f"拡張ビット列の解析中にエラーが発生しました: {e}")

    def to_bits(self) -> int:
        """
        全フィールドをビット列に変換する
        
        Returns:
            ビット列表現
        """
        try:
            # 親クラスのビット列を取得
            bitstr = super().to_bits()
            
            # 拡張フィールドを設定
            for field, (start, length) in self._EXTENDED_BIT_FIELDS.items():
                value = getattr(self, field)
                max_val = (1 << length) - 1
                if value > max_val:
                    raise BitFieldError(
                        f"フィールド '{field}' の値 {value} が最大値 {max_val} を超えています"
                    )
                bitstr |= (value & max_val) << start
                
            # ex_fieldを設定
            ex_field_start = max(start + length for start, length in self._EXTENDED_BIT_FIELDS.items())
            bitstr |= self.ex_field << ex_field_start
            
            return bitstr
        except Exception as e:
            raise BitFieldError(f"拡張ビット列への変換中にエラーが発生しました: {e}")
            
    def as_dict(self) -> Dict[str, Any]:
        """
        全フィールドを辞書形式で返す
        
        Returns:
            フィールド名と値の辞書
        """
        result = super().as_dict()
        # 拡張フィールドを追加
        for field in list(self._EXTENDED_BIT_FIELDS.keys()) + ['ex_field']:
            result[field] = getattr(self, field)
        return result


class ResolverRequest(Format):
    """
    リゾルバリクエストパケット
    
    拡張フィールド:
    - longitude: 129-192bit (64ビット)
    - latitude:  193-256bit (64ビット)
    """
    
    # 拡張ビットフィールド定義 (位置, 長さ)
    _EXTENDED_BIT_FIELDS = {
        'longitude': (128, 64),
        'latitude': (192, 64),
    }
    
    def __init__(self, **kwargs):
        """
        リゾルバリクエストパケットの初期化
        
        Args:
            **kwargs: 各フィールドの初期値または'bitstr'からの変換
        """
        # 拡張フィールドの初期化
        self.longitude = 0
        self.latitude = 0
        
        # 親クラスの初期化
        super().__init__(**kwargs)
        
        # bitstrが既に処理されていれば終了
        if 'bitstr' in kwargs:
            return
            
        # 拡張フィールドをキーワード引数から設定
        for field in ['longitude', 'latitude']:
            if field in kwargs:
                setattr(self, field, kwargs[field])

    def from_bits(self, bitstr: int) -> None:
        """
        ビット列から全フィールドを設定する
        
        Args:
            bitstr: 解析するビット列
        """
        # 親クラスのフィールドを設定
        super().from_bits(bitstr)
        
        try:
            # 拡張フィールドを設定
            for field, (start, length) in self._EXTENDED_BIT_FIELDS.items():
                value = self.extract_bits(bitstr, start, length)
                setattr(self, field, value)
        except Exception as e:
            raise BitFieldError(f"拡張ビット列の解析中にエラーが発生しました: {e}")

    def to_bits(self) -> int:
        """
        全フィールドをビット列に変換する
        
        Returns:
            ビット列表現
        """
        try:
            # 親クラスのビット列を取得
            bitstr = super().to_bits()
            
            # 拡張フィールドを設定
            for field, (start, length) in self._EXTENDED_BIT_FIELDS.items():
                value = getattr(self, field)
                max_val = (1 << length) - 1
                bitstr |= (value & max_val) << start
                
            return bitstr
        except Exception as e:
            raise BitFieldError(f"拡張ビット列への変換中にエラーが発生しました: {e}")
            
    def as_dict(self) -> Dict[str, Any]:
        """
        全フィールドを辞書形式で返す
        
        Returns:
            フィールド名と値の辞書
        """
        result = super().as_dict()
        # 拡張フィールドを追加
        for field in self._EXTENDED_BIT_FIELDS:
            result[field] = getattr(self, field)
        return result


class ResolverResponse(Format):
    """
    リゾルバレスポンスパケット
    
    拡張フィールド:
    - longitude: 129-192bit (64ビット)
    - latitude:  193-256bit (64ビット)
    - ex_field:  257-ビット
    """
    
    # 拡張ビットフィールド定義 (位置, 長さ)
    _EXTENDED_BIT_FIELDS = {
        'longitude': (128, 64),
        'latitude': (192, 64),
    }
    
    def __init__(self, **kwargs):
        """
        リゾルバレスポンスパケットの初期化
        
        Args:
            **kwargs: 各フィールドの初期値または'bitstr'からの変換
        """
        # 拡張フィールドの初期化
        self.longitude = 0
        self.latitude = 0
        self.ex_field = 0
        
        # 親クラスの初期化
        super().__init__(**kwargs)
        
        # bitstrが既に処理されていれば終了
        if 'bitstr' in kwargs:
            return
            
        # 拡張フィールドをキーワード引数から設定
        for field in ['longitude', 'latitude', 'ex_field']:
            if field in kwargs:
                setattr(self, field, kwargs[field])

    def from_bits(self, bitstr: int) -> None:
        """
        ビット列から全フィールドを設定する
        
        Args:
            bitstr: 解析するビット列
        """
        # 親クラスのフィールドを設定
        super().from_bits(bitstr)
        
        try:
            # 拡張フィールドを設定
            for field, (start, length) in self._EXTENDED_BIT_FIELDS.items():
                value = self.extract_bits(bitstr, start, length)
                setattr(self, field, value)
                
            # ex_fieldを設定（残りのビット）
            ex_field_start = max(start + length for start, length in self._EXTENDED_BIT_FIELDS.items())
            self.ex_field = self.extract_rest_bits(bitstr, ex_field_start)
        except Exception as e:
            raise BitFieldError(f"拡張ビット列の解析中にエラーが発生しました: {e}")

    def to_bits(self) -> int:
        """
        全フィールドをビット列に変換する
        
        Returns:
            ビット列表現
        """
        try:
            # 親クラスのビット列を取得
            bitstr = super().to_bits()
            
            # 拡張フィールドを設定
            for field, (start, length) in self._EXTENDED_BIT_FIELDS.items():
                value = getattr(self, field)
                max_val = (1 << length) - 1
                bitstr |= (value & max_val) << start
                
            # ex_fieldを設定
            ex_field_start = max(start + length for start, length in self._EXTENDED_BIT_FIELDS.items())
            bitstr |= self.ex_field << ex_field_start
            
            return bitstr
        except Exception as e:
            raise BitFieldError(f"拡張ビット列への変換中にエラーが発生しました: {e}")
            
    def as_dict(self) -> Dict[str, Any]:
        """
        全フィールドを辞書形式で返す
        
        Returns:
            フィールド名と値の辞書
        """
        result = super().as_dict()
        # 拡張フィールドを追加
        for field in list(self._EXTENDED_BIT_FIELDS.keys()) + ['ex_field']:
            result[field] = getattr(self, field)
        return result


# 使用例
if __name__ == "__main__":
    # 基本的な使用方法
    req = Request(version=1, packet_ID=123, type=2, weather_flag=1, timestamp=123456789)
    print(f"リクエスト: {req}")
    
    # ビット列への変換とその逆変換
    bitstr = req.to_bits()
    print(f"ビット列: {bitstr:b}")
    
    req2 = Request(bitstr=bitstr)
    print(f"復元されたリクエスト: {req2}")
    
    # バイト列への変換とその逆変換
    bytes_data = req.to_bytes()
    print(f"バイト列: {bytes_data.hex()}")
    
    req3 = Request.from_bytes(bytes_data)
    print(f"バイト列から復元: {req3}")
    
    # 辞書形式での取得
    print(f"辞書形式: {req.as_dict()}")
    
    # レスポンスの作成
    res = Response(
        version=1, 
        packet_ID=123, 
        type=2, 
        weather_flag=1, 
        timestamp=123456789,
        weather_code=1001,
        temperature=25,
        pops=80
    )
    print(f"レスポンス: {res}")
    
    # エラー処理のデモ
    try:
        # 範囲外の値
        invalid_req = Request(version=20)  # version は 4ビットなので最大は 15
    except BitFieldError as e:
        print(f"エラー捕捉: {e}")