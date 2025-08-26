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
from WIPCommonPy.utils.log_config import UnifiedLogFormatter

try:
    from dotenv import load_dotenv

    _DOTENV_AVAILABLE = True
except ImportError:
    _DOTENV_AVAILABLE = False

    def load_dotenv():
        pass


import traceback
from WIPCommonPy.packet import ErrorResponse
from WIPCommonPy.packet import Format


class BaseServer(ABC):
    """UDPサーバーの基底クラス"""

    def __init__(self, host="localhost", port=4000, debug=False, max_workers=None):
        """
        初期化

        Args:
            host: サーバーホスト
            port: サーバーポート (1-65535の範囲)
            debug: デバッグモードフラグ
            max_workers: スレッドプールのワーカー数（Noneの場合はCPU数*2）

        Raises:
            ValueError: ポート番号が無効な場合
        """
        if not (1 <= port <= 65535):
            raise ValueError(f"Invalid port number: {port}. Must be between 1-65535")
        # 環境変数を読み込む（dotenvが利用可能な場合のみ）
        if _DOTENV_AVAILABLE:
            load_dotenv()

        self.host = host
        self.port = port
        self.debug = debug

        # サーバー情報（派生クラスでオーバーライド可能）
        self.server_name = self.__class__.__name__
        self.version = int(os.getenv("PROTOCOL_VERSION", 1))

        # 認証設定の初期化（派生クラスでオーバーライド可能）
        self.auth_enabled = False
        self.auth_passphrase = ""
        self.request_auth_enabled = False

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
            thread_name_prefix=f"{self.server_name}_Worker",
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
        hex_str = " ".join(f"{b:02x}" for b in data)
        ascii_str = "".join(chr(b) if 32 <= b <= 126 else "." for b in data)
        return f"Hex: {hex_str}\nASCII: {ascii_str}"

    def _debug_print(self, title, message, data=None):
        """デバッグ情報を出力"""
        if not self.debug:
            return

        thread_name = threading.current_thread().name
        print(f"\n[{thread_name}] === {title} ===")
        print(message)
        print("=" * (len(title) + 8))
        print()

    def _debug_print_request(self, data, parsed, addr=None):
        """リクエストのデバッグ情報を出力（統一フォーマット）"""
        if not self.debug:
            return

        packet_details = {
            "Version": getattr(parsed, "version", "N/A"),
            "Type": getattr(parsed, "type", "N/A"),
            "Packet ID": getattr(parsed, "packet_id", "N/A"),
        }

        log = UnifiedLogFormatter.format_communication_log(
            server_name=self.server_name,
            direction="recv from",
            remote_addr=addr[0] if addr else "unknown",
            remote_port=addr[1] if addr else 0,
            packet_size=len(data),
            packet_details=packet_details,
        )
        print(log)

    def _debug_print_response(self, response, addr=None, request=None):
        """レスポンス送信時のログを出力（統一フォーマット）"""

        packet_details = {}
        if request is not None and self.debug:
            packet_details["Packet ID"] = getattr(request, "packet_id", "N/A")
            packet_details["Type"] = getattr(request, "type", "N/A")

        log = UnifiedLogFormatter.format_communication_log(
            server_name=self.server_name,
            direction="sent to",
            remote_addr=addr[0] if addr else "unknown",
            remote_port=addr[1] if addr else 0,
            packet_size=len(response),
            packet_details=packet_details if self.debug else None,
        )
        print(log)

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

    def validate_auth(self, request):
        """
        認証の妥当性をチェック（共通処理）

        Args:
            request: リクエストオブジェクト

        Returns:
            tuple: (is_valid, error_code, error_message)
        """
        # 認証が有効でない場合は常にTrue
        if not self.auth_enabled:
            if self.debug:
                print(f"[{self.server_name}] Auth: disabled")
            return True, None, None

        # リクエストに認証機能を設定
        request.enable_auth(self.auth_passphrase)

        # リクエスト認証フラグ処理（ReportServerのみ）
        if self.request_auth_enabled:
            if hasattr(request, "process_request_auth_flags"):
                if not request.process_request_auth_flags():
                    if self.debug:
                        print(f"[{self.server_name}] Auth Flags: ✗")
                    return False, "403", "認証フラグの検証に失敗しました"
                if self.debug:
                    print(f"[{self.server_name}] Auth Flags: ✓")
            else:
                if self.debug:
                    print(
                        f"[{self.server_name}] Warning: process_request_auth_flags not available"
                    )

        # 拡張フィールドベースの認証ハッシュを検証
        if hasattr(request, "verify_auth_from_extended_field"):
            if not request.verify_auth_from_extended_field():
                if self.debug:
                    print(f"[{self.server_name}] Auth: ✗")
                return False, "403", "認証に失敗しました"
            if self.debug:
                print(f"[{self.server_name}] Auth: ✓")
        else:
            if self.debug:
                print(
                    f"[{self.server_name}] Warning: verify_auth_from_extended_field not available"
                )
            return False, "403", "認証メソッドが利用できません"

        return True, None, None

    def validate_request(self, request):
        """
        リクエストの妥当性をチェック（派生クラスでオーバーライド可能）

        Args:
            request: リクエストオブジェクト

        Returns:
            tuple: (is_valid, error_message)
        """
        return True, None, None

    def _handle_error(self, error_code, original_packet, addr):
        """
        エラーパケットを生成して送信

        Args:
            error_code: エラーコード（uint16）
            original_packet: 元のリクエストパケット（解析済みオブジェクト）
            addr: 送信元アドレス
        """
        try:
            # ソース情報取得（送信元アドレスから）
            source_ip = addr[0] if isinstance(addr, tuple) else "0.0.0.0"
            source_port = addr[1] if isinstance(addr, tuple) else 0

            # 元のパケットにsource情報があれば優先的に利用する
            try:
                if (
                    hasattr(original_packet, "ex_field")
                    and original_packet.ex_field
                    and original_packet.ex_field.contains("source")
                ):
                    orig_source = original_packet.ex_field.source
                    if (
                        isinstance(orig_source, tuple)
                        and len(orig_source) == 2
                        and orig_source[0]
                    ):
                        source_ip, source_port = orig_source
            except Exception:
                pass

            # ErrorResponseパケットの生成
            err_pkt = ErrorResponse()
            err_pkt.packet_id = original_packet.packet_id
            err_pkt.error_code = error_code
            err_pkt.ex_flag = 1
            err_pkt.ex_field.set("source", (source_ip, source_port))

            # パケットをシリアライズ
            response_data = err_pkt.to_bytes()

            # エラーレスポンスを送信
            self.sock.sendto(response_data, addr)

            log = UnifiedLogFormatter.format_communication_log(
                server_name=self.server_name,
                direction="sent to",
                remote_addr=addr[0] if isinstance(addr, tuple) else "unknown",
                remote_port=addr[1] if isinstance(addr, tuple) else 0,
                packet_size=len(response_data),
                packet_details={"Error Code": error_code} if self.debug else None,
            )
            print(log)

        except Exception as e:
            print(
                f"[{threading.current_thread().name}] Failed to send error response: {e}"
            )
            if self.debug:
                traceback.print_exc()

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
            timing_info["parse"] = parse_time

            # デバッグ出力
            self._debug_print_request(data, request, addr)

            # リクエストの妥当性をチェック（基本チェックのみ）
            # 詳細なバリデーションは create_response 内で行われる
            basic_is_valid, basic_error_code, basic_error_msg = self.validate_request(
                request
            )
            if not basic_is_valid:
                with self.lock:
                    self.error_count += 1
                if self.debug:
                    print(
                        f"{basic_error_code}: [{threading.current_thread().name}] Invalid request from {addr}: {basic_error_msg}"
                    )
                # バリデーションエラーの場合はエラーパケットを送信
                # error_codeが指定されていればそれを使用、なければデフォルトの0x0001を使用
                error_code_int = (
                    int(basic_error_code)
                    if basic_error_code and str(basic_error_code).isdigit()
                    else 0x0001
                )
                self._handle_error(error_code_int, request, addr)
                return

            # レスポンスを作成
            response, response_time = self._measure_time(self.create_response, request)
            timing_info["response"] = response_time

            # デバッグ出力
            self._debug_print_response(response, addr, request)

            # レスポンスを送信
            send_start = time.time()
            self.sock.sendto(response, addr)
            timing_info["send"] = time.time() - send_start

            # 合計処理時間
            timing_info["total"] = time.time() - start_time

            # タイミング情報を出力
            if self.debug:
                self._print_timing_info(addr, timing_info)

            if self.debug:
                print(
                    f"[{threading.current_thread().name}] Successfully sent response to {addr}"
                )

        except Exception as e:
            with self.lock:
                self.error_count += 1
            print(
                f"[{threading.current_thread().name}] Error processing request from {addr}: {e}"
            )
            if self.debug:
                traceback.print_exc()

            # エラーが発生した場合、元のリクエストをパースできているかどうかで処理を分ける
            if "request" in locals() and request is not None:
                # リクエストのパースに成功している場合はエラーパケットを送信
                self._handle_error(0x0003, request, addr)  # 0x0003はサーバー内部エラー
            else:
                # リクエストのパースに失敗している場合は最小限のエラーパケットを送信
                dummy_request = Format()
                dummy_request.packet_id = 0  # 不明のため0
                self._handle_error(0x0001, dummy_request, addr)

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
            log = UnifiedLogFormatter.format_communication_log(
                server_name=self.server_name,
                direction="sent to",
                remote_addr=host,
                remote_port=port,
                packet_size=bytes_sent,
            )
            print(log)
            return bytes_sent
        except Exception as e:
            print(f"[{self.server_name}] Error sending packet to {host}:{port}: {e}")
            if self.debug:
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
        buffer_size = int(os.getenv("UDP_BUFFER_SIZE", 4096))

        try:
            while True:
                try:
                    # リクエストを受信
                    data, addr = self.sock.recvfrom(buffer_size)

                    # 常に受信をログ出力（統一フォーマット）
                    recv_log = UnifiedLogFormatter.format_communication_log(
                        server_name=self.server_name,
                        direction="recv from",
                        remote_addr=addr[0],
                        remote_port=addr[1],
                        packet_size=len(data),
                    )
                    print(recv_log)

                    if self.debug:
                        print(f"[Main] Submitting to worker pool for processing")

                    # スレッドプールにリクエスト処理を投入
                    self.thread_pool.submit(self.handle_request, data, addr)

                except socket.timeout:
                    # タイムアウトは正常な動作
                    continue
                except socket.error as e:
                    # Windows特有のエラー処理
                    if hasattr(e, "winerror"):
                        if e.winerror == 10054:
                            # WSAECONNRESET - クライアントが接続を切断
                            # UDPでは正常な動作なので無視
                            if self.debug:
                                print(f"[Main] Client disconnected (ignored): {e}")
                            continue
                        if e.winerror == 10038:
                            # WSAENOTSOCK - ソケットが無効
                            print(
                                f"[Main] Invalid socket detected (WSAENOTSOCK): {e}. Attempting to reinitialize socket."
                            )
                            try:
                                if self.sock:
                                    self.sock.close()
                                self._init_socket()
                                print("[Main] Socket reinitialized successfully")
                                continue
                            except Exception as reinit_err:
                                print(
                                    f"[Main] Failed to reinitialize socket: {reinit_err}. Shutting down."
                                )
                                self.shutdown()
                                break
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
