"""
Report Client - IoT機器データ収集専用クライアント

このモジュールはセンサーデータレポート用の `ReportClient` クラスと
コマンドライン実行向けのエントリポイントを提供する。
"""

import logging
import socket
import time
import os
from datetime import datetime
from typing import Optional, Dict, Any, Union, List

from ..packet.types.report_packet import ReportRequest, ReportResponse
from ..packet.types.error_response import ErrorResponse
from .utils.packet_id_generator import PacketIDGenerator12Bit


class ReportClient:
    """IoT機器からのセンサーデータレポート送信用クライアント"""

    def __init__(self, host='localhost', port=4110, debug=False):
        """
        初期化

        Args:
            host: 天気サーバーのホスト（レポートを転送）
            port: 天気サーバーのポート
            debug: デバッグモード
        """
        self.host = host
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.settimeout(10.0)
        self.debug = debug
        logging.basicConfig(level=logging.DEBUG if debug else logging.INFO)
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG if debug else logging.INFO)
        self.VERSION = 1
        self.PIDG = PacketIDGenerator12Bit()

        # 収集データをメンバ変数として保持
        self.area_code: Optional[Union[str, int]] = None
        self.weather_code: Optional[int] = None
        self.temperature: Optional[float] = None
        self.precipitation_prob: Optional[int] = None
        self.alert: Optional[List[str]] = None
        self.disaster: Optional[List[str]] = None

    def set_sensor_data(self, area_code: Union[str, int],
                       weather_code: Optional[int] = None,
                       temperature: Optional[float] = None,
                       precipitation_prob: Optional[int] = None,
                       alert: Optional[List[str]] = None,
                       disaster: Optional[List[str]] = None):
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

    def _hex_dump(self, data):
        """バイナリデータのhexダンプを作成"""
        hex_str = ' '.join(f'{b:02x}' for b in data)
        ascii_str = ''.join(chr(b) if 32 <= b <= 126 else '.' for b in data)
        return f"Hex: {hex_str}\nASCII: {ascii_str}"

    def _debug_print_request(self, request):
        """リクエストのデバッグ情報を出力"""
        if not self.debug:
            return

        self.logger.debug("\n=== SENDING REPORT REQUEST PACKET ===")
        self.logger.debug("Request Type: Report Data (Type 4)")
        self.logger.debug(f"Total Length: {len(request.to_bytes())} bytes")

        self.logger.debug("\nHeader:")
        self.logger.debug(f"Version: {request.version}")
        self.logger.debug(f"Type: {request.type}")
        self.logger.debug(f"Packet ID: {request.packet_id}")
        self.logger.debug(f"Timestamp: {time.ctime(request.timestamp)}")
        self.logger.debug(f"Area Code: {request.area_code}")

        self.logger.debug("\nFlags:")
        self.logger.debug(f"Weather: {request.weather_flag}")
        self.logger.debug(f"Temperature: {request.temperature_flag}")
        self.logger.debug(f"POP: {request.pop_flag}")
        self.logger.debug(f"Alert: {request.alert_flag}")
        self.logger.debug(f"Disaster: {request.disaster_flag}")

        self.logger.debug("\nSensor Data:")
        if request.weather_flag and hasattr(request, 'weather_code'):
            self.logger.debug(f"Weather Code: {request.weather_code}")
        if request.temperature_flag and hasattr(request, 'temperature'):
            temp_celsius = getattr(request, 'temperature', 0) - 100
            self.logger.debug(f"Temperature: {temp_celsius}℃")
        if request.pop_flag and hasattr(request, 'pop'):
            self.logger.debug(f"Precipitation Prob: {request.pop}%")

        self.logger.debug("\nRaw Packet:")
        self.logger.debug(self._hex_dump(request.to_bytes()))
        self.logger.debug("====================================\n")

    def _debug_print_response(self, response):
        """レスポンスのデバッグ情報を出力"""
        if not self.debug:
            return

        self.logger.debug("\n=== RECEIVED REPORT RESPONSE PACKET ===")
        self.logger.debug(f"Response Type: {response.type}")
        self.logger.debug(f"Total Length: {len(response.to_bytes())} bytes")

        self.logger.debug("\nHeader:")
        self.logger.debug(f"Version: {response.version}")
        self.logger.debug(f"Type: {response.type}")
        self.logger.debug(f"Area Code: {response.area_code}")
        self.logger.debug(f"Packet ID: {response.packet_id}")
        self.logger.debug(f"Timestamp: {time.ctime(response.timestamp)}")

        if hasattr(response, 'is_success'):
            self.logger.debug(f"Success: {response.is_success()}")

        if hasattr(response, 'get_response_summary'):
            summary = response.get_response_summary()
            self.logger.debug(f"Summary: {summary}")

        self.logger.debug("\nRaw Packet:")
        self.logger.debug(self._hex_dump(response.to_bytes()))
        self.logger.debug("=====================================\n")

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
                version=self.VERSION
            )

            self._debug_print_request(request)
            self.sock.sendto(request.to_bytes(), (self.host, self.port))
            response_data, _ = self.sock.recvfrom(1024)

            response_type = int.from_bytes(response_data[2:3], byteorder='little') & 0x07

            if response_type == 5:  # レポートレスポンス（ACK）
                response = ReportResponse.from_bytes(response_data)
                self._debug_print_response(response)

                if response.is_success():
                    result = {
                        'type': 'report_ack',
                        'success': True,
                        'area_code': response.area_code,
                        'packet_id': response.packet_id,
                        'timestamp': response.timestamp,
                        'response_time_ms': (time.time() - start_time) * 1000
                    }

                    if hasattr(response, 'get_response_summary'):
                        result.update(response.get_response_summary())

                    if self.debug:
                        self.logger.debug(f"\n✓ レポート送信成功: {result}")

                    return result
                else:
                    self.logger.error("レポート送信失敗: サーバーからエラーレスポンス")
                    return None

            elif response_type == 7:  # エラーレスポンス
                response = ErrorResponse.from_bytes(response_data)
                if self.debug:
                    self.logger.error("\n=== ERROR RESPONSE ===")
                    self.logger.error(f"Error Code: {response.error_code}")
                    self.logger.error("=====================\n")

                return {
                    'type': 'error',
                    'error_code': response.error_code,
                    'success': False
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
            'area_code': self.area_code,
            'weather_code': self.weather_code,
            'temperature': self.temperature,
            'precipitation_prob': self.precipitation_prob,
            'alert': self.alert,
            'disaster': self.disaster
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

    host = os.getenv('WEATHER_SERVER_HOST', 'localhost')
    port = int(os.getenv('WEATHER_SERVER_PORT', '4110'))

    client = ReportClient(host=host, port=port, debug=True)

    try:
        logger.info("\n1. Setting sensor data individually")
        logger.info("-" * 40)

        client.set_area_code("011000")  # 札幌
        client.set_weather_code(100)    # 晴れ
        client.set_temperature(25.5)    # 25.5℃
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
            weather_code=200,    # 曇り
            temperature=22.3,    # 22.3℃
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
            weather_code=300,    # 雨
            temperature=18.7,    # 18.7℃
            precipitation_prob=80,  # 80%
            alert=["大雨警報", "洪水注意報"],
            disaster=["河川氾濫危険情報"]
        )

        result = client.send_report_data()
        if result:
            logger.info("\n✓ Alert report sent successfully!")
            logger.info(f"Response: {result}")
        else:
            logger.error("\n✗ Failed to send alert report")

    finally:
        client.close()

    logger.info("\n" + "="*60)
    logger.info("Report Client Example completed")
    logger.info("✓ IoT sensor data reporting functionality demonstrated")


def create_report_client(host='localhost', port=4110, debug=False):
    """ReportClientインスタンスを作成する便利関数"""
    return ReportClient(host=host, port=port, debug=debug)


def send_sensor_report(area_code, weather_code=None, temperature=None,
                      precipitation_prob=None, alert=None, disaster=None,
                      host='localhost', port=4110, debug=False):
    """センサーレポートを一回の呼び出しで送信する便利関数"""
    client = ReportClient(host=host, port=port, debug=debug)

    try:
        client.set_sensor_data(
            area_code=area_code,
            weather_code=weather_code,
            temperature=temperature,
            precipitation_prob=precipitation_prob,
            alert=alert,
            disaster=disaster
        )

        return client.send_report_data()

    finally:
        client.close()


if __name__ == "__main__":
    main()
