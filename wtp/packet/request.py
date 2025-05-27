"""
リクエストパケット
"""
from typing import Optional, Dict, Any
from .exceptions import BitFieldError
from .format_base import FormatBase
from .extended_field_mixin import ExtendedFieldMixin
from .bit_utils import extract_rest_bits


class Request(FormatBase, ExtendedFieldMixin):
    """
    リクエストパケット
    
    拡張フィールド:
    - ex_field: 129- (可変長)
        - alert: 警報情報 (文字列のリスト)
        - disaster: 災害情報 (文字列のリスト)
        - latitude: 緯度 (数値)
        - longitude: 経度 (数値)
        - source_ip: 送信元IPアドレス (文字列)
    """
    
    # 可変長拡張フィールドの開始位置
    VARIABLE_FIELD_START = 128  # 基本フィールドの後から開始

    def __init__(self, *, ex_field: Optional[Dict[str, Any]] = None, **kwargs) -> None:
        """
        リクエストパケットの初期化
        
        Args:
            ex_field: 拡張フィールド辞書
            **kwargs: 基本フィールドのパラメータ
            
        Raises:
            BitFieldError: フィールド値が不正な場合
        """
        # 拡張フィールドの初期化
        self._ex_field = {} if ex_field is None else ex_field.copy()
        
        # 親クラスの初期化
        super().__init__(**kwargs)

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
            
            # ex_flagが設定されていれば拡張フィールドを解析
            if self.ex_flag == 1:
                ex_field_bits = extract_rest_bits(bitstr, self.VARIABLE_FIELD_START)
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
            
            # ex_fieldを設定（辞書から適切なビット列を生成）
            if self.ex_flag == 1 and self.ex_field:
                ex_field_bits = self._dict_to_ex_field_bits(self.ex_field)
                bitstr |= ex_field_bits << self.VARIABLE_FIELD_START
                
            return bitstr
            
        except BitFieldError:
            raise
        except Exception as e:
            raise BitFieldError("ビット列への変換中にエラー: {}".format(e))

    def as_dict(self) -> Dict[str, Any]:
        """
        全フィールドを辞書形式で返す
        
        Returns:
            フィールド名と値の辞書
        """
        result = super().as_dict()
        result['ex_field'] = self.ex_field
        return result
