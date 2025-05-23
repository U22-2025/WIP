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
    - packet_id:        5-16bit  (12ビット)
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
        'packet_id': (4, 12),
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
        'packet_id': (0, (1 << 12) - 1),
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
        self.packet_id = 0
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
        self.ex_field = {}
        #self.next_server_ip = 0

        
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
                if isinstance(value, float):
                    value = int(value)
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
        # 基本ビットフィールドの最大位置を計算
        max_pos = max(bit_pos + bit_len for bit_pos, bit_len in self._BIT_FIELDS.values())
        
        # 拡張ビットフィールドがある場合はそれも考慮
        extended_fields = getattr(self, '_EXTENDED_BIT_FIELDS', {})
        if extended_fields:
            extended_max = max(bit_pos + bit_len for bit_pos, bit_len in extended_fields.values())
            max_pos = max(max_pos, extended_max)
            
        # バイト数に変換（8ビット = 1バイト）
        num_bytes = (max_pos + 7) // 8
        
        # 少なくとも32バイト確保（256ビット）
        num_bytes = max(num_bytes, 32)
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
            ex_field_start = max(pos + size for _, (pos, size) in self._EXTENDED_BIT_FIELDS.items())
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
                if isinstance(value, float):
                    value = int(value)
                max_val = (1 << length) - 1
                if value > max_val:
                    raise BitFieldError(
                        f"フィールド '{field}' の値 {value} が最大値 {max_val} を超えています"
                    )
                bitstr |= (value & max_val) << start
                
            # ex_fieldを設定
            ex_field_start = max(pos + size for _, (pos, size) in self._EXTENDED_BIT_FIELDS.items())
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
                value = kwargs[field]
                # 座標値を10^6倍して整数に変換
                if field == 'longitude' or field == 'latitude':
                    if isinstance(value, float):
                        # 浮動小数点の座標値を10^6倍して整数に変換
                         value = int(value * (10**6))
                    # 整数の場合はそのまま使用（すでに変換済みと想定）
                
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
                # value = self.extract_bits(bitstr, start, length)
                raw_value = self.extract_bits(bitstr, start, length)
                # 座標値の場合、10^6で割って元の浮動小数点数に戻す
                if field == 'longitude' or field == 'latitude':
                    # 整数値を浮動小数点数に変換（10^6で割る）
                    value = raw_value / (10**6)
                else:
                    # 座標以外のフィールドはそのまま
                    value = raw_value
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
                if isinstance(value, float):
                    value = int(value)
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
        'ex_field': (256,None),
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
        self.ex_field = [] #辞書型
        
        # 親クラスの初期化
        super().__init__(**kwargs)
        
        # bitstrが既に処理されていれば終了
        if 'bitstr' in kwargs:
            return
            
        # 拡張フィールドをキーワード引数から設定
        for field in ['longitude', 'latitude', 'ex_field']:
            if field in kwargs:
                value = kwargs[field]
                # 座標値を10^6倍して整数に変換
                if field == 'longitude' or field == 'latitude':
                    if isinstance(value, float):
                        # 浮動小数点の座標値を10^6倍して整数に変換
                         value = int(value * (10**6))
                    # 整数の場合はそのまま使用（すでに変換済みと想定）
                
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
                if field == 'ex_field':
                    # ex_fieldは残りのビット全体を取得して別途処理
                    ex_field_start = start
                    ex_field_data = self.extract_rest_bits(bitstr, ex_field_start)
                    # ex_fieldデータを解析
                    self.fetch_ex_field(ex_field_data)
                elif length is not None:
                    # その他のフィールドは従来通り処理
                    raw_value = self.extract_bits(bitstr, start, length)
                    
                    # 座標値の場合、10^6で割って元の浮動小数点数に戻す
                    if field == 'longitude' or field == 'latitude':
                        value = raw_value / (10**6)
                    else:
                        value = raw_value
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
                if isinstance(value, float):
                    value = int(value)
                max_val = (1 << length) - 1
                bitstr |= (value & max_val) << start
                
            # ex_fieldを設定
            ex_field_start = max(pos + size for _, (pos, size) in self._EXTENDED_BIT_FIELDS.items())
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
def fetch_ex_field(self, bitstr: int, total_bits: int = None) -> None:
    """
    拡張フィールド (ex_field) のデータを解析します。
    
    ビット列は次のフォーマットとなっています：
    ・先頭16ビット：バイト数を示す（10進数と仮定しています）
    ・次の8ビット：キー
    ・その後 (バイト数 * 8) ビット分：値
    これらのレコードが連続していると想定し、全レコードを解析します。
    
    Args:
    bitstr: 解析対象のビット列（整数として与えられる）
    total_bits: ビット列全体の長さ。送信ビット列が固定長で先頭の0が有意な場合、この値を指定してください。
                省略時は bitstr.bit_length() を利用します。
    """
    result = {}
    current_pos = 0
    # total_bitsが指定されなければ、bit_length()で判定（注意：先頭の0は含まれない）
    if total_bits is None:
        total_bits = bitstr.bit_length()
        
    print(f"入力ビット列: {bin(bitstr)}")
    print(f"ビット長: {total_bits}")
    
    # レコードのヘッダはそれぞれ16+8=24ビット必要なため、その分が残っているか確認
    while current_pos + 24 <= total_bits:
        # 先頭16ビットからバイト数を取得（ここではBCD変換の必要がなければそのまま整数として扱う）
        length_field = self.extract_bits(bitstr, current_pos, 16)
        # もし、length_fieldがBCDでエンコードされている場合は以下のように変換してください：
        #   bytes_length = self.bcd_to_int(length_field, 4)
        # 今回はそのままバイナリ値と仮定します。
        bytes_length = length_field  
        bits_length = bytes_length * 8
        print(f"位置 {current_pos}: バイト数={bytes_length}, ビット数={bits_length}")
        current_pos += 16
        
        # 次の8ビットをキーとして抽出
        key = self.extract_bits(bitstr, current_pos, 8)
        print(f"位置 {current_pos}: キー={key}")
        current_pos += 8
        
        # 指定されたデータビットが全体に足りなければ処理終了
        if current_pos + bits_length > total_bits:
            print(f"残りのビットが不足しています: 必要={bits_length}, 残り={total_bits - current_pos}")
            break
        
        # バイト数で指定された長さ分のデータを値として抽出
        value = self.extract_bits(bitstr, current_pos, bits_length)
        print(f"位置 {current_pos}: 値={value} (長さ={bits_length}ビット)")
        current_pos += bits_length
        
        # 結果を辞書に登録
        result[key] = value
        print(f"登録: key={key}, value={value}")
    
    print(f"解析完了: {result}")
    self.ex_field = result

# 使用例
if __name__ == "__main__":
    from uuid import uuid4
    from datetime import datetime
    latitude = 35.6895
    longitude = 139.6917
    req = ResolverRequest(version=1, packet_id=1, type=0, weather_flag=0, timestamp=int(datetime.now().timestamp()), longitude=longitude, latitude=latitude, ex_field=0)
    print(f"{req}")
    print(f"{req.to_bits()}")
    res = ResolverResponse(bitstr = req.to_bits())
    print(f"{res}")