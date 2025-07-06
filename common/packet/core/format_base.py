"""
パケットフォーマットの基底クラス（修正版）
共通ヘッダー部分の構造を定義し、ビット操作の基本機能を提供します
"""
from typing import Optional, Union, Dict, Any
from pathlib import Path
from ..dynamic_format import load_base_fields, reload_base_fields
from .exceptions import BitFieldError
from .bit_utils import extract_bits
from ...utils.auth import WIPAuth
from datetime import datetime


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
    - request_auth:     29bit    (1ビット)
    - response_auth:    30bit    (1ビット)
    - reserved:         31-32bit (2ビット)
    - timestamp:        33-96bit (64ビット)
    - area_code:        97-116bit (20ビット)
    - checksum:         117-128bit (12ビット)
    """
    
    # JSON定義からフィールド仕様を動的に読み込む
    FIELD_SPEC = load_base_fields()
    FIELD_LENGTH = {k: v["length"] for k, v in FIELD_SPEC.items()}
    FIELD_TYPE = {k: v.get("type", "int") for k, v in FIELD_SPEC.items()}

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

    # 初期ロード時にプロパティを生成
    # （メソッド定義後に実行するためプレースホルダ。実際の呼び出しはクラス定義末尾で行う）

    @classmethod
    def _generate_properties(cls) -> None:
        """FIELD_LENGTH に基づきプロパティを動的に生成する"""
        for field in cls.FIELD_LENGTH:
            if field == "area_code":
                def getter(self, *, _f=field):
                    area_code_int = getattr(self, f"_{_f}", 0)
                    return f"{area_code_int:06d}"

                def setter(self, value: Union[int, str], *, _f=field) -> None:
                    if isinstance(value, str):
                        try:
                            area_code_int = int(value)
                        except ValueError:
                            raise BitFieldError(
                                f"エリアコード '{value}' は有効な数値ではありません"
                            )
                    elif isinstance(value, (int, float)):
                        area_code_int = int(value)
                    else:
                        raise BitFieldError(
                            f"エリアコードは文字列または数値である必要があります。受け取った型: {type(value)}"
                        )
                    area_len = cls.FIELD_LENGTH.get("area_code", 20)
                    max_area = (1 << area_len) - 1
                    if not (0 <= area_code_int <= max_area):
                        raise BitFieldError(
                            f"エリアコード {area_code_int} が{area_len}ビットの範囲（0-{max_area}）を超えています"
                        )
                    self._set_validated_field(_f, area_code_int)

            else:
                def getter(self, *, _f=field):
                    return getattr(self, f"_{_f}", 0)

                def setter(self, value: Union[int, float], *, _f=field) -> None:
                    self._set_validated_field(_f, value)

            setattr(cls, field, property(getter, setter))

    @classmethod
    def reload_field_spec(cls, file_name: str | Path = "request_fields.json") -> None:
        """JSON定義を再読み込みしてフィールド仕様を更新する"""
        old_fields = set(cls.FIELD_LENGTH)
        cls.FIELD_SPEC = reload_base_fields(file_name)
        cls.FIELD_LENGTH = {k: v["length"] for k, v in cls.FIELD_SPEC.items()}
        cls.FIELD_TYPE = {k: v.get("type", "int") for k, v in cls.FIELD_SPEC.items()}
        new_fields = set(cls.FIELD_LENGTH)

        cls.FIELD_POSITION = {}
        current_pos = 0
        for field, length in cls.FIELD_LENGTH.items():
            cls.FIELD_POSITION[field] = current_pos
            current_pos += length

        cls._BIT_FIELDS = {
            field: (pos, cls.FIELD_LENGTH[field])
            for field, pos in cls.FIELD_POSITION.items()
        }

        cls._FIELD_RANGES = {
            field: (0, (1 << length) - 1)
            for field, length in cls.FIELD_LENGTH.items()
        }

        removed = old_fields - new_fields
        for field in removed:
            if hasattr(cls, field):
                delattr(cls, field)

        cls._generate_properties()

    def __init__(self, *, bitstr: Optional[int] = None, **kwargs) -> None:
        """
        共通フィールドの初期化。すべてのフィールドはJSON定義に基づき ``kwargs``
        で指定します。

        Args:
            bitstr: ビット列からの変換用
            **kwargs: フィールド名と値のペア
            
        Raises:
            BitFieldError: フィールド値が不正な場合
        """
        try:
            # チェックサム自動計算フラグ
            self._auto_checksum = True

            
            # 認証機能の設定
            self._auth_enabled = False
            self._auth_passphrase = None
            
            # ビット列が提供された場合はそれを解析
            if bitstr is not None:
                self.from_bits(bitstr)
                return

            # フィールドの初期化と検証
            remaining = dict(kwargs)
            for field in self.FIELD_LENGTH:
                value = remaining.pop(field, 0)
                self._set_validated_field(field, value)

            if remaining:
                raise BitFieldError(f"未知のフィールド: {', '.join(remaining.keys())}")
                
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
        cls = self.__class__
        return sum(cls.FIELD_LENGTH.values()) // 8

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

        # from_bits中の不要なチェックサム再計算を防ぐため一時的に無効化
        instance._auto_checksum = False

        # パケット全体のビット長を保存
        instance._total_bits = len(data) * 8

        # from_bitsを手動で呼び出す（_total_bitsが設定された後）
        instance.from_bits(bitstr)

        # チェックサム自動計算を再有効化
        instance._auto_checksum = True
        
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
        total = 0
        
        # 1バイトずつ加算
        for byte in data:
            total += byte
            
        # キャリーを12ビットに折り返し
        while total >> 12:
            total = (total & 0xFFF) + (total >> 12)
            
        # 1の補数を返す（12ビットマスク）
        checksum = (~total) & 0xFFF
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

    # ===================================================================
    # 認証機能
    # ===================================================================

    def enable_auth(self, passphrase: str) -> None:
        """
        認証機能を有効にする
        
        Args:
            passphrase: 認証用パスフレーズ
        """
        self._auth_enabled = True
        self._auth_passphrase = passphrase

    def disable_auth(self) -> None:
        """
        認証機能を無効にする
        """
        self._auth_enabled = False
        self._auth_passphrase = None

    def is_auth_enabled(self) -> bool:
        """
        認証機能が有効かどうかを確認
        
        Returns:
            認証機能が有効な場合True
        """
        return getattr(self, '_auth_enabled', False)

    def get_auth_passphrase(self) -> Optional[str]:
        """
        認証用パスフレーズを取得
        
        Returns:
            パスフレーズまたはNone
        """
        return getattr(self, '_auth_passphrase', None)

    def calculate_auth_hash(self) -> Optional[bytes]:
        """
        認証ハッシュを計算する
        
        Returns:
            16バイトのMD5ハッシュまたはNone（認証無効時）
        """
        if not self.is_auth_enabled() or not self._auth_passphrase:
            return None
        
        return WIPAuth.calculate_auth_hash(
            self.packet_id,
            self.timestamp,
            self._auth_passphrase
        )

    def verify_auth_hash(self, auth_hash: bytes) -> bool:
        """
        認証ハッシュを検証する
        
        Args:
            auth_hash: 検証する16バイトのMD5ハッシュ
            
        Returns:
            検証に成功した場合True
        """
        if not self.is_auth_enabled() or not self._auth_passphrase:
            return False
        
        return WIPAuth.verify_auth_hash(
            self.packet_id,
            self.timestamp,
            self._auth_passphrase,
            auth_hash
        )

    def add_auth_to_extended_field(self) -> None:
        """
        認証ハッシュを拡張フィールドに追加する
        認証が有効な場合のみ実行
        """
        if not self.is_auth_enabled():
            return

        # 拡張フィールドが存在しない場合は作成
        if not hasattr(self, 'ex_field') or not self.ex_field:
            from .extended_field import ExtendedField
            self.ex_field = ExtendedField()

        auth_hash = self.calculate_auth_hash()
        if auth_hash:
            self.ex_field.auth_hash = auth_hash
            self.ex_flag = 1

    def verify_auth_from_extended_field(self) -> bool:
        """
        拡張フィールドから認証ハッシュを取得して検証する
        
        Returns:
            検証に成功した場合True（認証無効時はTrue）
        """
        if not self.is_auth_enabled():
            return True  # 認証無効時は常に成功

        # 拡張フィールドが存在し、認証ハッシュが設定されている場合のみ検証
        if hasattr(self, 'ex_field') and self.ex_field and self.ex_field.auth_hash:
            return self.verify_auth_hash(self.ex_field.auth_hash)
        
        return False  # 認証有効だが認証ハッシュが無い場合は失敗


# クラス定義後にプロパティを生成
FormatBase._generate_properties()
