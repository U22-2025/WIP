"""
ビット操作のユーティリティ関数
"""
from .exceptions import BitFieldError


def extract_bits(bitstr: int, start: int, length: int) -> int:
    """
    指定したビット列(bitstr)から、startビット目（0始まり）からlengthビット分を取り出す
    
    Args:
        bitstr: 元のビット列
        start: 開始位置（0始まり）
        length: 取り出すビット長
        
    Returns:
        取り出されたビット値
        
    Examples:
        >>> extract_bits(0b110110, 1, 3)
        0b101
    """
    if length <= 0:
        raise BitFieldError(f"長さは正の整数である必要があります: {length}")
        
    mask = (1 << length) - 1
    return (bitstr >> start) & mask


def extract_rest_bits(bitstr: int, start: int) -> int:
    """
    指定したビット列(bitstr)から、startビット目（0始まり）以降の全てのビットを取り出す
    
    Args:
        bitstr: 元のビット列
        start: 開始位置（0始まり）
        
    Returns:
        取り出されたビット値
        
    Examples:
        >>> extract_rest_bits(0b110110, 2)
        0b110
    """
    return bitstr >> start
