"""
基底サーバークラス
UDPサーバーの共通機能を提供する抽象基底クラス
"""

import socket
import time
import threading
import concurrent.futures
import os
from abc import ABC, abstractmethod
from dotenv import load_dotenv


class BaseServer(ABC):
    """UDPサーバーの基底クラス"""
    
    def __init__(self, host='localhost', port=4000, debug=False, max_workers=None):
        """
        初期化
        
        Args:
            host: サーバーホスト
            port: サーバーポート
            debug: デバッグモードフラグ
            max_workers: スレッドプールのワーカー数（Noneの場合はCPU数*2）
        """
        # 環境変数を読み込む
        load_dotenv()
        
        self.host = host
        self.port = port
        self.debug = debug
        
        # サーバー情報（派生クラスでオーバーライド可能）
        self.server_name = self.__class__.__name__
        self.version = int(os.getenv('PROTOCOL_VERSION', 1))
        
        # 並列処理設定
        self.max_workers = max_workers
        self.thread_pool = None
        self._init_thread_pool()
        
        # ソケット初期化
        self.sock = None
        self._init_socket()
        
        # 統計情報
        self.request_count = 0
        self.error_count = 0
        self.start_time = None
        self.lock = threading.Lock()  # 統計情報の同期用
    
    def _init_thread_pool(self):
        """スレッドプールの初期化"""
        if self.max_workers is None:
            # デフォルトはCPU数の2倍
            import os
            self.max_workers = (os.cpu_count() or 1) * 2
        
        self.thread_pool = concurrent.futures.ThreadPoolExecutor(
            max_workers=self.max_workers,
            thread_name_prefix=f"{self.server_name}_Worker"
        )
        
        if self.debug:
            print(f"Initialized thread pool with {self.max_workers} workers")
    
    def _init_socket(self):
        """UDPソケットの初期化"""
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock.bind((self.host, self.port))
        except Exception as e:
            print(f"Failed to initialize socket: {e}")
            raise
    
    def _hex_dump(self, data):
        """バイナリデータのhexダンプを作成"""
        hex_str = ' '.join(f'{b:02x}' for b in data)
        ascii_str = ''.join(chr(b) if 32 <= b <= 126 else '.' for b in data)
        return f"Hex: {hex_str}\nASCII: {ascii_str}"
    
    def _debug_print(self, title, message, data=None):
        """デバッグ情報を出力"""
        if not self.debug:
            return
            
        thread_name = threading.current_thread().name
        print(f"\n[{thread_name}] === {title} ===")
        print(message)
        if data:
            print("\nRaw Data:")
            print(self._hex_dump(data))
        print("=" * (len(title) + 8))
        print()
    
    def _debug_print_request(self, data, parsed):
        """リクエストのデバッグ情報を出力（派生クラスでオーバーライド可能）"""
        self._debug_print(
            "RECEIVED REQUEST PACKET",
            f"Total Length: {len(data)} bytes\nFrom: {getattr(parsed, 'addr', 'Unknown')}",
            data
        )
    
    def _debug_print_response(self, response, request=None):
        """レスポンスのデバッグ情報を出力（派生クラスでオーバーライド可能）"""
        self._debug_print(
            "SENDING RESPONSE PACKET",
            f"Total Length: {len(response)} bytes",
            response
        )
    
    def _measure_time(self, func, *args, **kwargs):
        """関数の実行時間を計測"""
        start_time = time.time()
        result = func(*args, **kwargs)
        elapsed_time = time.time() - start_time
        return result, elapsed_time
    
    @abstractmethod
    def parse_request(self, data):
        """
        リクエストデータをパース（派生クラスで実装）
        
        Args:
            data: 受信したバイナリデータ
            
        Returns:
            パースされたリクエストオブジェクト
        """
        pass
    
    @abstractmethod
    def create_response(self, request):
        """
        レスポンスを作成（派生クラスで実装）
        
        Args:
            request: リクエストオブジェクト
            
        Returns:
            レスポンスのバイナリデータ
        """
        pass
    
    def validate_request(self, request):
        """
        リクエストの妥当性をチェック（派生クラスでオーバーライド可能）
        
        Args:
            request: リクエストオブジェクト
            
        Returns:
            tuple: (is_valid, error_message)
        """
        return True, None
    
    def handle_request(self, data, addr):
        """
        リクエストを処理（ワーカースレッドで実行）
        
        Args:
            data: 受信したバイナリデータ
            addr: 送信元アドレス
        """
        timing_info = {}
        start_time = time.time()
        
        try:
            # リクエストカウントを増加（スレッドセーフ）
            with self.lock:
                self.request_count += 1
            
            # リクエストをパース
            request, parse_time = self._measure_time(self.parse_request, data)
            timing_info['parse'] = parse_time
            
            # デバッグ出力
            self._debug_print_request(data, request)
            
            # リクエストの妥当性をチェック
            is_valid, error_msg = self.validate_request(request)
            if not is_valid:
                with self.lock:
                    self.error_count += 1
                if self.debug:
                    print(f"[{threading.current_thread().name}] Invalid request from {addr}: {error_msg}")
                return
            
            # レスポンスを作成
            response, response_time = self._measure_time(self.create_response, request)
            timing_info['response'] = response_time
            
            # デバッグ出力
            self._debug_print_response(response, request)
            
            # レスポンスを送信
            send_start = time.time()
            self.sock.sendto(response, addr)
            timing_info['send'] = time.time() - send_start
            
            # 合計処理時間
            timing_info['total'] = time.time() - start_time
            
            # タイミング情報を出力
            if self.debug:
                self._print_timing_info(addr, timing_info)
            
            if self.debug:
                print(f"[{threading.current_thread().name}] Successfully sent response to {addr}")
                
        except Exception as e:
            with self.lock:
                self.error_count += 1
            print(f"[{threading.current_thread().name}] Error processing request from {addr}: {e}")
            if self.debug:
                import traceback
                traceback.print_exc()
    
    def _print_timing_info(self, addr, timing_info):
        """タイミング情報を出力"""
        thread_name = threading.current_thread().name
        print(f"\n[{thread_name}] === TIMING INFORMATION for {addr} ===")
        print(f"Request parsing time: {timing_info.get('parse', 0)*1000:.2f}ms")
        print(f"Response creation time: {timing_info.get('response', 0)*1000:.2f}ms")
        print(f"Response send time: {timing_info.get('send', 0)*1000:.2f}ms")
        print(f"Total processing time: {timing_info.get('total', 0)*1000:.2f}ms")
        print("=" * 50)
        print()
    
    def print_statistics(self):
        """統計情報を出力"""
        if self.start_time:
            uptime = time.time() - self.start_time
            with self.lock:
                total_requests = self.request_count
                total_errors = self.error_count
            
            print(f"\n=== {self.server_name} STATISTICS ===")
            print(f"Uptime: {uptime:.2f} seconds")
            print(f"Total requests: {total_requests}")
            print(f"Total errors: {total_errors}")
            print(f"Success rate: {(1 - total_errors/max(total_requests, 1))*100:.2f}%")
            print(f"Thread pool workers: {self.max_workers}")
            print("=================================\n")
    
    def send_udp_packet(self, data, host, port):
        """
        メインソケットを使用してUDPパケットを送信
        
        Args:
            data: 送信するバイナリデータ
            host: 送信先ホスト
            port: 送信先ポート
            
        Returns:
            int: 送信したバイト数
        """
        try:
            bytes_sent = self.sock.sendto(data, (host, port))
            if self.debug:
                print(f"[{self.server_name}] Sent {bytes_sent} bytes to {host}:{port} from port {self.port}")
            return bytes_sent
        except Exception as e:
            print(f"[{self.server_name}] Error sending packet to {host}:{port}: {e}")
            if self.debug:
                import traceback
                traceback.print_exc()
            raise
    
    def run(self):
        """サーバーを開始（並列処理対応）"""
        print(f"{self.server_name} running on {self.host}:{self.port}")
        print(f"Parallel processing enabled with {self.max_workers} worker threads")
        if self.debug:
            print("Debug mode enabled")
        
        self.start_time = time.time()
        
        # バッファサイズを環境変数から取得
        buffer_size = int(os.getenv('UDP_BUFFER_SIZE', 4096))
        
        try:
            while True:
                try:
                    # リクエストを受信
                    data, addr = self.sock.recvfrom(buffer_size)
                    
                    if self.debug:
                        print(f"\n[Main] Received request from {addr}, submitting to worker pool")
                    
                    # スレッドプールにリクエスト処理を投入
                    self.thread_pool.submit(self.handle_request, data, addr)
                    
                except socket.timeout:
                    # タイムアウトは正常な動作
                    continue
                except socket.error as e:
                    # Windows特有のエラー処理
                    if hasattr(e, 'winerror') and e.winerror == 10054:
                        # WSAECONNRESET - クライアントが接続を切断
                        # UDPでは正常な動作なので無視
                        if self.debug:
                            print(f"[Main] Client disconnected (ignored): {e}")
                        continue
                    else:
                        print(f"[Main] Socket error: {e}")
                        continue
                except Exception as e:
                    print(f"[Main] Error receiving request: {e}")
                    continue
                    
        except KeyboardInterrupt:
            print(f"\n{self.server_name} shutting down...")
            self.shutdown()
        except Exception as e:
            print(f"[Main] Fatal error in main loop: {e}")
            self.shutdown()
    
    def shutdown(self):
        """サーバーを適切にシャットダウン"""
        print("Shutting down server...")
        
        # スレッドプールをシャットダウン
        if self.thread_pool:
            print("Shutting down thread pool...")
            self.thread_pool.shutdown(wait=True)
            print("Thread pool shutdown complete.")
        
        # 統計情報を出力
        self.print_statistics()
        
        # ソケットを閉じる
        if self.sock:
            print("Closing socket...")
            self.sock.close()
            
        # 派生クラス固有のクリーンアップ
        self._cleanup()
        
        print("Server shutdown complete.")
    
    def _cleanup(self):
        """派生クラス固有のクリーンアップ処理（オーバーライド可能）"""
        pass
