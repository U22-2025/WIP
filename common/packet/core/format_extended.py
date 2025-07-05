"""
パケットフォーマットの拡張フィールド処理（統合版）
拡張フィールドの構造を定義し、ビット操作のユーティリティを提供します
"""
from typing import Optional, Dict, Any, Union
from .exceptions import BitFieldError
from .bit_utils import extract_rest_bits
from .format_base import FormatBase
from .extended_field import ExtendedField


class FormatExtended(FormatBase):
    """
    パケットフォーマットの拡張フィールド処理クラス
    拡張フィールドの構造を定義し、ビット操作のユーティリティを提供します
    """

    def __init__(self, *, ex_field: Optional[Union[Dict[str, Any], ExtendedField]] = None, **kwargs) -> None:
        """
        拡張フィールドを含むパケットの初期化
        
        Args:
            ex_field: 拡張フィールド（辞書またはExtendedFieldオブジェクト）
            **kwargs: 基本フィールドのパラメータ
            
        Raises:
            BitFieldError: フィールド値が不正な場合
        """
        # 拡張フィールドの初期化
        if isinstance(ex_field, dict):
            self._ex_field = ExtendedField(ex_field)
        elif isinstance(ex_field, ExtendedField):
            self._ex_field = ex_field
        else:
            self._ex_field = ExtendedField()
        
        # 親クラスの初期化
        super().__init__(**kwargs)
        
        # 拡張フィールドの変更を監視してチェックサムを再計算
        self._ex_field.add_observer(self._on_ex_field_changed)

    def _on_ex_field_changed(self) -> None:
        """拡張フィールドが変更されたときの処理"""
        if self._auto_checksum:
            self._recalculate_checksum()

    @property
    def ex_field(self) -> ExtendedField:
        """拡張フィールドのプロパティ"""
        return self._ex_field
    
    @ex_field.setter
    def ex_field(self, value: Union[Dict[str, Any], ExtendedField]) -> None:
        """拡張フィールドの設定"""
        # 既存のオブザーバーを削除
        self._ex_field.remove_observer(self._on_ex_field_changed)
        
        # 新しい拡張フィールドを設定
        if isinstance(value, dict):
            self._ex_field = ExtendedField(value)
        elif isinstance(value, ExtendedField):
            self._ex_field = value
        else:
            self._ex_field = ExtendedField()
        
        # 新しいオブザーバーを追加
        self._ex_field.add_observer(self._on_ex_field_changed)
        
        # チェックサムを再計算
        self._on_ex_field_changed()

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
                ex_field_start = max(pos + size for field, (pos, size) in self._BIT_FIELDS.items())
                ex_field_bits = extract_rest_bits(bitstr, ex_field_start)
                
                # 元のビット列の長さから拡張フィールドの正確なビット長を計算
                total_bitstr_length = bitstr.bit_length()
                if total_bitstr_length > ex_field_start:
                    ex_field_total_bits = total_bitstr_length - ex_field_start
                    # ExtendedFieldクラスのfrom_bitsメソッドを使用
                    self._ex_field = ExtendedField.from_bits(ex_field_bits, ex_field_total_bits)
                else:
                    self._ex_field = ExtendedField.from_bits(ex_field_bits)
                
                # オブザーバーを追加
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
            
            # ex_fieldを設定（ExtendedFieldオブジェクトのto_bitsメソッドを使用）
            if self.ex_flag == 1 and self._ex_field and self._ex_field.to_dict():
                ex_field_start = max(pos + size for field, (pos, size) in self._BIT_FIELDS.items())
                ex_field_bits = self._ex_field.to_bits()
                bitstr |= ex_field_bits << ex_field_start
                
            return bitstr
            
        except BitFieldError:
            raise
        except Exception as e:
            raise BitFieldError("ビット列への変換中にエラー: {}".format(e))

    def to_bytes(self) -> bytes:
        """基底クラスの ``to_bytes()`` を利用してバイト列を取得する"""
        return super().to_bytes()

    def as_dict(self) -> Dict[str, Any]:
        """
        全フィールドを辞書形式で返す
        
        Returns:
            フィールド名と値の辞書
        """
        result = super().as_dict()
        # ExtendedFieldオブジェクトを辞書形式で追加
        result['ex_field'] = self._ex_field.to_dict()
        return result
