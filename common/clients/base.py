import socket
import logging
import os

class BaseClient:
    """クライアント共通基底クラス"""

    def __init__(self, host: str, port: int, *, debug: bool = False, timeout: float | None = None,
                 auth_enabled_env: str | None = None, auth_passphrase_env: str | None = None):
        self.server_host = host
        self.server_port = port
        self.debug = debug
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        if timeout is not None:
            self.sock.settimeout(timeout)
        logging.basicConfig(level=logging.DEBUG if debug else logging.INFO)
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.setLevel(logging.DEBUG if debug else logging.INFO)
        self.VERSION = 1
        if auth_enabled_env and auth_passphrase_env:
            self._init_auth_config(auth_enabled_env, auth_passphrase_env)
        else:
            self.auth_enabled = False
            self.auth_passphrase = ''

    def _init_auth_config(self, enabled_var: str, passphrase_var: str) -> None:
        auth_enabled = os.getenv(enabled_var, 'false').lower() == 'true'
        auth_passphrase = os.getenv(passphrase_var, '')
        self.auth_enabled = auth_enabled
        self.auth_passphrase = auth_passphrase
        if self.debug:
            self.logger.debug(f"認証有効: {self.auth_enabled}")
            self.logger.debug(f"パスフレーズ設定: {'✓' if self.auth_passphrase else '✗'}")

    def _hex_dump(self, data: bytes) -> str:
        hex_str = ' '.join(f'{b:02x}' for b in data)
        ascii_str = ''.join(chr(b) if 32 <= b <= 126 else '.' for b in data)
        return f"Hex: {hex_str}\nASCII: {ascii_str}"

    def close(self) -> None:
        self.sock.close()
