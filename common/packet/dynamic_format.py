"""
動的フォーマット読み込みモジュール

JSONファイルからフィールド定義を読み込み辞書として返します。
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict

from .core.exceptions import BitFieldError

# フォーマット仕様ディレクトリ
_FORMAT_SPEC_DIR = Path(__file__).resolve().parent / "format_spec"


def _resolve_path(file_name: str | Path) -> Path:
    """内部利用: 相対パスの場合はformat_specディレクトリを基準に解決"""
    path = Path(file_name)
    if not path.is_absolute():
        path = _FORMAT_SPEC_DIR / path
    return path


def load_base_fields(file_name: str | Path = "request_fields.json") -> Dict[str, int]:
    """基本フィールド定義を読み込む

    Args:
        file_name: 読み込むJSONファイル名またはパス。相対パスの場合は
            ``format_spec/`` を基準とします。

    Returns:
        フィールド名をキー、ビット長を値とする辞書

    Raises:
        BitFieldError: ファイルの読み込みまたはJSON解析に失敗した場合
    """
    path = _resolve_path(file_name)
    try:
        with open(path, "r", encoding="utf-8") as fp:
            data = json.load(fp)
        if not isinstance(data, dict):
            raise ValueError("JSONデータが辞書ではありません")
        return {str(k): int(v) for k, v in data.items()}
    except Exception as e:  # noqa: BLE001
        raise BitFieldError(
            f"基本フィールド定義の読み込みに失敗: {e}"
        ) from e


def reload_base_fields(file_name: str | Path = "request_fields.json") -> Dict[str, int]:
    """基本フィールド定義を再読み込みする"""
    return load_base_fields(file_name)


def load_extended_fields(file_name: str | Path = "extended_fields.json") -> Dict[str, int]:
    """拡張フィールド定義を読み込む

    Args:
        file_name: 読み込むJSONファイル名またはパス。相対パスの場合は
            ``format_spec/`` を基準とします。

    Returns:
        フィールド名をキー、ビット長を値とする辞書

    Raises:
        BitFieldError: ファイルの読み込みまたはJSON解析に失敗した場合
    """
    path = _resolve_path(file_name)
    try:
        with open(path, "r", encoding="utf-8") as fp:
            data = json.load(fp)
        if not isinstance(data, dict):
            raise ValueError("JSONデータが辞書ではありません")
        return {str(k): int(v) for k, v in data.items()}
    except Exception as e:  # noqa: BLE001
        raise BitFieldError(
            f"拡張フィールド定義の読み込みに失敗: {e}"
        ) from e


def load_response_fields(file_name: str | Path = "response_fields.json") -> Dict[str, int]:
    """レスポンスフィールド定義を読み込む

    Args:
        file_name: 読み込むJSONファイル名またはパス。相対パスの場合は
            ``format_spec/`` を基準とします。

    Returns:
        フィールド名をキー、ビット長を値とする辞書

    Raises:
        BitFieldError: ファイルの読み込みまたはJSON解析に失敗した場合
    """
    path = _resolve_path(file_name)
    try:
        with open(path, "r", encoding="utf-8") as fp:
            data = json.load(fp)
        if not isinstance(data, dict):
            raise ValueError("JSONデータが辞書ではありません")
        return {str(k): int(v) for k, v in data.items()}
    except Exception as e:  # noqa: BLE001
        raise BitFieldError(
            f"レスポンスフィールド定義の読み込みに失敗: {e}"
        ) from e
