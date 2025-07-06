"""
WeatherServerの認証設定が正しく適用されているかテストするスクリプト
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 環境変数設定を確実に読み込む
from dotenv import load_dotenv
load_dotenv()

print("=== WeatherServer 認証設定テスト ===")
print("環境変数読み込み状況:")
print(f"QUERY_SERVER_REQUEST_AUTH_ENABLED: {os.getenv('QUERY_SERVER_REQUEST_AUTH_ENABLED')}")
print(f"LOCATION_SERVER_REQUEST_AUTH_ENABLED: {os.getenv('LOCATION_SERVER_REQUEST_AUTH_ENABLED')}")
print(f"QUERY_SERVER_PASSPHRASE: {os.getenv('QUERY_SERVER_PASSPHRASE')}")
print(f"LOCATION_SERVER_PASSPHRASE: {os.getenv('LOCATION_SERVER_PASSPHRASE')}")

try:
    from WIP_Server.servers.weather_server.weather_server import WeatherServer
    
    print("\nWeatherServerを初期化中...")
    server = WeatherServer(debug=True)
    
    print("\n=== 認証設定確認 ===")
    print(f"Query Server Request Auth Enabled: {server.query_server_request_auth_enabled}")
    print(f"Location Server Request Auth Enabled: {server.location_server_request_auth_enabled}")
    print(f"Query Server Passphrase: '{server.query_server_passphrase}'")
    print(f"Location Server Passphrase: '{server.location_server_passphrase}'")
    
    print("\n=== クライアント初期化状況確認 ===")
    print("QueryClient初期化:")
    if hasattr(server, 'query_client'):
        print(f"  ✓ QueryClient正常初期化")
        print(f"  Auth Enabled: {server.query_client.auth_enabled}")
        print(f"  Auth Passphrase: '{server.query_client.auth_passphrase}'")
    else:
        print("  ✗ QueryClient初期化失敗")
    
    print("LocationClient初期化:")
    if hasattr(server, 'location_client'):
        print(f"  ✓ LocationClient正常初期化")
        print(f"  Auth Enabled: {server.location_client.auth_enabled}")
        print(f"  Auth Passphrase: '{server.location_client.auth_passphrase}'")
    else:
        print("  ✗ LocationClient初期化失敗")
    
    print("\n✓ WeatherServer認証設定テスト完了")
    
except Exception as e:
    print(f"\n✗ エラー発生: {e}")
    import traceback
    traceback.print_exc()