"""
リクエストパケット
"""
from typing import Optional, Dict, Any
from .exceptions import BitFieldError
from .format_base import FormatBase
from .extended_field import ExtendedField
from .bit_utils import extract_rest_bits


class Request(FormatBase):
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
        # 拡張フィールドの初期化（ExtendedFieldオブジェクトとして作成）
        self._ex_field = ExtendedField(ex_field)
        
        # 親クラスの初期化
        super().__init__(**kwargs)
        
        # ex_fieldの変更を監視してチェックサムを再計算
        self._ex_field.add_observer(self._on_ex_field_changed)

    def _on_ex_field_changed(self) -> None:
        """拡張フィールドが変更された時のコールバック"""
        if hasattr(self, '_auto_checksum') and self._auto_checksum:
            self._recalculate_checksum()

    @property
    def ex_field(self) -> ExtendedField:
        """拡張フィールドのプロパティ（ExtendedFieldオブジェクトを返す）"""
        return self._ex_field

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
                if ex_field_bits:
                    # 総ビット長を計算（_total_bitsが設定されていれば使用）
                    ex_field_total_bits = getattr(self, '_total_bits', None)
                    if ex_field_total_bits:
                        ex_field_total_bits = ex_field_total_bits - self.VARIABLE_FIELD_START
                        self._ex_field = ExtendedField.from_bits(ex_field_bits, ex_field_total_bits)
                    else:
                        # _total_bitsが設定されていない場合はビット長から推定
                        self._ex_field = ExtendedField.from_bits(ex_field_bits)
                    
                    # 新しいex_fieldの変更を監視
                    self._ex_field.add_observer(self._on_ex_field_changed)
                
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
            
            # ex_fieldを設定（ExtendedFieldオブジェクトからビット列を生成）
            if self.ex_flag == 1 and self._ex_field.to_dict():
                ex_field_bits = self._ex_field.to_bits()
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
        result['ex_field'] = self._ex_field.to_dict()
        return result
