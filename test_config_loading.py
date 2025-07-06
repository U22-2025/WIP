#!/usr/bin/env python3
"""
設定ファイルの環境変数読み込みテスト
"""

import os
import sys
from pathlib import Path

# パスを追加
sys.path.insert(0, str(Path(__file__).parent))

from common.utils.config_loader import ConfigLoader

def test_config_loading():
    """設定ファイルの環境変数読み込みをテスト"""
    print("環境変数読み込みテスト開始")
    print("=" * 50)
    
    # Weather Serverの設定をテスト
    print("\n[Weather Server Config Test]")
    try:
        config = ConfigLoader('WIP_Server/servers/weather_server/config.ini')
        
        # 基本設定のテスト
        host = config.get('server', 'host', 'default')
        port = config.get('server', 'port', 'default')
        debug = config.get('server', 'debug', 'default')
        
        print(f"Host: {host}")
        print(f"Port: {port}")
        print(f"Debug: {debug}")
        
        # 接続先設定のテスト
        print("\n接続先設定:")
        location_host = config.get('connections', 'location_server_host', 'default')
        location_port = config.get('connections', 'location_server_port', 'default')
        query_host = config.get('connections', 'query_server_host', 'default')
        query_port = config.get('connections', 'query_server_port', 'default')
        
        print(f"Location Server: {location_host}:{location_port}")
        print(f"Query Server: {query_host}:{query_port}")
        
        # 認証設定のテスト
        print("\n認証設定:")
        auth_enabled = config.get('auth', 'enable_auth', 'default')
        passphrase = config.get('auth', 'passphrase', 'default')
        
        print(f"Auth Enabled: {auth_enabled}")
        print(f"Passphrase: {passphrase}")
        
        # 環境変数が正しく展開されているかチェック
        if query_host == '${QUERY_GENERATOR_HOST}':
            print("❌ ERROR: 環境変数が展開されていません!")
            print(f"QUERY_GENERATOR_HOST環境変数: {os.getenv('QUERY_GENERATOR_HOST', 'NOT SET')}")
        else:
            print("✅ SUCCESS: 環境変数が正しく展開されました")
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
    
    # Query Serverの設定もテスト
    print("\n[Query Server Config Test]")
    try:
        config = ConfigLoader('WIP_Server/servers/query_server/config.ini')
        
        host = config.get('server', 'host', 'default')
        port = config.get('server', 'port', 'default')
        redis_host = config.get('redis', 'host', 'default')
        redis_port = config.get('redis', 'port', 'default')
        
        print(f"Host: {host}")
        print(f"Port: {port}")
        print(f"Redis: {redis_host}:{redis_port}")
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
    
    # Location Serverの設定もテスト
    print("\n[Location Server Config Test]")
    try:
        config = ConfigLoader('WIP_Server/servers/location_server/config.ini')
        
        host = config.get('server', 'host', 'default')
        port = config.get('server', 'port', 'default')
        db_host = config.get('database', 'host', 'default')
        db_port = config.get('database', 'port', 'default')
        
        print(f"Host: {host}")
        print(f"Port: {port}")
        print(f"Database: {db_host}:{db_port}")
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
    
    print("\n" + "=" * 50)
    print("テスト完了")

if __name__ == "__main__":
    test_config_loading()