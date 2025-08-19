"""
Report Client - IoT機器データ収集専用クライアント

このモジュールはセンサーデータレポート用の `ReportClient` クラスと
コマンドライン実行向けのエントリポイントを提供する。
"""

import logging
import socket
import time
import os
import asyncio
from typing import Optional, Dict, Any, Union, List

from WIPCommonPy.packet.types.report_packet import ReportRequest, ReportResponse
from WIPCommonPy.packet.types.error_response import ErrorResponse
from WIPCommonPy.packet.debug import create_debug_logger
from WIPCommonPy.clients.utils.packet_id_generator import PacketIDGenerator12Bit
from WIPCommonPy.clients.utils import receive_with_id, receive_with_id_async, safe_sock_sendto
from WIPCommonPy.utils.network import resolve_ipv4


class ReportClient:
    """IoT機器からのセンサーデータレポート送信用クライアント"""

    def __init__(self, host=None, port=None, debug=False):
        """
        初期化

        Args:
            host: Report Serverのホスト
            port: Report Serverのポート
            debug: デバッグモード
        """
        if host is None:
            host = os.getenv("REPORT_SERVER_HOST", "localhost")
        if port is None:
            port = int(os.getenv("REPORT_SERVER_PORT", "4112"))

        self.host = resolve_ipv4(host)
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.settimeout(10.0)
        self.debug = debug
        logging.basicConfig(level=logging.DEBUG if debug else logging.INFO)
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG if debug else logging.INFO)
        self.debug_logger = create_debug_logger(__name__, debug)
        self.VERSION = 1
        self.PIDG = PacketIDGenerator12Bit()

        # 認証設定を初期化
        self._init_auth_config()

        # 収集データをメンバ変数として保持
        self.area_code: Optional[Union[str, int]] = None
        self.weather_code: Optional[int] = None
        self.temperature: Optional[float] = None
        self.precipitation_prob: Optional[int] = None
        self.alert: Optional[List[str]] = None
        self.disaster: Optional[List[str]] = None

    def _init_auth_config(self):
        """認証設定を環境変数から読み込み"""
        # ReportServer向けのリクエスト認証設定
        auth_enabled = (
            os.getenv("REPORT_SERVER_REQUEST_AUTH_ENABLED", "false").lower() == "true"
        )
        auth_passphrase = os.getenv("REPORT_SERVER_PASSPHRASE", "")

        self.auth_enabled = auth_enabled
        self.auth_passphrase = auth_passphrase

    def _get_response_auth_config(self):
        """レスポンス認証設定を取得"""
        return (
            os.getenv("REPORT_SERVER_RESPONSE_AUTH_ENABLED", "false").lower() == "true"
        )
    
    def _verify_response_auth(self, response):
        """
        レスポンス認証を検証
        
        Args:
            response: ReportResponse オブジェクト
            
        Returns:
            bool: 認証が成功した場合True、失敗またはスキップした場合False
        """
        # レスポンス認証が無効な場合は常にTrue
        if not self._get_response_auth_config():
            return True
            
        # パスフレーズが設定されていない場合は失敗
        if not self.auth_passphrase:
            self.logger.warning("Response authentication enabled but passphrase not set")
            return False
            
        # レスポンスパケットのタイムスタンプとパケットIDを使って再計算
        from WIPCommonPy.utils.auth import WIPAuth
        
        try:
            # レスポンスパケットの認証ハッシュを拡張フィールドから取得
            if not hasattr(response, "ex_field") or not response.ex_field:
                self.logger.warning("Response authentication required but no extended field found")
                return False
                
            auth_hash_str = response.ex_field._data.get("auth_hash")
            if not auth_hash_str:
                self.logger.warning("Response authentication required but no auth_hash found")
                return False
                
            # hex文字列をバイト列に変換
            received_hash = bytes.fromhex(auth_hash_str)
            
            # レスポンスパケットのタイムスタンプとパケットIDで認証ハッシュを再計算
            is_valid = WIPAuth.verify_auth_hash(
                packet_id=response.packet_id,
                timestamp=response.timestamp,
                passphrase=self.auth_passphrase,
                received_hash=received_hash
            )
            
            if not is_valid:
                self.logger.error("Response authentication verification failed")
                return False
                
            self.logger.debug("Response authentication verification successful")
            return True
            
        except Exception as e:
            self.logger.error(f"Error during response authentication verification: {e}")
            return False

    def set_sensor_data(
        self,
        area_code: Union[str, int],
        weather_code: Optional[int] = None,
        temperature: Optional[float] = None,
        precipitation_prob: Optional[int] = None,
        alert: Optional[List[str]] = None,
        disaster: Optional[List[str]] = None,
    ):
        """センサーデータを設定"""
        self.area_code = area_code
        self.weather_code = weather_code
        self.temperature = temperature
        self.precipitation_prob = precipitation_prob
        self.alert = alert
        self.disaster = disaster

        if self.debug:
            self.logger.debug(
                f"センサーデータを設定: エリア={area_code}, 天気={weather_code}, "
                f"気温={temperature}℃, 降水確率={precipitation_prob}%"
            )

    def set_area_code(self, area_code: Union[str, int]):
        """エリアコードを設定"""
        self.area_code = area_code

    def set_weather_code(self, weather_code: int):
        """天気コードを設定"""
        self.weather_code = weather_code

    def set_temperature(self, temperature: float):
        """気温を設定（摂氏）"""
        self.temperature = temperature

    def set_precipitation_prob(self, precipitation_prob: int):
        """降水確率を設定（0-100%）"""
        self.precipitation_prob = precipitation_prob

    def set_alert(self, alert: List[str]):
        """警報情報を設定"""
        self.alert = alert

    def set_disaster(self, disaster: List[str]):
        """災害情報を設定"""
        self.disaster = disaster

    def send_report_data(self) -> Optional[Dict[str, Any]]:
        """設定されたセンサーデータでレポートを送信（統一命名規則版）"""
        if self.area_code is None:
            self.logger.error("エリアコードが設定されていません")
            return None

        try:
            start_time = time.time()

            request = ReportRequest.create_sensor_data_report(
                area_code=self.area_code,
                weather_code=self.weather_code,
                temperature=self.temperature,
                precipitation_prob=self.precipitation_prob,
                alert=self.alert,
                disaster=self.disaster,
                version=self.VERSION,
            )

            # 認証設定を適用（認証が有効な場合）
            if self.auth_enabled and self.auth_passphrase:
                request.enable_auth(self.auth_passphrase)
                request.set_auth_flags()

            # レスポンス認証フラグの設定
            if self._get_response_auth_config():
                request.response_auth = 1

            self.debug_logger.log_request(request, "SENSOR REPORT REQUEST")
            self.sock.sendto(request.to_bytes(), (self.host, self.port))
            response_data, _ = receive_with_id(self.sock, request.packet_id, 10.0)

            response_type = (
                int.from_bytes(response_data[2:3], byteorder="little") & 0x07
            )

            if response_type == 5:  # レポートレスポンス（ACK）
                response = ReportResponse.from_bytes(response_data)
                self.debug_logger.log_response(response, "SENSOR REPORT RESPONSE")

                # レスポンス認証検証
                if response and not self._verify_response_auth(response):
                    self.logger.error("Response authentication verification failed")
                    return {"status": "error", "message": "Response authentication failed"}

                if response.is_success():
                    result = {
                        "type": "report_ack",
                        "success": True,
                        "area_code": response.area_code,
                        "packet_id": response.packet_id,
                        "timestamp": response.timestamp,
                        "response_time_ms": (time.time() - start_time) * 1000,
                    }

                    if hasattr(response, "get_response_summary"):
                        result.update(response.get_response_summary())

                    # 統一フォーマットでの成功ログ出力
                    execution_time = time.time() - start_time
                    report_data = {
                        "area_code": self.area_code,
                        "timestamp": result["timestamp"],
                    }
                    if self.weather_code is not None:
                        report_data["weather_code"] = self.weather_code
                    if self.temperature is not None:
                        report_data["temperature"] = self.temperature
                    if self.precipitation_prob is not None:
                        report_data["precipitation_prob"] = self.precipitation_prob
                    if self.alert:
                        report_data["alert"] = self.alert
                    if self.disaster:
                        report_data["disaster"] = self.disaster

                    self.debug_logger.log_unified_packet_received(
                        "Direct request", execution_time, report_data
                    )

                    return result
                else:
                    self.logger.error("レポート送信失敗: サーバーからエラーレスポンス")
                    return None

            elif response_type == 7:  # エラーレスポンス
                response = ErrorResponse.from_bytes(response_data)
                self.debug_logger.log_error(
                    f"Report failed", f"Error Code: {response.error_code}"
                )

                return {
                    "type": "error",
                    "error_code": response.error_code,
                    "success": False,
                }
            else:
                self.logger.error(f"不明なパケットタイプ: {response_type}")
                return None

        except socket.timeout:
            self.logger.error("レポートサーバー接続タイムアウト")
            return None
        except Exception as e:
            self.logger.error(f"レポート送信エラー: {e}")
            if self.debug:
                self.logger.exception("Traceback:")
            return None

    async def send_report_data_async(self) -> Optional[Dict[str, Any]]:
        """非同期でレポートを送信"""
        if self.area_code is None:
            self.logger.error("エリアコードが設定されていません")
            return None

        loop = asyncio.get_running_loop()
        self.sock.setblocking(False)

        try:
            start_time = time.time()

            request = ReportRequest.create_sensor_data_report(
                area_code=self.area_code,
                weather_code=self.weather_code,
                temperature=self.temperature,
                precipitation_prob=self.precipitation_prob,
                alert=self.alert,
                disaster=self.disaster,
                version=self.VERSION,
            )

            if self.auth_enabled and self.auth_passphrase:
                request.enable_auth(self.auth_passphrase)
                request.set_auth_flags()

            # レスポンス認証フラグの設定（非同期版）
            if self._get_response_auth_config():
                request.response_auth = 1

            self.debug_logger.log_request(request, "SENSOR REPORT REQUEST")
            await safe_sock_sendto(
                loop, self.sock, request.to_bytes(), (self.host, self.port)
            )
            response_data, _ = await receive_with_id_async(
                self.sock, request.packet_id, 10.0
            )

            response_type = (
                int.from_bytes(response_data[2:3], byteorder="little") & 0x07
            )

            if response_type == 5:
                response = ReportResponse.from_bytes(response_data)
                self.debug_logger.log_response(response, "SENSOR REPORT RESPONSE")

                # レスポンス認証検証（非同期版）
                if response and not self._verify_response_auth(response):
                    self.logger.error("Response authentication verification failed")
                    return {"status": "error", "message": "Response authentication failed"}

                if response.is_success():
                    result = {
                        "type": "report_ack",
                        "success": True,
                        "area_code": response.area_code,
                        "packet_id": response.packet_id,
                        "timestamp": response.timestamp,
                        "response_time_ms": (time.time() - start_time) * 1000,
                    }

                    if hasattr(response, "get_response_summary"):
                        result.update(response.get_response_summary())

                    execution_time = time.time() - start_time
                    report_data = {
                        "area_code": self.area_code,
                        "timestamp": result["timestamp"],
                    }
                    if self.weather_code is not None:
                        report_data["weather_code"] = self.weather_code
                    if self.temperature is not None:
                        report_data["temperature"] = self.temperature
                    if self.precipitation_prob is not None:
                        report_data["precipitation_prob"] = self.precipitation_prob
                    if self.alert:
                        report_data["alert"] = self.alert
                    if self.disaster:
                        report_data["disaster"] = self.disaster

                    self.debug_logger.log_unified_packet_received(
                        "Direct request", execution_time, report_data
                    )

                    return result
                else:
                    self.logger.error("レポート送信失敗: サーバーからエラーレスポンス")
                    return None

            elif response_type == 7:
                response = ErrorResponse.from_bytes(response_data)
                self.debug_logger.log_error(
                    "Report failed", f"Error Code: {response.error_code}"
                )

                return {
                    "type": "error",
                    "error_code": response.error_code,
                    "success": False,
                }
            else:
                self.logger.error(f"不明なパケットタイプ: {response_type}")
                return None

        except asyncio.TimeoutError:
            self.logger.error("レポートサーバー接続タイムアウト")
            return None
        except Exception as e:
            self.logger.error(f"レポート送信エラー: {e}")
            if self.debug:
                self.logger.exception("Traceback:")
            return None

    def send_data_simple(self) -> Optional[Dict[str, Any]]:
        """現在設定されているデータでレポートを送信（統一命名規則版）"""
        return self.send_report_data()

    def clear_data(self):
        """設定されているセンサーデータをクリア"""
        self.area_code = None
        self.weather_code = None
        self.temperature = None
        self.precipitation_prob = None
        self.alert = None
        self.disaster = None

        if self.debug:
            self.logger.debug("センサーデータをクリアしました")

    def get_current_data(self) -> Dict[str, Any]:
        """現在設定されているセンサーデータを取得"""
        return {
            "area_code": self.area_code,
            "weather_code": self.weather_code,
            "temperature": self.temperature,
            "precipitation_prob": self.precipitation_prob,
            "alert": self.alert,
            "disaster": self.disaster,
        }

    def close(self):
        """ソケットを閉じる"""
        self.sock.close()

    # 後方互換性のためのエイリアスメソッド
    def send_report(self) -> Optional[Dict[str, Any]]:
        """後方互換性のため - send_report_data()を使用してください"""
        return self.send_report_data()

    def send_current_data(self) -> Optional[Dict[str, Any]]:
        """後方互換性のため - send_data_simple()を使用してください"""
        return self.send_data_simple()


