"""
設定ファイル読み込みユーティリティ
各サーバーの設定ファイルを読み込み、環境変数の展開もサポート
"""

import os
import configparser
from pathlib import Path
from dotenv import load_dotenv


class ConfigLoader:
    """設定ファイルローダー"""

    def __init__(self, config_path=None):
        """
        初期化

        Args:
            config_path: 設定ファイルのパス（Noneの場合は呼び出し元のディレクトリから探す）
        """
        # 環境変数を読み込む
        load_dotenv()

        # 設定ファイルのパスを決定
        if config_path is None:
            # 呼び出し元のディレクトリからconfig.iniを探す
            import inspect

            caller_file = inspect.stack()[1].filename
            caller_dir = Path(caller_file).parent
            config_path = caller_dir / "config.ini"

        self.config_path = Path(config_path)
        # 環境変数展開は独自実装を使うため、デフォルトの補間を無効化
        self.config = configparser.ConfigParser(interpolation=None)

        # 設定ファイルを読み込む
        self._load_config()

    def _load_config(self):
        """設定ファイルを読み込む"""
        if self.config_path.exists():
            self.config.read(self.config_path, encoding="utf-8")
            self._expand_env_vars()
        else:
            print(f"Warning: Config file not found: {self.config_path}")

    def _expand_env_vars(self):
        """設定値内の環境変数を展開"""
        for section in self.config.sections():
            for key, value in self.config.items(section):
                # ${VAR_NAME}形式の環境変数を展開
                if "${" in value and "}" in value:
                    import re

                    pattern = r"\$\{([^}]+)\}"

                    def replace_env(match):
                        env_var = match.group(1)
                        return os.getenv(env_var, match.group(0))

                    expanded_value = re.sub(pattern, replace_env, value)
                    self.config.set(section, key, expanded_value)

    def get(self, section, key, default=None):
        """設定値を取得"""
        try:
            return self.config.get(section, key)
        except (configparser.NoSectionError, configparser.NoOptionError):
            return default

    def getint(self, section, key, default=None):
        """整数値として設定値を取得"""
        try:
            return self.config.getint(section, key)
        except (configparser.NoSectionError, configparser.NoOptionError, ValueError):
            return default

    def getboolean(self, section, key, default=None):
        """ブール値として設定値を取得"""
        try:
            return self.config.getboolean(section, key)
        except (configparser.NoSectionError, configparser.NoOptionError, ValueError):
            return default

    def get_section(self, section):
        """セクション全体を辞書として取得"""
        try:
            return dict(self.config.items(section))
        except configparser.NoSectionError:
            return {}

    def has_section(self, section):
        """セクションが存在するかチェック"""
        return self.config.has_section(section)

    def sections(self):
        """全セクションのリストを取得"""
        return self.config.sections()
