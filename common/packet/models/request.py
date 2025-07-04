"""
リクエストパケット
"""
from typing import Optional, Dict, Any, Union
from ..core.exceptions import BitFieldError
from ..core.format_base import FormatBase
from ..core.extended_field import ExtendedField
from ..core.bit_utils import extract_rest_bits


class Request(FormatBase):
    """
    リクエストパケット
    
    拡張フィールド:
    - ex_field: 129- (可変長)
        - alert: 警報情報 (文字列のリスト)
        - disaster: 災害情報 (文字列のリスト)
        - latitude: 緯度 (数値)
        - longitude: 経度 (数値)
        - source: 送信元情報 (ip, port) のタプル
    """

    def get_coordinates(self) -> Optional[tuple[float, float]]:
        """
        拡張フィールドから緯度経度を取得する
        
        Returns:
            緯度経度のタプル (latitude, longitude)、存在しない場合はNone
        """
        ex_dict = self.ex_field.to_dict()
        if 'latitude' in ex_dict and 'longitude' in ex_dict:
            return (float(ex_dict['latitude']), float(ex_dict['longitude']))
        return None
    
    # 可変長拡張フィールドの開始位置
    VARIABLE_FIELD_START = sum(FormatBase.FIELD_LENGTH.values())

    @classmethod
    def reload_request_spec(cls) -> None:
        """基本フィールド定義変更時に開始位置を再計算する"""
        cls.VARIABLE_FIELD_START = sum(FormatBase.FIELD_LENGTH.values())

    def get_min_packet_size(self) -> int:
        """
        リクエストパケットの最小サイズを取得する

        Returns:
            最小パケットサイズ（バイト） - 基本フィールドのみ
        """
        return super().get_min_packet_size()

    def __init__(self, *, ex_field: Optional[Union[Dict[str, Any], ExtendedField]] = None, **kwargs) -> None:
        """
        リクエストパケットの初期化
        
        Args:
            ex_field: 拡張フィールド（辞書またはExtendedFieldオブジェクト）
            **kwargs: 基本フィールドのパラメータと拡張フィールドのパラメータ
            
        Raises:
            BitFieldError: フィールド値が不正な場合
        """
        # 拡張フィールド用のパラメータを抽出
        ex_field_params = {}
        base_kwargs = {}
        for key, value in kwargs.items():
            if key in ['source', 'alert', 'disaster', 'latitude', 'longitude']:
                ex_field_params[key] = value
            else:
                base_kwargs[key] = value
        
        # 拡張フィールドの初期化
        if isinstance(ex_field, dict):
            ex_field_params.update(ex_field)
            self._ex_field = ExtendedField(ex_field_params)
        elif isinstance(ex_field, ExtendedField):
            self._ex_field = ex_field
            for key, value in ex_field_params.items():
                self._ex_field[key] = value
        else:
            self._ex_field = ExtendedField(ex_field_params)
        
        # 親クラスの初期化
        super().__init__(**base_kwargs)
        
        # 拡張フィールドの変更を監視してチェックサムを再計算
        self._ex_field.add_observer(self._on_ex_field_changed)

    def _on_ex_field_changed(self) -> None:
        """拡張フィールドが変更されたときの処理"""
        if hasattr(self, '_auto_checksum') and self._auto_checksum:
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
        # ExtendedFieldオブジェクトを辞書形式で追加
        result['ex_field'] = self._ex_field.to_dict()
        return result
