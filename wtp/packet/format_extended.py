"""
パケットフォーマットの拡張フィールド処理
拡張フィールドの構造を定義し、ビット操作のユーティリティを提供します
"""
from typing import Optional, Dict, Any
from .exceptions import BitFieldError
from .bit_utils import extract_rest_bits
from .format_base import FormatBase
from .extended_field_mixin import ExtendedFieldMixin


class FormatExtended(FormatBase, ExtendedFieldMixin):
    """
    パケットフォーマットの拡張フィールド処理クラス
    拡張フィールドの構造を定義し、ビット操作のユーティリティを提供します
    """

    def __init__(self, *, ex_field: Optional[Dict[str, Any]] = None, **kwargs) -> None:
        """
        拡張フィールドを含むパケットの初期化
        
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
                ex_field_start = max(pos + size for field, (pos, size) in self._BIT_FIELDS.items())
                ex_field_bits = extract_rest_bits(bitstr, ex_field_start)
                # 元のビット列の長さから拡張フィールドの正確なビット長を計算
                total_bitstr_length = bitstr.bit_length()
                if total_bitstr_length > ex_field_start:
                    ex_field_total_bits = total_bitstr_length - ex_field_start
                    self.fetch_ex_field(ex_field_bits, ex_field_total_bits)
                else:
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
                ex_field_start = max(pos + size for field, (pos, size) in self._BIT_FIELDS.items())
                ex_field_bits = self._dict_to_ex_field_bits(self.ex_field)
                bitstr |= ex_field_bits << ex_field_start
                
            return bitstr
            
        except BitFieldError:
            raise
        except Exception as e:
            raise BitFieldError("ビット列への変換中にエラー: {}".format(e))

    def to_bytes(self) -> bytes:
        """
        ビット列をバイト列に変換する
        
        基本フィールドと拡張フィールドを含むすべてのデータをバイト列に変換します。
        バイト列の長さは以下のように計算されます：
        1. 基本フィールド: 最低32バイト（256ビット）
        2. 拡張フィールド（存在する場合）:
           - 各フィールドのヘッダー: 3バイト（24ビット）
           - 文字列データ: UTF-8エンコード後のバイト数
           - 数値データ: 必要最小限のバイト数
        
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
            
            # 基本バイト数を計算（最低32バイト = 256ビット）
            num_bytes = max((bitstr.bit_length() + 7) // 8, 32)
            
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
        result['ex_field'] = self.ex_field
        return result
