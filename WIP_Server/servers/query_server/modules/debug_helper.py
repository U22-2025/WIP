"""
デバッグ支援クラス
デバッグ出力とパフォーマンス測定を担当
"""

import time
import threading
from .weather_constants import DebugConstants


class DebugHelper:
    """デバッグ支援クラス"""
    
    def __init__(self, debug_enabled=False):
        """
        初期化
        
        Args:
            debug_enabled: デバッグモードの有効/無効
        """
        self.debug_enabled = debug_enabled
    
    def _hex_dump(self, data):
        """
        バイナリデータのHEXダンプを作成
        
        Args:
            data: バイナリデータ
            
        Returns:
            str: HEXダンプ文字列
        """
        hex_str = ' '.join(f'{b:02x}' for b in data)
        ascii_str = ''.join(chr(b) if 32 <= b <= 126 else '.' for b in data)
        return f"Hex: {hex_str}\nASCII: {ascii_str}"
    
    def print_request_debug(self, data, parsed_request):
        """
        リクエストパケットのデバッグ情報を出力
        
        Args:
            data: 受信したバイナリデータ
            parsed_request: パースされたリクエスト
        """
        if not self.debug_enabled:
            return
        
        print(f"\n{DebugConstants.REQUEST_SEPARATOR}")
        print(f"Total Length: {len(data)} bytes")
        print("\nCoordinates:")
        print(f"{parsed_request.ex_field}")
        print("===========================\n")
    
    def print_response_debug(self, response_data):
        """
        レスポンスパケットのデバッグ情報を出力
        
        Args:
            response_data: レスポンスのバイナリデータ
        """
        if not self.debug_enabled:
            return
        
        print(f"\n{DebugConstants.RESPONSE_SEPARATOR}")
        print(f"Total Length: {len(response_data)} bytes")
        print(f"Response : {response_data}")
        print("============================\n")
    
    def print_timing_info(self, thread_id, addr, timing_data):
        """
        処理時間情報を出力
        
        Args:
            thread_id: スレッドID
            addr: クライアントアドレス
            timing_data: タイミングデータの辞書
        """
        if not self.debug_enabled:
            return
        
        print(f"\n{DebugConstants.TIMING_SEPARATOR}")
        print(f"[{thread_id}] Processing times for {addr}:")
        
        for key, value in timing_data.items():
            print(f"{key}: {value * DebugConstants.MS_MULTIPLIER:.2f}ms")
        
        print("========================\n")
    
    def print_thread_info(self, message, addr=None):
        """
        スレッド情報を出力
        
        Args:
            message: 出力メッセージ
            addr: クライアントアドレス（オプション）
        """
        if not self.debug_enabled:
            return
        
        thread_id = threading.current_thread().name
        if addr:
            print(f"[{thread_id}] {message} from {addr}")
        else:
            print(f"[{thread_id}] {message}")
    
    def print_error(self, message, addr=None, exception=None):
        """
        エラー情報を出力
        
        Args:
            message: エラーメッセージ
            addr: クライアントアドレス（オプション）
            exception: 例外オブジェクト（オプション）
        """
        thread_id = threading.current_thread().name
        error_msg = f"[{thread_id}] ERROR: {message}"
        
        if addr:
            error_msg += f" from {addr}"
        
        if exception:
            error_msg += f" - {exception}"
        
        print(error_msg)
    
    def print_info(self, message):
        """
        情報メッセージを出力
        
        Args:
            message: 情報メッセージ
        """
        if self.debug_enabled:
            print(f"INFO: {message}")


class PerformanceTimer:
    """パフォーマンス測定クラス"""
    
    def __init__(self):
        """初期化"""
        self.start_time = None
        self.timings = {}
    
    def start(self):
        """測定開始"""
        self.start_time = time.time()
        return self.start_time
    
    def mark(self, label):
        """
        特定のポイントの時間を記録
        
        Args:
            label: ラベル名
            
        Returns:
            float: 経過時間
        """
        if self.start_time is None:
            self.start()
        
        current_time = time.time()
        elapsed = current_time - self.start_time
        self.timings[label] = elapsed
        return elapsed
    
    def get_timing(self, label):
        """
        特定のラベルの時間を取得
        
        Args:
            label: ラベル名
            
        Returns:
            float: 経過時間
        """
        return self.timings.get(label, 0.0)
    
    def get_all_timings(self):
        """
        全ての測定時間を取得
        
        Returns:
            dict: 全ての測定時間
        """
        return self.timings.copy()
    
    def reset(self):
        """測定データをリセット"""
        self.start_time = None
        self.timings.clear()
