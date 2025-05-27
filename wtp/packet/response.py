"""
レスポンスパケット
"""
from typing import Optional, Dict, Any
from .exceptions import BitFieldError
from .format_base import FormatBase
from .extended_field_mixin import ExtendedFieldMixin
from .bit_utils import extract_bits, extract_rest_bits


class Response(FormatBase, ExtendedFieldMixin):
    """
    レスポンスパケット
    
    基本フィールド:
    - 共通ヘッダー (Format クラスと同じ)
    
    固定長拡張フィールド:
    - weather_code (129-144bit, 16ビット):
        天気コード。0-65535の範囲で天気状態を表す。
        
    - temperature (145-152bit, 8ビット):
        気温。0-255の範囲で気温を表す。
        実際の気温は、この値から100を引いた値となる（-100℃～+155℃）。
        
    - pops (153-160bit, 8ビット):
        降水確率 (Probability of Precipitation)。
        0-100の範囲でパーセント値を表す。
        
    可変長拡張フィールド (161bit-):
    - ex_field: 可変長の拡張データ
        - alert: 警報情報 (文字列のリスト)
        - disaster: 災害情報 (文字列のリスト)
        - latitude: 緯度 (数値)
        - longitude: 経度 (数値)
        - source_ip: 送信元IPアドレス (文字列)
    """
    
    # 固定長拡張フィールドの長さ定義
    FIXED_FIELD_LENGTH = {
        'weather_code': 16,  # 天気コード
        'temperature': 8,    # 気温
        'pops': 8,          # 降水確率
    }

    # 固定長拡張フィールドの開始位置を計算
    FIXED_FIELD_POSITION = {}
    _current_pos = 128  # 基本フィールドの後から開始
    for field, length in FIXED_FIELD_LENGTH.items():
        FIXED_FIELD_POSITION[field] = _current_pos
        _current_pos += length

    # 可変長拡張フィールドの開始位置
    VARIABLE_FIELD_START = _current_pos  # 161bit-

    # 固定長拡張フィールドの有効範囲
    FIXED_FIELD_RANGES = {
        'weather_code': (0, (1 << 16) - 1),  # 0-65535
        'temperature': (0, (1 << 8) - 1),    # 0-255 (-100℃～+155℃)
        'pops': (0, 100),                    # 0-100%
    }

    def __init__(
        self, 
        *,
        # 固定長拡張フィールド
        weather_code: int = 0,
        temperature: int = 0,
        pops: int = 0,
        # 可変長拡張フィールド
        ex_field: Optional[Dict[str, Any]] = None,
        # その他のパラメータ
        **kwargs
    ) -> None:
        """
        レスポンスパケットの初期化
        
        Args:
            weather_code: 天気コード (16ビット, 0-65535)
            temperature: 気温 (8ビット, -100℃～+155℃を0-255で表現)
            pops: 降水確率 (8ビット, 0-100%)
            ex_field: 拡張フィールド辞書
            **kwargs: 基本フィールドのパラメータ
            
        Raises:
            BitFieldError: フィールド値が不正な場合
        """
        try:
            # チェックサム自動計算フラグ
            self._auto_checksum = True
            
            # 可変長拡張フィールドの初期化
            self._ex_field = {} if ex_field is None else ex_field.copy()
            
            # ビット列が提供された場合はそれを解析
            if 'bitstr' in kwargs:
                # 固定長拡張フィールドを初期化（from_bitsで上書きされる）
                self.weather_code = 0
                self.temperature = 0
                self.pops = 0
                
                # 親クラスの初期化（from_bitsが呼ばれる）
                super().__init__(**kwargs)
                # from_bitsから受け取った場合はチェックサムをそのまま保持
                return
                
            # 通常の初期化の場合
            # 固定長拡張フィールドの初期化
            self.weather_code = 0
            self.temperature = 0
            self.pops = 0
            
            # 親クラスの初期化
            super().__init__(**kwargs)
            
            # 引数で与えられた固定長拡張フィールドの値を設定・検証
            self._set_validated_extended_field('weather_code', weather_code)
            self._set_validated_extended_field('temperature', temperature)
            self._set_validated_extended_field('pops', pops)
                
        except BitFieldError:
            raise
        except Exception as e:
            raise BitFieldError("レスポンスパケットの初期化中にエラー: {}".format(e))

    @property
    def ex_field(self) -> Dict[str, Any]:
        """拡張フィールドのプロパティ"""
        return getattr(self, '_ex_field', {})
    
    @ex_field.setter
    def ex_field(self, value: Dict[str, Any]) -> None:
        """拡張フィールドの設定時にチェックサムを再計算"""
        self._ex_field = value.copy() if value else {}
        # 拡張フィールドが更新された場合、チェックサムを再計算
        if hasattr(self, '_auto_checksum') and self._auto_checksum:
            self._recalculate_checksum()

    def _set_validated_extended_field(self, field: str, value: int) -> None:
        """
        拡張フィールド値を検証して設定する
        
        Args:
            field: 設定するフィールド名
            value: 設定する値
            
        Raises:
            BitFieldError: 値が有効範囲外の場合
        """
        if field in self.FIXED_FIELD_RANGES:
            min_val, max_val = self.FIXED_FIELD_RANGES[field]
            if not (min_val <= value <= max_val):
                raise BitFieldError("フィールド '{}' の値 {} が有効範囲 {}～{} 外です".format(
                    field, value, min_val, max_val))
                
        setattr(self, field, value)

    def from_bits(self, bitstr: int) -> None:
        """
        ビット列からフィールドを設定する
        
        Args:
            bitstr: 解析するビット列
            
        Raises:
            BitFieldError: ビット列の解析中にエラーが発生した場合
        """
        try:
            # 親クラスのフィールドを設定
            super().from_bits(bitstr)
            
            # 固定長拡張フィールドを設定（直接設定してチェックサム再計算を避ける）
            for field, pos in self.FIXED_FIELD_POSITION.items():
                length = self.FIXED_FIELD_LENGTH[field]
                value = extract_bits(bitstr, pos, length)
                # 値をマスクして有効範囲内に収める
                if field == 'pops':
                    value &= 0xFF  # 8ビットマスク (0-255)
                elif field == 'temperature':
                    value &= 0xFF  # 8ビットマスク (0-255)
                elif field == 'weather_code':
                    value &= 0xFFFF  # 16ビットマスク (0-65535)
                # 直接設定（チェックサム再計算を避ける）
                object.__setattr__(self, field, value)
            
            # ex_flagが設定されていれば可変長拡張フィールドを解析
            if self.ex_flag == 1:
                ex_field_bits = extract_rest_bits(bitstr, self.VARIABLE_FIELD_START)
                if ex_field_bits:
                    self.fetch_ex_field(ex_field_bits)
                
        except BitFieldError:
            raise
        except Exception as e:
            raise BitFieldError("ビット列の解析中にエラー: {}".format(e))

    def to_bits(self) -> int:
        """
        全フィールドをビット列に変換する
        
        Returns:
            ビット列表現
            
        Raises:
            BitFieldError: ビット列への変換中にエラーが発生した場合
        """
        try:
            # 親クラスのビット列を取得
            bitstr = super().to_bits()
            
            # 固定長拡張フィールドを設定
            for field, pos in self.FIXED_FIELD_POSITION.items():
                length = self.FIXED_FIELD_LENGTH[field]
                value = getattr(self, field)
                # 値の検証は_set_validated_extended_fieldで行われているため、
                # ここでは単純にビット操作のみを行う
                bitstr |= (value & ((1 << length) - 1)) << pos
                
            # ex_fieldを設定（辞書から適切なビット列を生成）
            if self.ex_flag == 1 and self.ex_field:
                ex_field_bits = self._dict_to_ex_field_bits(self.ex_field)
                bitstr |= ex_field_bits << self.VARIABLE_FIELD_START
            
            return bitstr
            
        except BitFieldError:
            raise
        except Exception as e:
            raise BitFieldError("拡張ビット列への変換中にエラー: {}".format(e))

    def to_bytes(self) -> bytes:
        """
        ビット列をバイト列に変換する
        
        基本フィールドと拡張フィールドを含むすべてのデータをバイト列に変換します。
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
            
            # 基本バイト数を計算（固定長拡張フィールドを含む最低バイト数）
            # 基本フィールド: 128ビット + 固定長拡張フィールド: 32ビット = 160ビット = 20バイト
            min_bytes_needed = (self.VARIABLE_FIELD_START + 7) // 8  # 161ビット = 21バイト
            num_bytes = max((bitstr.bit_length() + 7) // 8, min_bytes_needed)
            
            # 拡張フィールドのバイト数を計算
            if self.ex_flag == 1 and self.ex_field:
                # ヘッダー用のバイト数（各フィールドに24ビット = 3バイト）
                num_bytes += len(self.ex_field) * 3
                
                # 各値のバイト数を計算
                for value in self.ex_field.values():
                    try:
                        if isinstance(value, list):
                            # リストの場合、最初の要素のみを使用
                            if value:
                                num_bytes += len(str(value[0]).encode('utf-8'))
                        elif isinstance(value, str):
                            num_bytes += len(value.encode('utf-8'))
                        elif isinstance(value, (int, float)):
                            val_bits = int(value)
                            num_bytes += (val_bits.bit_length() + 7) // 8 or 1
                    except (ValueError, TypeError) as e:
                        raise BitFieldError(f"拡張フィールドの値の変換に失敗: {e}")
            
            # チェックサム計算用のバイト列を生成
            data_for_checksum = bitstr.to_bytes(num_bytes, byteorder='big')
            
            # チェックサムを計算して設定
            self.checksum = self.calc_checksum12(data_for_checksum)
            
            # 最終的なビット列を生成（チェックサムを含む）
            final_bitstr = self.to_bits()
            return final_bitstr.to_bytes(num_bytes, byteorder='big')
            
        except Exception as e:
            # エラー時は元のチェックサムを復元
            self.checksum = original_checksum
            raise BitFieldError("バイト列への変換中にエラー: {}".format(e))

    def as_dict(self) -> Dict[str, Any]:
        """
        全フィールドを辞書形式で返す
        
        Returns:
            フィールド名と値の辞書
        """
        result = super().as_dict()
        # 固定長拡張フィールドを追加
        for field in self.FIXED_FIELD_LENGTH:
            result[field] = getattr(self, field)
        # 可変長拡張フィールドを追加
        result['ex_field'] = self.ex_field
        return result
