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


    # 拡張フィールドのヘッダー
    _EXTENDED_HEADER = {
        'length': (0, 10),
        'key': (10, 6),
    }

    # 拡張フィールドのヘッダーの有効範囲
    _EXTENDED_HEADER_RANGES = {
        'length': (0, (1 << 10) - 1),
        'key': (0, (1 << 6) - 1),
    }

    # 拡張フィールドのキーと値のマッピング
    _EXTENDED_FIELD_MAPPING_INT = {
        1: 'alert',
        17: 'disaster',
        65: 'latitude',
        66: 'longitude',
        128: 'source_ip',
    }

    _EXTENDED_FIELD_MAPPING_STR = {
        'alert': 1,
        'disaster': 17,
        'latitude': 65,
        'longitude': 66,
        'source_ip': 128,
    }

    def __init__(self, *, version=0, packet_id=0, type=0, weather_flag=0, temperature_flag=0, 
                 pops_flag=0, alert_flag=0, disaster_flag=0, ex_flag=0, day=0, reserved=0, 
                 timestamp=0, area_code=0, checksum=0, ex_field=None, bitstr=None):
        """
        共通フィールドの初期化
        
        Args:
            version: バージョン番号
            packet_id: パケットID
            type: パケットタイプ
            weather_flag: 天気フラグ
            temperature_flag: 気温フラグ
            pops_flag: 降水確率フラグ
            alert_flag: 警報フラグ
            disaster_flag: 災害フラグ
            ex_flag: 拡張フラグ
            day: 日数
            reserved: 予約領域
            timestamp: タイムスタンプ
            area_code: エリアコード
            checksum: チェックサム
            ex_field: 拡張フィールド辞書
            bitstr: ビット列からの変換用
        """
        # フィールドの初期化
        self.version = version
        self.packet_id = packet_id
        self.type = type
        self.weather_flag = weather_flag
        self.temperature_flag = temperature_flag
        self.pops_flag = pops_flag
        self.alert_flag = alert_flag
        self.disaster_flag = disaster_flag
        self.ex_flag = ex_flag
        self.day = day
        self.reserved = reserved
        self.timestamp = timestamp
        self.area_code = area_code
        self.checksum = checksum
        self.ex_field = {} if ex_field is None else ex_field
        #self.next_server_ip = 0

        
        # 'bitstr'が提供された場合はそれを解析
        if bitstr is not None:
            self.from_bits(bitstr)
            return
            
        # 各フィールドの値を検証
        for field in self._BIT_FIELDS.keys():
            value = getattr(self, field)
            self._set_validated_field(field, value)

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
        """
        return bitstr >> start

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
        
        # ビット長を計算
        bit_length = bitstr.bit_length()
        
        # 必要なバイト数を計算（8で割って切り上げ）
        # 最低でも32バイト（256ビット）を確保
        num_bytes = max((bit_length + 7) // 8, 32)
        
        # 拡張フィールドがある場合は追加のバイトを確保
        if hasattr(self, 'ex_field') and self.ex_field and self.ex_flag == 1:
            # 拡張フィールドごとに必要なバイト数を追加
            for value in self.ex_field.values():
                if isinstance(value, list):
                    # リストの場合、各要素の文字列表現のバイト数を加算
                    for item in value:
                        num_bytes += len(str(item).encode('utf-8'))
                elif isinstance(value, str):
                    # 文字列の場合、UTF-8エンコードのバイト数を加算
                    num_bytes += len(value.encode('utf-8'))
                elif isinstance(value, (int, float)):
                    # 数値の場合、ビット長から必要なバイト数を計算
                    val_bits = int(value) if isinstance(value, float) else value
                    num_bytes += (val_bits.bit_length() + 7) // 8
            
            # ヘッダー用の追加バイト（各拡張フィールドに16+8ビットのヘッダーが必要）
            num_bytes += len(self.ex_field) * 3  # (16+8)/8 = 3 bytes per header
        
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
    def fetch_ex_field(self, bitstr: int, total_bits: int = -1) -> None:
        """
        拡張フィールド (ex_field) のデータを解析します。
        
        ビット列は次のフォーマットとなっています：
        ・先頭10ビット：バイト数を示す
        ・次の6ビット：キー
        ・その後 (バイト数 * 8) ビット分：値
        これらのレコードが連続していると想定し、全レコードを解析します。
        
        Args:
        bitstr: 解析対象のビット列（整数として与えられる）
        total_bits: ビット列全体の長さ。送信ビット列が固定長で先頭の0が有意な場合、この値を指定してください。
                    省略時は bitstr.bit_length() を利用します。
        """
        result = []
        current_pos = 0
        # 入力ビット列の情報を表示
        print(f"入力ビット列: {bin(bitstr)}")
        
        # 拡張フィールドの開始位置を計算
        ex_field_start = max(pos + size for field, (pos, size) in self._BIT_FIELDS.items())
        
        # 拡張フィールドのビット列を取得
        ex_field_bits = self.extract_rest_bits(bitstr, ex_field_start)
        
        # ビット長を計算（最低でも16ビット必要）
        if total_bits == -1:
            total_bits = ex_field_bits.bit_length()
        
        # 拡張フィールドの処理
        while current_pos < total_bits and ex_field_bits != 0:
            # 残りのビット数が16ビット未満なら終了
            if total_bits - current_pos < 16:
                break
                
            # ヘッダーを取得（16ビット）
            header = self.extract_bits(bitstr, current_pos, 16)
            
            # ヘッダーから長さとキーを抽出
            key = (header >> 10) & 0x3F    # 上位6ビットがキー
            bytes_length = header & 0x3FF  # 下位10ビットが長さ
            
            bits_length = bytes_length * 8
            print(f"位置 {current_pos}: バイト数={bytes_length}, ビット数={bits_length}")
            print(f"位置 {current_pos}: キー={key}")
            
            # 必要なビット数を計算
            required_bits = 16 + bits_length  # ヘッダー + データ
            
            # 残りのビット数が足りなければ終了
            if current_pos + required_bits > total_bits:
                print(f"残りのビットが不足しています: 必要={required_bits}, 残り={total_bits - current_pos}")
                break
            
            # 値を取得（ヘッダーの後ろから）
            value_bits = self.extract_bits(bitstr, current_pos + 16, bits_length)
            
            # バイト列に変換して文字列にデコード
            try:
                value_bytes = value_bits.to_bytes(bytes_length, byteorder='big')
                if key in [1, 17]:  # alert, disaster
                    value = value_bytes.decode('utf-8')
                elif key in [65, 66]:  # latitude, longitude
                    value = int.from_bytes(value_bytes, byteorder='big')
                elif key == 128:  # source_ip
                    value = value_bytes.decode('utf-8')
                else:
                    value = value_bits
            except UnicodeDecodeError:
                value = value_bits
                
            print(f"位置 {current_pos}: 値={value} (長さ={bits_length}ビット)")
            current_pos += 16 + bits_length  # ヘッダー + データ長
            
            # 結果を辞書に登録
            field_key = self._get_extended_field_key(key)
            if field_key:
                result.append({field_key: value})
                print(f"登録: key={key}, value={value}")
        
        self.ex_field = self._extended_field_to_dict(result)
    def _dict_to_ex_field_bits(self, ex_field_dict: dict) -> int:
        """
        ex_field辞書をビット列に変換する
        
        Args:
            ex_field_dict: 変換する辞書
            
        Returns:
            ビット列表現
        """
        result_bits = 0
        current_pos = 0
        
        # 辞書の各項目をビット列に変換
        for key, value in ex_field_dict.items():
            # キーを整数に変換
            if isinstance(key, str):
                key_int = self._get_extended_field_key_from_str(key)
                if key_int is None:
                    print(f"警告: キー '{key}' は拡張フィールドマッピングにありません")
                    continue
            else:
                key_int = key
                
            # 値をバイト列に変換
            if isinstance(value, list):
                # リストの場合、最初の要素を文字列として使用
                if not value:
                    continue
                value_str = str(value[0])
                value_bytes = value_str.encode('utf-8')
            elif isinstance(value, str):
                value_bytes = value.encode('utf-8')
            elif isinstance(value, (int, float)):
                value = int(value) if isinstance(value, float) else value
                value_bytes = value.to_bytes((value.bit_length() + 7) // 8 or 1, byteorder='big')
            else:
                print(f"警告: 値の型 {type(value)} は拡張フィールドでサポートされていません")
                continue

            # バイト数とビット長を計算
            bytes_needed = len(value_bytes)
            bits_length = bytes_needed * 8
            
            # バイト列をビット列に変換
            value_bits = int.from_bytes(value_bytes, byteorder='big')
            
            # 現在のフィールドのビット列を構築
            field_bits = 0
            
            # ヘッダー（6ビットのキー + 10ビットのバイト数）を配置
            header = ((key_int & 0x3F) << 10) | (bytes_needed & 0x3FF)
            result_bits |= (header << current_pos)
            
            # 値を配置（ヘッダーの後ろに）
            result_bits |= (value_bits << (current_pos + 16))
            
            # 位置を更新（ヘッダー + データ長）
            current_pos += 16 + bits_length
            
            print(f"エンコード: キー={key_int}, バイト数={bytes_needed}, 値={value_bits:x}")
        
        return result_bits

    def _extended_field_to_dict(self, extended_field: list) -> dict:
        """
        拡張フィールドを辞書に変換する
        """
        result = {}
        for item in extended_field:
            key = list(item.keys())[0]
            value = item[key]
            if key in ["alert", "disaster"]:
                if key not in result:
                    result[key] = [value]
                else:
                    result[key].append(value)
            else:
                result[key] = value
        return result
        
    def _get_extended_field_key(self, key: int) -> str:
        """
        拡張フィールドのキーを文字列に変換する
        """
        return self._EXTENDED_FIELD_MAPPING_INT.get(key,None)
    
    def _get_extended_field_key_from_str(self, key: str) -> int:
        """
        拡張フィールドのキーを整数に変換する
        """
        return self._EXTENDED_FIELD_MAPPING_STR.get(key,None)


class Request(Format):
    """
    リクエストパケット
    

    拡張フィールド:
    - ex_field:       129- (可変長)
    """
    
    def __init__(self, *, version=0, packet_id=0, type=0, weather_flag=0, temperature_flag=0, 
                 pops_flag=0, alert_flag=0, disaster_flag=0, ex_flag=0, day=0, reserved=0, 
                 timestamp=0, area_code=0, checksum=0, ex_field=None, bitstr=None):
        """
        リクエストパケットの初期化
        
        Args:
            version: バージョン番号
            packet_id: パケットID
            type: パケットタイプ
            weather_flag: 天気フラグ
            temperature_flag: 気温フラグ
            pops_flag: 降水確率フラグ
            alert_flag: 警報フラグ
            disaster_flag: 災害フラグ
            ex_flag: 拡張フラグ
            day: 日数
            reserved: 予約領域
            timestamp: タイムスタンプ
            area_code: エリアコード
            checksum: チェックサム
            ex_field: 拡張フィールド辞書
            bitstr: ビット列からの変換用
        """
        # 親クラスの初期化
        super().__init__(version=version, packet_id=packet_id, type=type, weather_flag=weather_flag,
                         temperature_flag=temperature_flag, pops_flag=pops_flag, alert_flag=alert_flag,
                         disaster_flag=disaster_flag, ex_flag=ex_flag, day=day, reserved=reserved,
                         timestamp=timestamp, area_code=area_code, checksum=checksum, 
                         ex_field=ex_field, bitstr=bitstr)
        
        # bitstrが既に処理されていれば終了
        if bitstr is not None:
            return
    def from_bits(self, bitstr: int) -> None:
        # 親クラスのフィールドを設定
        super().from_bits(bitstr)
        
        # ex_flagが設定されていれば拡張フィールドを解析
        if self.ex_flag == 1:
            # 基本フィールドの後に続く拡張フィールドを解析
            ex_field_start = max(pos + size for field, (pos, size) in self._BIT_FIELDS.items())
            ex_field_bits = self.extract_rest_bits(bitstr, ex_field_start)
            self.fetch_ex_field(ex_field_bits)
    def to_bits(self) -> int:
        """
        全フィールドをビット列に変換する
        
        Returns:
            ビット列表現
        """
        try:
            # 親クラスのビット列を取得
            bitstr = super().to_bits()
            
            # ex_fieldを設定（辞書から適切なビット列を生成）
            if self.ex_flag == 1 and self.ex_field:
                ex_field_start = max(pos + size for field, (pos, size) in self._BIT_FIELDS.items())
                ex_field_bits = self._dict_to_ex_field_bits(self.ex_field)
                bitstr |= ex_field_bits << ex_field_start
            return bitstr
        except Exception as e:
            raise BitFieldError(f"拡張ビット列への変換中にエラーが発生しました: {e}")


class Response(Format):
    """
    レスポンスパケット
    
    拡張フィールド:
    - weather_code:   129-144bit (16ビット)
    - temperature:    145-152bit (8ビット)
    - pops:           153-160bit (8ビット)
    - ex_field:       161- (可変長)
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

    def __init__(self, *, version=0, packet_id=0, type=0, weather_flag=0, temperature_flag=0, 
                 pops_flag=0, alert_flag=0, disaster_flag=0, ex_flag=0, day=0, reserved=0, 
                 timestamp=0, area_code=0, checksum=0, ex_field=None, bitstr=None,
                 weather_code=0, temperature=0, pops=0):
        """
        レスポンスパケットの初期化
        
        Args:
            version: バージョン番号
            packet_id: パケットID
            type: パケットタイプ
            weather_flag: 天気フラグ
            temperature_flag: 気温フラグ
            pops_flag: 降水確率フラグ
            alert_flag: 警報フラグ
            disaster_flag: 災害フラグ
            ex_flag: 拡張フラグ
            day: 日数
            reserved: 予約領域
            timestamp: タイムスタンプ
            area_code: エリアコード
            checksum: チェックサム
            ex_field: 拡張フィールド辞書
            bitstr: ビット列からの変換用
            weather_code: 天気コード
            temperature: 気温
            pops: 降水確率
        """
        # 拡張フィールドの初期化
        self.weather_code = weather_code
        self.temperature = temperature
        self.pops = pops
        
        # 親クラスの初期化
        super().__init__(version=version, packet_id=packet_id, type=type, weather_flag=weather_flag,
                         temperature_flag=temperature_flag, pops_flag=pops_flag, alert_flag=alert_flag,
                         disaster_flag=disaster_flag, ex_flag=ex_flag, day=day, reserved=reserved,
                         timestamp=timestamp, area_code=area_code, checksum=checksum,
                         ex_field=ex_field, bitstr=bitstr)
        
        # bitstrが既に処理されていれば終了
        if bitstr is not None:
            return
            
        # 拡張フィールドの値を検証
        for field in self._EXTENDED_BIT_FIELDS.keys():
            value = getattr(self, field)
            self._set_validated_extended_field(field, value)

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
        # 親クラスのフィールドを設定
        super().from_bits(bitstr)
        
        # 拡張ビットフィールドを設定
        for field, (start, length) in self._EXTENDED_BIT_FIELDS.items():
            value = self.extract_bits(bitstr, start, length)
            setattr(self, field, value)
        
        # ex_flagが設定されていれば可変長拡張フィールドを解析
        if self.ex_flag == 1:
            # 固定拡張フィールドの後に続く可変長拡張フィールドを解析
            ex_field_start = max(pos + size for field, (pos, size) in self._EXTENDED_BIT_FIELDS.items())
            ex_field_bits = self.extract_rest_bits(bitstr, ex_field_start)
            self.fetch_ex_field(ex_field_bits)

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
                
            # ex_fieldを設定（辞書から適切なビット列を生成）
            if self.ex_flag == 1 and self.ex_field:
                ex_field_start = max(pos + size for _, (pos, size) in self._EXTENDED_BIT_FIELDS.items())
                ex_field_bits = self._dict_to_ex_field_bits(self.ex_field)
                bitstr |= ex_field_bits << ex_field_start
            
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
    from uuid import uuid4
    from datetime import datetime
    latitude = 35.6895
    longitude = 139.6917
    req = Request(version=1, packet_id=1, type=0, weather_flag=0, timestamp=int(datetime.now().timestamp()), ex_flag=1, 
                  ex_field={'alert':["津波警報"],
                            "disaster":["土砂崩れ"],
                            "latitude":latitude,
                            "longitude":longitude,
                            "source_ip":"127.0.0.1"
                            })
    print(f"リクエスト: {req.__dict__}")
    print(f"バイト列: {req.to_bytes()}")
    req1 = Request.from_bytes(req.to_bytes())
    print(f"復元したリクエスト: {req1.__dict__}")


    res = Response(version=1, packet_id=1, type=1, weather_flag=0, timestamp=int(datetime.now().timestamp()), ex_flag=1, ex_field={'alert':["津波警報"],
                            "disaster":["土砂崩れ"],
                            "latitude":latitude,
                            "longitude":longitude,
                            "source_ip":"127.0.0.1"
                            })
    print(f"レスポンス: {res.__dict__}")
    print(f"バイト列: {res.to_bytes()}")
    res1 = Response.from_bytes(res.to_bytes())
    print(f"復元したレスポンス: {res1.__dict__}")