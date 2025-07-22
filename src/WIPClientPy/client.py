"""WIP Client - 天気サーバーとの通信を簡潔に行う高水準クライアント"""

from __future__ import annotations

import logging
import os
import sys
from dataclasses import dataclass, asdict
from typing import Optional, Dict

from dotenv import load_dotenv

# 統一ログフォーマットをインポート
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'WIP_Server', 'servers'))
try:
    from common.log_config import LoggerConfig, UnifiedLogFormatter
except ImportError:
    # フォールバック用
    class LoggerConfig:
        @staticmethod
        def setup_client_logger(client_name="WIPClient", debug=False):
            logger = logging.getLogger(f"Client.{client_name}")
            if not logger.handlers and debug:
                handler = logging.StreamHandler()
                formatter = logging.Formatter('%(message)s')
                handler.setFormatter(formatter)
                logger.addHandler(handler)
                logger.setLevel(logging.DEBUG)
            return logger
    
    class UnifiedLogFormatter:
        @staticmethod
        def format_communication_log(**kwargs):
            return "*** Client Log ***"

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from WIPCommonPy.clients.weather_client import WeatherClient
from WIPCommonPy.clients.location_client import LocationClient
from WIPCommonPy.clients.query_client import QueryClient
from WIPCommonPy.packet import LocationRequest, QueryRequest

load_dotenv()

@dataclass
class ServerConfig:
    """Weather Server の接続設定"""

    host: str = os.getenv("WEATHER_SERVER_HOST", "localhost")
    port: int = int(os.getenv("WEATHER_SERVER_PORT", 4110))

    def update(self, host: str, port: Optional[int] = None) -> None:
        self.host = host
        if port is not None:
            self.port = port


@dataclass
class ClientState:
    """クライアントが保持する座標やエリアコード"""

    latitude: Optional[float] = None
    longitude: Optional[float] = None
    area_code: Optional[str | int] = None