def main():
    """メイン関数 - 使用例"""
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    logger.info("Report Client Example - IoT Sensor Data Reporting")
    logger.info("=" * 60)

    host = os.getenv("REPORT_SERVER_HOST", "localhost")
    port = int(os.getenv("REPORT_SERVER_PORT", "4112"))

    client = ReportClient(host=host, port=port, debug=True)

    try:
        logger.info("\n1. Setting sensor data individually")
        logger.info("-" * 40)

        client.set_area_code("011000")  # 札幌
        client.set_weather_code(100)  # 晴れ
        client.set_temperature(25.5)  # 25.5℃
        client.set_precipitation_prob(30)  # 30%

        current_data = client.get_current_data()
        logger.info(f"Current data: {current_data}")

        result = client.send_report_data()
        if result:
            logger.info("\n✓ Report sent successfully!")
            logger.info(f"Response: {result}")
        else:
            logger.error("\n✗ Failed to send report")

        logger.info("\n\n2. Setting sensor data in batch")
        logger.info("-" * 40)

        client.set_sensor_data(
            area_code="130000",  # 東京
            weather_code=200,  # 曇り
            temperature=22.3,  # 22.3℃
            precipitation_prob=60,  # 60%
            alert=["大雨注意報"],
        )

        result = client.send_data_simple()
        if result:
            logger.info("\n✓ Batch report sent successfully!")
            logger.info(f"Response: {result}")
        else:
            logger.error("\n✗ Failed to send batch report")

        logger.info("\n\n3. Sending report with alert and disaster info")
        logger.info("-" * 50)

        client.clear_data()
        client.set_sensor_data(
            area_code="270000",  # 大阪
            weather_code=300,  # 雨
            temperature=18.7,  # 18.7℃
            precipitation_prob=80,  # 80%
            alert=["大雨警報", "洪水注意報"],
            disaster=["河川氾濫危険情報"],
        )

        result = client.send_report_data()
        if result:
            logger.info("\n✓ Alert report sent successfully!")
            logger.info(f"Response: {result}")
        else:
            logger.error("\n✗ Failed to send alert report")

    finally:
        client.close()

    logger.info("\n" + "=" * 60)
    logger.info("Report Client Example completed")
    logger.info("✓ IoT sensor data reporting functionality demonstrated")


def create_report_client(host="localhost", port=4110, debug=False):
    """ReportClientインスタンスを作成する便利関数"""
    return ReportClient(host=host, port=port, debug=debug)


def send_sensor_report(
    area_code,
    weather_code=None,
    temperature=None,
    precipitation_prob=None,
    alert=None,
    disaster=None,
    host="localhost",
    port=4110,
    debug=False,
):
    """センサーレポートを一回の呼び出しで送信する便利関数"""
    client = ReportClient(host=host, port=port, debug=debug)

    try:
        client.set_sensor_data(
            area_code=area_code,
            weather_code=weather_code,
            temperature=temperature,
            precipitation_prob=precipitation_prob,
            alert=alert,
            disaster=disaster,
        )

        return client.send_report_data()

    finally:
        client.close()


