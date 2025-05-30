"""
パケットフォーマットの拡張フィールド処理（修正版）
拡張フィールドの構造を定義し、ビット操作のユーティリティを提供します
"""
from typing import Optional, Dict, Any
from .exceptions import BitFieldError
from .bit_utils import extract_rest_bits
from .format_base import FormatBase
from .extended_field import ExtendedField


class FormatExtended(FormatBase):
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
                ex_field_start = max(pos + size for field, (pos, size) in self._BIT_FIELDS.items())
                ex_field_bits = extract_rest_bits(bitstr, ex_field_start)
                # 元のビット列の長さから拡張フィールドの正確なビット長を計算
                total_bitstr_length = bitstr.bit_length()
                if total_bitstr_length > ex_field_start:
                    ex_field_total_bits = total_bitstr_length - ex_field_start
                    self._ex_field = ExtendedField.from_bits(ex_field_bits, ex_field_total_bits)
                else:
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
                ex_field_start = max(pos + size for field, (pos, size) in self._BIT_FIELDS.items())
                ex_field_bits = self._ex_field.to_bits()
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
            if self.ex_flag == 1:
                ex_dict = self._ex_field.to_dict()
                if ex_dict:
                    # ヘッダー用のバイト数（各フィールドに24ビット = 3バイト）
                    num_bytes += len(ex_dict) * 3
                    
                    # 各値のバイト数を計算
                    for value in ex_dict.values():
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
            
            # 必要なバイト数を計算
            required_bytes = (bitstr.bit_length() + 7) // 8
            
            # リトルエンディアンでバイト列に変換
            if required_bytes > 0:
                bytes_data = bitstr.to_bytes(required_bytes, byteorder='little')
            else:
                bytes_data = b''
            
            # 最低必要バイト数にパディング（右側を0で埋める）
            if len(bytes_data) < num_bytes:
                bytes_data = bytes_data + b'\x00' * (num_bytes - len(bytes_data))
            
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
            
            # 最低必要バイト数にパディング
            if len(final_bytes) < num_bytes:
                final_bytes = final_bytes + b'\x00' * (num_bytes - len(final_bytes))
            
            return final_bytes
            
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
        result['ex_field'] = self._ex_field.to_dict()
        return result