class Client:
    """WeatherClient をラップした状態管理型クライアント"""

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        *,
        server_config: Optional[ServerConfig] = None,
        debug: bool = False,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        area_code: Optional[str | int] = None,
    ) -> None:
        self.config = server_config or ServerConfig()
        if host is not None:
            self.config.host = host
        if port is not None:
            self.config.port = port
        self.debug = debug
        self.state = ClientState(latitude, longitude, area_code)

        self.logger = LoggerConfig.setup_client_logger(
            client_name="WIPClient",
            debug=self.debug
        )

        if not 1 <= self.config.port <= 65535:
            raise ValueError("112: 無効なポート番号")

        try:
            self._weather_client = WeatherClient(
                host=self.config.host, port=self.config.port, debug=self.debug
            )
            self._location_client = LocationClient(debug=self.debug)
            self._query_client = QueryClient(debug=self.debug)
        except Exception as e:  # pragma: no cover
            raise RuntimeError(f"111: クライアント初期化失敗 - {e}") from e

        if self.debug:
            init_log = UnifiedLogFormatter.format_communication_log(
                server_name="WIPClient",
                direction="connected to",
                remote_addr=self.config.host,
                remote_port=self.config.port,
                packet_size=0,
                packet_details={"Initial State": str(self.state)}
            )
            self.logger.debug(init_log)

    # ---------------------------------------------------------------
    # プロパティ
    # ---------------------------------------------------------------
    @property
    def latitude(self) -> Optional[float]:
        return self.state.latitude

    @latitude.setter
    def latitude(self, value: Optional[float]) -> None:
        self.state.latitude = value
        if self.debug:
            self.logger.debug(f"Latitude updated: {value}")

    @property
    def longitude(self) -> Optional[float]:
        return self.state.longitude

    @longitude.setter
    def longitude(self, value: Optional[float]) -> None:
        self.state.longitude = value
        if self.debug:
            self.logger.debug(f"Longitude updated: {value}")

    @property
    def area_code(self) -> Optional[str | int]:
        return self.state.area_code

    @area_code.setter
    def area_code(self, value: Optional[str | int]) -> None:
        self.state.area_code = value
        if self.debug:
            self.logger.debug(f"Area code updated: {value}")

    # ---------------------------------------------------------------
    # 公開メソッド
    # ---------------------------------------------------------------
    def set_coordinates(self, latitude: float, longitude: float) -> None:
        if not (-90 <= latitude <= 90) or not (-180 <= longitude <= 180):
            raise ValueError("120: 無効な座標値")
        self.state.latitude = latitude
        self.state.longitude = longitude
        if self.debug:
            self.logger.debug(f"Coordinates updated: ({latitude}, {longitude})")

    def get_weather(
        self,
        weather: bool = True,
        temperature: bool = True,
        precipitation_prob: bool = True,
        alert: bool = False,
        disaster: bool = False,
        day: int = 0,
        *,
        proxy: bool = False,
    ) -> Optional[Dict]:
        if (
            self.state.latitude is None
            and self.state.longitude is None
            and self.state.area_code is None
        ):
            raise ValueError("133: 必要なデータ未設定 - 座標またはエリアコードを設定してください")

        if proxy:
            if self.state.area_code is not None:
                request = QueryRequest.create_query_request(
                    area_code=self.state.area_code,
                    packet_id=self._weather_client.PIDG.next_id(),
                    weather=weather,
                    temperature=temperature,
                    precipitation_prob=precipitation_prob,
                    alert=alert,
                    disaster=disaster,
                    day=day,
                    version=self._weather_client.VERSION
                )
                result = self._weather_client._execute_query_request(request=request)
            else:
                request = LocationRequest.create_coordinate_lookup(
                    latitude=self.state.latitude,
                    longitude=self.state.longitude,
                    packet_id=self._weather_client.PIDG.next_id(),
                    weather=weather,
                    temperature=temperature,
                    precipitation_prob=precipitation_prob,
                    alert=alert,
                    disaster=disaster,
                    day=day,
                    version=self._weather_client.VERSION
                )
                result = self._weather_client._execute_location_request(request=request)
        else:
            if self.state.area_code is not None:
                result = self._query_client.get_weather_data(
                    area_code=self.state.area_code,
                    weather=weather,
                    temperature=temperature,
                    precipitation_prob=precipitation_prob,
                    alert=alert,
                    disaster=disaster,
                    day=day,
                )
            else:
                area_code = self._location_client.get_area_code_simple(
                    latitude=self.state.latitude,
                    longitude=self.state.longitude,
                )
                if area_code is None:
                    return None
                result = self._query_client.get_weather_data(
                    area_code=area_code,
                    weather=weather,
                    temperature=temperature,
                    precipitation_prob=precipitation_prob,
                    alert=alert,
                    disaster=disaster,
                    day=day,
                )

        if isinstance(result, dict) and result.get("type") == "error":
            return {"error_code": result["error_code"]}
        return result

    def get_weather_by_coordinates(
        self,
        latitude: float,
        longitude: float,
        *,
        proxy: bool = False,
        **kwargs,
    ) -> Optional[Dict]:
        if proxy:
            return self._weather_client.get_weather_by_coordinates(
                latitude=latitude, longitude=longitude, **kwargs
            )
        area_code = self._location_client.get_area_code_simple(
            latitude=latitude, longitude=longitude
        )
        if area_code is None:
            return None
        return self._query_client.get_weather_data(
            area_code=area_code,
            **kwargs,
        )

    def get_weather_by_area_code(
        self,
        area_code: str | int,
        *,
        proxy: bool = False,
        **kwargs,
    ) -> Optional[Dict]:
        if proxy:
            return self._weather_client.get_weather_by_area_code(
                area_code=area_code, **kwargs
            )
        return self._query_client.get_weather_data(area_code=area_code, **kwargs)

    def get_state(self) -> Dict:
        return {**asdict(self.state), "host": self.config.host, "port": self.config.port}

    def set_server(self, host: str, port: Optional[int] = None) -> None:
        self.config.update(host, port)
        self._weather_client.close()
        self._weather_client = WeatherClient(host=self.config.host, port=self.config.port, debug=self.debug)
        self._location_client.close()
        self._query_client.close()
        self._location_client = LocationClient(debug=self.debug)
        self._query_client = QueryClient(debug=self.debug)
        if self.debug:
            self.logger.debug(f"Server updated - New server: {self.config.host}:{self.config.port}")

    # ---------------------------------------------------------------
    # コンテキストマネージャ対応
    # ---------------------------------------------------------------
    def close(self) -> None:
        self._weather_client.close()
        self._location_client.close()
        self._query_client.close()
        if self.debug:
            self.logger.debug("WIP Client closed")

    def __enter__(self) -> "Client":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()
