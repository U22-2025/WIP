"""WIP Client - 天気サーバーとの通信を簡潔に行う高水準クライアント"""

from __future__ import annotations

import logging
import os
import sys
from dataclasses import dataclass, asdict
from typing import Optional, Dict, Literal

from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common.clients.weather_client import WeatherClient
from common.packet.query_packet import QueryRequest, QueryResponse
from common.packet.location_packet import LocationRequest, LocationResponse
from common.utils.auth import WIPAuth
from datetime import datetime


load_dotenv()


@dataclass
class AuthConfig:
    """認証設定"""
    enabled: bool = False
    passphrase: Optional[str] = None


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
    passphrase: Optional[str] = None  # 後方互換性のため
    # 各サーバーごとの認証設定
    auth_configs: Dict[str, AuthConfig] = None

    def __post_init__(self):
        if self.auth_configs is None:
            self.auth_configs = self._load_auth_configs()

    def _load_auth_configs(self) -> Dict[str, AuthConfig]:
        """環境変数から各サーバーの認証設定を読み込み"""
        configs = {}
        
        # Location Resolver
        configs['location'] = AuthConfig(
            enabled=os.getenv("LOCATION_SERVER_AUTH_ENABLED", "false").lower() == "true",
            passphrase=os.getenv("LOCATION_SERVER_PASSPHRASE")
        )
        
        # Query Generator
        configs['query'] = AuthConfig(
            enabled=os.getenv("QUERY_SERVER_AUTH_ENABLED", "false").lower() == "true",
            passphrase=os.getenv("QUERY_SERVER_PASSPHRASE")
        )
        
        # Weather Server
        configs['weather'] = AuthConfig(
            enabled=os.getenv("WEATHER_SERVER_AUTH_ENABLED", "false").lower() == "true",
            passphrase=os.getenv("WEATHER_SERVER_PASSPHRASE")
        )
        
        # Report Server
        configs['report'] = AuthConfig(
            enabled=os.getenv("REPORT_SERVER_AUTH_ENABLED", "false").lower() == "true",
            passphrase=os.getenv("REPORT_SERVER_PASSPHRASE")
        )
        
        return configs

    def get_auth_config(self, server_type: Literal['location', 'query', 'weather', 'report']) -> AuthConfig:
        """指定されたサーバータイプの認証設定を取得"""
        return self.auth_configs.get(server_type, AuthConfig())


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
        passphrase: Optional[str] = None,
    ) -> None:
        self.config = server_config or ServerConfig()
        if host is not None:
            self.config.host = host
        if port is not None:
            self.config.port = port
        self.debug = debug
        self.state = ClientState(latitude, longitude, area_code, passphrase)

        self.logger = logging.getLogger(__name__)
        if self.debug:
            logging.basicConfig(level=logging.DEBUG)
            self.logger.setLevel(logging.DEBUG)
        else:
            self.logger.setLevel(logging.INFO)

        if not 1 <= self.config.port <= 65535:
            raise ValueError("112: 無効なポート番号")

        try:
            self._weather_client = WeatherClient(
                host=self.config.host, port=self.config.port, debug=self.debug
            )
        except Exception as e:  # pragma: no cover
            raise RuntimeError(f"111: クライアント初期化失敗 - {e}") from e

        if self.debug:
            self.logger.debug(
                f"WIP Client initialized - Server: {self.config.host}:{self.config.port}"
            )
            self.logger.debug(f"Initial state: {self.state}")

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

    @property
    def passphrase(self) -> Optional[str]:
        return self.state.passphrase

    @passphrase.setter
    def passphrase(self, value: Optional[str]) -> None:
        self.state.passphrase = value
        if self.debug:
            self.logger.debug(f"Passphrase updated: {'***' if value else None}")

    # ---------------------------------------------------------------
    # 認証機能
    # ---------------------------------------------------------------
    def _setup_auth(self, request, server_type: Literal['location', 'query', 'weather', 'report']) -> None:
        """
        リクエストに認証機能を設定（認証フラグ対応）
        
        Args:
            request: Request オブジェクト
            server_type: サーバータイプ ('location', 'query', 'weather', 'report')
        """
        # 後方互換性のため、既存のパスフレーズ設定を確認
        if self.state.passphrase:
            request.enable_auth(self.state.passphrase)
            request.add_auth_to_extended_field()
            if self.debug:
                self.logger.debug(f"Authentication enabled (legacy) for packet ID {request.packet_id}")
            return
        
        # 新しいサーバーごとの認証設定を使用
        auth_config = self.state.get_auth_config(server_type)
        
        # 認証フラグの設定
        if hasattr(request, 'set_auth_flags'):
            # サーバーが認証を要求するかどうかとレスポンス認証を有効にするかを設定
            server_request_auth_enabled = auth_config.enabled
            
            # レスポンス認証の設定（サーバーからの認証を要求）
            response_auth_enabled = self._get_response_auth_enabled(server_type)
            
            request.set_auth_flags(
                server_request_auth_enabled=server_request_auth_enabled,
                response_auth_enabled=response_auth_enabled
            )
            
            if self.debug:
                self.logger.debug(f"Authentication flags set for {server_type}: "
                                f"server_request_auth={server_request_auth_enabled}, "
                                f"response_auth={response_auth_enabled}")
        
        # 従来の認証機能（拡張フィールドベース）も設定
        if auth_config.enabled and auth_config.passphrase:
            request.enable_auth(auth_config.passphrase)
            request.add_auth_to_extended_field()
            if self.debug:
                self.logger.debug(f"Extended field authentication enabled for {server_type} server, packet ID {request.packet_id}")
        elif self.debug:
            self.logger.debug(f"Authentication disabled for {server_type} server (enabled={auth_config.enabled}, has_passphrase={bool(auth_config.passphrase)})")
    
    def _get_response_auth_enabled(self, server_type: Literal['location', 'query', 'weather', 'report']) -> bool:
        """
        指定されたサーバータイプのレスポンス認証設定を取得
        
        Args:
            server_type: サーバータイプ
            
        Returns:
            レスポンス認証が有効かどうか
        """
        response_auth_map = {
            'location': os.getenv("LOCATION_RESOLVER_RESPONSE_AUTH_ENABLED", "false").lower() == "true",
            'query': os.getenv("QUERY_GENERATOR_RESPONSE_AUTH_ENABLED", "false").lower() == "true",
            'weather': os.getenv("WEATHER_SERVER_RESPONSE_AUTH_ENABLED", "false").lower() == "true",
            'report': os.getenv("REPORT_SERVER_RESPONSE_AUTH_ENABLED", "false").lower() == "true"
        }
        return response_auth_map.get(server_type, False)

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
    ) -> Optional[Dict]:
        if (
            self.state.latitude is None
            and self.state.longitude is None
            and self.state.area_code is None
        ):
            raise ValueError("133: 必要なデータ未設定 - 座標またはエリアコードを設定してください")

        if self.state.area_code is not None:
            # QueryRequestの場合
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
            
            # 認証機能を設定（QueryRequestの場合はquery server経由）
            self._setup_auth(request, 'query')
            
            result = self._weather_client._execute_query_request(request=request)
        else:
            # LocationRequestの場合
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
            
            # 認証機能を設定（LocationRequestの場合はlocation server経由）
            self._setup_auth(request, 'location')
            
            result = self._weather_client._execute_location_request(request=request)

        if isinstance(result, dict) and result.get("type") == "error":
            return {"error_code": result["error_code"]}
        return result

    def get_weather_by_coordinates(self, latitude: float, longitude: float, **kwargs) -> Optional[Dict]:
        return self._weather_client.get_weather_by_coordinates(latitude=latitude, longitude=longitude, **kwargs)

    def get_weather_by_area_code(self, area_code: str | int, **kwargs) -> Optional[Dict]:
        return self._weather_client.get_weather_by_area_code(area_code=area_code, **kwargs)

    def get_state(self) -> Dict:
        return {**asdict(self.state), "host": self.config.host, "port": self.config.port}

    def set_server(self, host: str, port: Optional[int] = None) -> None:
        self.config.update(host, port)
        self._weather_client.close()
        self._weather_client = WeatherClient(host=self.config.host, port=self.config.port, debug=self.debug)
        if self.debug:
            self.logger.debug(f"Server updated - New server: {self.config.host}:{self.config.port}")

    # ---------------------------------------------------------------
    # コンテキストマネージャ対応
    # ---------------------------------------------------------------
    def close(self) -> None:
        self._weather_client.close()
        if self.debug:
            self.logger.debug("WIP Client closed")

    def __enter__(self) -> "Client":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()


# ---------------------------------------------------------------------------
# 使用例
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("WIP Client Example (State Management)")
    print("=" * 50)

    with Client(debug=True) as client:
        client.set_coordinates(latitude=35.6895, longitude=139.6917)
        result = client.get_weather()
        if result:
            print("✓ Success!")
            print(result)
        else:
            print("✗ Failed to get weather data")
