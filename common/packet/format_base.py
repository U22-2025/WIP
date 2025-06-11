"""
パケットフォーマットの基底クラス（修正版）
共通ヘッダー部分の構造を定義し、ビット操作の基本機能を提供します
"""
from typing import Optional, Union, Dict, Any
from .exceptions import BitFieldError
from .bit_utils import extract_bits


class FormatBase:
    """
    パケットフォーマットの基底クラス
    共通ヘッダー部分の構造を定義し、ビット操作の基本機能を提供します
    
    ビットフィールド構造:
    - version:          1-4bit   (4ビット)
    - packet_id:        5-16bit  (12ビット)
    - type:             17-19bit (3ビット)
    - weather_flag:     20bit    (1ビット)
    - temperature_flag: 21bit    (1ビット)
    - pop_flag:        22bit    (1ビット)
    - alert_flag:       23bit    (1ビット)
    - disaster_flag:    24bit    (1ビット)
    - ex_flag:          25bit    (1ビット)
    - day:              26-28bit (3ビット)
    - reserved:         29-32bit (4ビット)
    - timestamp:        33-96bit (64ビット)
    - area_code:        97-116bit (20ビット)
    - checksum:         117-128bit (12ビット)
    """
    
    # ビットフィールドの長さ定義
    FIELD_LENGTH = {
        'version': 4,          # バージョン番号
        'packet_id': 12,       # パケットID
        'type': 3,            # パケットタイプ
        'weather_flag': 1,     # 天気フラグ
        'temperature_flag': 1, # 気温フラグ
        'pop_flag': 1,       # 降水確率フラグ
        'alert_flag': 1,      # 警報フラグ
        'disaster_flag': 1,    # 災害フラグ
        'ex_flag': 1,         # 拡張フラグ
        'day': 3,             # 日数
        'reserved': 4,        # 予約領域
        'timestamp': 64,      # タイムスタンプ
        'area_code': 20,      # エリアコード
        'checksum': 12,       # チェックサム
    }

    # ビットフィールドの開始位置を計算
    FIELD_POSITION = {}
    _current_pos = 0
    for field, length in FIELD_LENGTH.items():
        FIELD_POSITION[field] = _current_pos
        _current_pos += length

    # ビットフィールド定義 (位置, 長さ)
    _BIT_FIELDS = {}
    for field, pos in FIELD_POSITION.items():
        _BIT_FIELDS[field] = (pos, FIELD_LENGTH[field])
    
    # フィールドの有効範囲
    _FIELD_RANGES = {
        field: (0, (1 << length) - 1)
        for field, length in FIELD_LENGTH.items()
    }

    def __init__(
        self,
        *,
        # 基本フィールド
        version: int = 0,
        packet_id: int = 0,
        type: int = 0,
        weather_flag: int = 0,
        temperature_flag: int = 0,
        pop_flag: int = 0,
        alert_flag: int = 0,
        disaster_flag: int = 0,
        ex_flag: int = 0,
        day: int = 0,
        reserved: int = 0,
        timestamp: int = 0,
        area_code: Union[int, str] = 0,
        checksum: int = 0,
        # ビット列
        bitstr: Optional[int] = None
    ) -> None:
        """
        共通フィールドの初期化
        
        Args:
            version: バージョン番号 (4ビット)
            packet_id: パケットID (12ビット)
            type: パケットタイプ (3ビット)
            weather_flag: 天気フラグ (1ビット)
            temperature_flag: 気温フラグ (1ビット)
            pop_flag: 降水確率フラグ (1ビット)
            alert_flag: 警報フラグ (1ビット)
            disaster_flag: 災害フラグ (1ビット)
            ex_flag: 拡張フラグ (1ビット)
            day: 日数 (3ビット)
            reserved: 予約領域 (4ビット)
            timestamp: タイムスタンプ (64ビット)
            area_code: エリアコード (20ビット)
            checksum: チェックサム (12ビット)
            bitstr: ビット列からの変換用
            
        Raises:
            BitFieldError: フィールド値が不正な場合
        """
        try:
            # チェックサム自動計算フラグ
            self._auto_checksum = True
            
            # ビット列が提供された場合はそれを解析
            if bitstr is not None:
                self.from_bits(bitstr)
                # from_bitsから受け取った場合はチェックサムをそのまま保持
                return
                
            # フィールドの初期化と検証
            field_values = {
                'version': version,
                'packet_id': packet_id,
                'type': type,
                'weather_flag': weather_flag,
                'temperature_flag': temperature_flag,
                'pop_flag': pop_flag,
                'alert_flag': alert_flag,
                'disaster_flag': disaster_flag,
                'ex_flag': ex_flag,
                'day': day,
                'reserved': reserved,
                'timestamp': timestamp,
                'area_code': area_code,
                'checksum': checksum,
            }
            
            # 各フィールドを設定・検証
            for field, value in field_values.items():
                self._set_validated_field(field, value)
                
        except BitFieldError:
            raise
        except Exception as e:
            raise BitFieldError("パケットの初期化中にエラー: {}".format(e))

    def _set_validated_field(self, field: str, value: Union[int, float, str]) -> None:
        """
        フィールド値を検証して設定する
        
        Args:
            field: 設定するフィールド名
            value: 設定する値（整数、浮動小数点、または文字列）
            
        Raises:
            BitFieldError: 値が有効範囲外の場合、または不正な型の場合
        """
        # area_codeフィールドの特別な処理
        if field == 'area_code':
            if isinstance(value, str):
                try:
                    value = int(value)
                except ValueError:
                    raise BitFieldError(f"エリアコード '{value}' は有効な数値ではありません")
            elif isinstance(value, (int, float)):
                value = int(value)
            else:
                raise BitFieldError(f"エリアコードは文字列または数値である必要があります。受け取った型: {type(value)}")
        else:
            # 他のフィールドは数値のみ
            if not isinstance(value, (int, float)):
                raise BitFieldError(f"フィールド '{field}' の値は数値である必要があります。受け取った型: {type(value)}")
            
        # 浮動小数点数を整数に変換
        if isinstance(value, float):
            value = int(value)
            
        if field in self._FIELD_RANGES:
            min_val, max_val = self._FIELD_RANGES[field]
            if not (min_val <= value <= max_val):
                raise BitFieldError("フィールド '{}' の値 {} が有効範囲 {}～{} 外です".format(
                    field, value, min_val, max_val))
                
        # 内部フィールドに値を設定
        setattr(self, f'_{field}', value)
        
        # チェックサム以外のフィールドが更新された場合、チェックサムを再計算
        if field != 'checksum' and hasattr(self, '_auto_checksum') and self._auto_checksum:
            self._recalculate_checksum()

    def _recalculate_checksum(self) -> None:
        """
        チェックサムを再計算する
        """
        try:
            # 一時的にチェックサムを0にしてビット列を取得
            original_checksum = getattr(self, '_checksum', 0)
            self._checksum = 0
            bitstr = self.to_bits()
            
            # 必要なバイト数を計算
            required_bytes = (bitstr.bit_length() + 7) // 8
            min_packet_size = self.get_min_packet_size()
            
            # リトルエンディアンでバイト列に変換
            if required_bytes > 0:
                bytes_data = bitstr.to_bytes(required_bytes, byteorder='little')
            else:
                bytes_data = b''
            
            # パケットタイプに応じた最小サイズまでパディング
            if len(bytes_data) < min_packet_size:
                bytes_data = bytes_data + b'\x00' * (min_packet_size - len(bytes_data))
            
            # チェックサムを計算して設定
            self._checksum = self.calc_checksum12(bytes_data)
            
        except Exception as e:
            # エラー時は元のチェックサムを復元
            self._checksum = original_checksum
            raise BitFieldError(f"チェックサム再計算中にエラー: {e}")

    # プロパティを定義してフィールド更新時の自動チェックサム計算を実現
    @property
    def version(self) -> int:
        return getattr(self, '_version', 0)
    
    @version.setter
    def version(self, value: Union[int, float]) -> None:
        self._set_validated_field('version', value)
    
    @property
    def packet_id(self) -> int:
        return getattr(self, '_packet_id', 0)
    
    @packet_id.setter
    def packet_id(self, value: Union[int, float]) -> None:
        self._set_validated_field('packet_id', value)
    
    @property
    def type(self) -> int:
        return getattr(self, '_type', 0)
    
    @type.setter
    def type(self, value: Union[int, float]) -> None:
        self._set_validated_field('type', value)
    
    @property
    def weather_flag(self) -> int:
        return getattr(self, '_weather_flag', 0)
    
    @weather_flag.setter
    def weather_flag(self, value: Union[int, float]) -> None:
        self._set_validated_field('weather_flag', value)
    
    @property
    def temperature_flag(self) -> int:
        return getattr(self, '_temperature_flag', 0)
    
    @temperature_flag.setter
    def temperature_flag(self, value: Union[int, float]) -> None:
        self._set_validated_field('temperature_flag', value)
    
    @property
    def pop_flag(self) -> int:
        return getattr(self, '_pop_flag', 0)
    
    @pop_flag.setter
    def pop_flag(self, value: Union[int, float]) -> None:
        self._set_validated_field('pop_flag', value)
    
    @property
    def alert_flag(self) -> int:
        return getattr(self, '_alert_flag', 0)
    
    @alert_flag.setter
    def alert_flag(self, value: Union[int, float]) -> None:
        self._set_validated_field('alert_flag', value)
    
    @property
    def disaster_flag(self) -> int:
        return getattr(self, '_disaster_flag', 0)
    
    @disaster_flag.setter
    def disaster_flag(self, value: Union[int, float]) -> None:
        self._set_validated_field('disaster_flag', value)
    
    @property
    def ex_flag(self) -> int:
        return getattr(self, '_ex_flag', 0)
    
    @ex_flag.setter
    def ex_flag(self, value: Union[int, float]) -> None:
        self._set_validated_field('ex_flag', value)
    
    @property
    def day(self) -> int:
        return getattr(self, '_day', 0)
    
    @day.setter
    def day(self, value: Union[int, float]) -> None:
        self._set_validated_field('day', value)
    
    @property
    def reserved(self) -> int:
        return getattr(self, '_reserved', 0)
    
    @reserved.setter
    def reserved(self, value: Union[int, float]) -> None:
        self._set_validated_field('reserved', value)
    
    @property
    def timestamp(self) -> int:
        return getattr(self, '_timestamp', 0)
    
    @timestamp.setter
    def timestamp(self, value: Union[int, float]) -> None:
        self._set_validated_field('timestamp', value)
    
    @property
    def area_code(self) -> str:
        """エリアコードを6桁の文字列として返す"""
        area_code_int = getattr(self, '_area_code', 0)
        return f"{area_code_int:06d}"
    
    @area_code.setter
    def area_code(self, value: Union[int, str]) -> None:
        """エリアコードを設定する（数値または文字列を受け取り、内部では数値として保存）"""
        if isinstance(value, str):
            # 文字列の場合は数値に変換
            try:
                area_code_int = int(value)
            except ValueError:
                raise BitFieldError(f"エリアコード '{value}' は有効な数値ではありません")
        elif isinstance(value, (int, float)):
            area_code_int = int(value)
        else:
            raise BitFieldError(f"エリアコードは文字列または数値である必要があります。受け取った型: {type(value)}")
        
        # 20ビットの範囲チェック
        if not (0 <= area_code_int <= 1048575):  # 2^20 - 1
            raise BitFieldError(f"エリアコード {area_code_int} が20ビットの範囲（0-1048575）を超えています")
        
        # 内部では数値として保存（パケット化のため）
        self._set_validated_field('area_code', area_code_int)
    
    @property
    def checksum(self) -> int:
        return getattr(self, '_checksum', 0)
    
    @checksum.setter
    def checksum(self, value: Union[int, float]) -> None:
        self._set_validated_field('checksum', value)

    def from_bits(self, bitstr: int) -> None:
        """
        ビット列から全フィールドを設定する
        
        Args:
            bitstr: 解析するビット列
        """
        try:
            for field, (start, length) in self._BIT_FIELDS.items():
                value = extract_bits(bitstr, start, length)
                setattr(self, field, value)
        except Exception as e:
            raise BitFieldError(f"ビット列の解析中にエラーが発生しました: {e}")

    def get_min_packet_size(self) -> int:
        """
        パケットの最小サイズを取得する（子クラスでオーバーライド可能）
        
        Returns:
            最小パケットサイズ（バイト）
        """
        # 基本フィールド（128ビット = 16バイト）
        return 16

    def to_bits(self) -> int:
        """
        全フィールドをビット列に変換する
        
        Returns:
            ビット列表現
        """
        try:
            bitstr = 0
            for field, (start, length) in self._BIT_FIELDS.items():
                # area_codeフィールドの特別な処理
                if field == 'area_code':
                    # 内部の数値を直接取得
                    value = getattr(self, f'_{field}', 0)
                else:
                    value = getattr(self, field)
                
                # 値の範囲を確認
                if isinstance(value, float):
                    value = int(value)
                elif isinstance(value, str):
                    # 文字列の場合は数値に変換
                    try:
                        value = int(value)
                    except ValueError:
                        raise BitFieldError(f"フィールド '{field}' の文字列値 '{value}' を数値に変換できません")
                
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
        
        基本フィールドをバイト列に変換します。
        チェックサムを計算して格納します。
        
        Returns:
            バイト列表現
            
        Raises:
            BitFieldError: バイト列への変換中にエラーが発生した場合
        """
        try:
            # 一時的にチェックサムを0にしてビット列を取得
            original_checksum = self.checksum
            self.checksum = 0
            bitstr = self.to_bits()
            
            # 必要なバイト数を計算
            required_bytes = (bitstr.bit_length() + 7) // 8
            min_packet_size = self.get_min_packet_size()
            
            # リトルエンディアンでバイト列に変換
            if required_bytes > 0:
                bytes_data = bitstr.to_bytes(required_bytes, byteorder='little')
            else:
                bytes_data = b''
            
            # パケットタイプに応じた最小サイズまでパディング
            if len(bytes_data) < min_packet_size:
                bytes_data = bytes_data + b'\x00' * (min_packet_size - len(bytes_data))
            
            # チェックサムを計算して設定
            self.checksum = self.calc_checksum12(bytes_data)
            
            # 最終的なビット列を生成（チェックサムを含む）
            final_bitstr = self.to_bits()
            
            # 最終的なバイト列を生成
            final_required_bytes = (final_bitstr.bit_length() + 7) // 8
            if final_required_bytes > 0:
                final_bytes = final_bitstr.to_bytes(final_required_bytes, byteorder='little')
            else:
                final_bytes = b''
            
            # パケットタイプに応じた最小サイズまでパディング
            if len(final_bytes) < min_packet_size:
                final_bytes = final_bytes + b'\x00' * (min_packet_size - len(final_bytes))
            
            return final_bytes
            
        except Exception as e:
            # エラー時は元のチェックサムを復元
            self.checksum = original_checksum
            raise BitFieldError("バイト列への変換中にエラー: {}".format(e))
        
    @classmethod
    def from_bytes(cls, data: bytes) -> 'FormatBase':
        """
        バイト列からインスタンスを生成する
        
        Args:
            data: バイト列
            
        Returns:
            生成されたインスタンス
        """
        # バイト列の長さが最小パケットサイズより短い場合はエラー
        min_packet_size = cls().get_min_packet_size()
        if len(data) < min_packet_size:
            raise BitFieldError(f"バイト列の長さが最小パケットサイズ {min_packet_size} バイトより短いです。受け取った長さ: {len(data)} バイト")

        # リトルエンディアンからビット列に変換
        bitstr = int.from_bytes(data, byteorder='little')
        
        # インスタンスを作成（bitstrは渡さない）
        instance = cls()
        
        # パケット全体のビット長を保存
        instance._total_bits = len(data) * 8
        
        # from_bitsを手動で呼び出す（_total_bitsが設定された後）
        instance.from_bits(bitstr)
        
        # チェックサムを検証
        if not instance.verify_checksum12(data):
            raise BitFieldError("チェックサム検証に失敗しました。パケットが破損しているか、改ざんされています。")
        
        return instance
        
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
        
    def calc_checksum12(self, data: bytes) -> int:
        """
        12ビットチェックサムを計算する
        
        Args:
            data: チェックサム計算対象のバイト列
            
        Returns:
            12ビットチェックサム値
        """
        sum = 0
        
        # 1バイトずつ加算
        for byte in data:
            sum += byte
            
        # キャリーを12ビットに折り返し
        while sum >> 12:
            sum = (sum & 0xFFF) + (sum >> 12)
            
        # 1の補数を返す（12ビットマスク）
        checksum = (~sum) & 0xFFF
        return checksum
        
    def verify_checksum12(self, data_with_checksum: bytes) -> bool:
        """
        12ビットチェックサムを検証する
        
        Args:
            data_with_checksum: チェックサムを含むバイト列
            
        Returns:
            チェックサムが正しければTrue
        """
        try:
            # データからビット列を復元（リトルエンディアン）
            bitstr = int.from_bytes(data_with_checksum, byteorder='little')
            
            # チェックサム部分を抽出
            checksum_start, checksum_length = self._BIT_FIELDS['checksum']
            stored_checksum = extract_bits(bitstr, checksum_start, checksum_length)
            
            # チェックサム部分を0にしたデータを作成
            checksum_mask = ((1 << checksum_length) - 1) << checksum_start
            bitstr_without_checksum = bitstr & ~checksum_mask
            
            # チェックサム部分を0にしたバイト列を生成（リトルエンディアン）
            data_without_checksum = bitstr_without_checksum.to_bytes(len(data_with_checksum), byteorder='little')
            
            # チェックサムを計算
            calculated_checksum = self.calc_checksum12(data_without_checksum)
            
            # 計算されたチェックサムと格納されたチェックサムを比較
            return calculated_checksum == stored_checksum
            
        except Exception:
            return False
        
    def as_dict(self) -> Dict[str, Any]:
        """
        全フィールドを辞書形式で返す
        
        Returns:
            フィールド名と値の辞書
        """
        return {field: getattr(self, field) for field in self._BIT_FIELDS}
