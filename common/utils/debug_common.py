"""
共通デバッグユーティリティ
"""

def debug_print(message, prefix="[DEBUG]"):
    """
    デバッグメッセージを出力
    
    Args:
        message: 出力するメッセージ
        prefix: メッセージのプレフィックス
    """
    print(f"{prefix} {message}")


def debug_hex(data, max_len=None):
    """
    バイナリデータを16進数形式で出力
    
    Args:
        data: バイナリデータ
        max_len: 表示する最大バイト数
        
    Returns:
        str: 16進数文字列
    """
    if max_len and len(data) > max_len:
        data = data[:max_len]
        truncated = True
    else:
        truncated = False
        
    hex_str = ' '.join(f'{b:02x}' for b in data)
    
    if truncated:
        hex_str += " ..."
        
    return hex_str


def debug_packet(packet, title="Packet"):
    """
    パケット情報をデバッグ出力
    
    Args:
        packet: パケットオブジェクト
        title: タイトル
    """
    print(f"\n=== {title} ===")
    print(f"Version: {packet.version}")
    print(f"Type: {packet.type}")
    print(f"Packet ID: {packet.packet_id}")
    print(f"Area Code: {packet.area_code}")
    
    if hasattr(packet, 'ex_field') and packet.ex_field:
        print(f"Extended Field: {packet.ex_field.to_dict()}")
        
    print("================\n")
