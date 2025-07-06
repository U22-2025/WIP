import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from WIP_Client import Client
from dotenv import load_dotenv

# 環境変数を読み込み
load_dotenv()

print("=== 認証設定デバッグ ===")
print()

# 環境変数の確認
print("環境変数:")
auth_vars = [
    "WEATHER_SERVER_AUTH_ENABLED",
    "WEATHER_SERVER_PASSPHRASE",
    "LOCATION_SERVER_AUTH_ENABLED", 
    "LOCATION_SERVER_PASSPHRASE",
    "QUERY_SERVER_AUTH_ENABLED",
    "QUERY_SERVER_PASSPHRASE",
    "WEATHER_SERVER_RESPONSE_AUTH_ENABLED",
    "LOCATION_RESOLVER_RESPONSE_AUTH_ENABLED",
    "QUERY_GENERATOR_RESPONSE_AUTH_ENABLED"
]

for var in auth_vars:
    value = os.getenv(var)
    print(f"  {var}: {value}")

print()

# クライアントを作成
print("クライアント作成:")
client = Client(area_code=460010, debug=True)

print()
print("認証設定:")
for server_type in ['location', 'query', 'weather', 'report']:
    auth_config = client.state.get_auth_config(server_type)
    print(f"  {server_type}: enabled={auth_config.enabled}, has_passphrase={bool(auth_config.passphrase)}")

print()

# QueryRequestの作成と認証設定をテスト
print("QueryRequest認証設定テスト:")
from common.packet.query_packet import QueryRequest

request = QueryRequest.create_query_request(
    area_code=460010,
    packet_id=1234,
    weather=True,
    temperature=True,
    precipitation_prob=True,
    alert=True,
    disaster=True,
    day=0,
    version=1
)

print(f"リクエスト作成完了 - packet_id: {request.packet_id}")

# 認証設定前の状態
print("認証設定前:")
print(f"  request_auth: {request.request_auth}")
print(f"  response_auth: {request.response_auth}")
print(f"  ex_flag: {request.ex_flag}")
print(f"  auth_enabled: {request.is_auth_enabled()}")

# 認証設定を適用
client._setup_auth(request, 'query')

print("認証設定後:")
print(f"  request_auth: {request.request_auth}")
print(f"  response_auth: {request.response_auth}")
print(f"  ex_flag: {request.ex_flag}")
print(f"  auth_enabled: {request.is_auth_enabled()}")

if hasattr(request, 'ex_field') and request.ex_field:
    ex_dict = request.ex_field.to_dict()
    print(f"  拡張フィールド: {ex_dict}")
    if 'auth_hash' in ex_dict:
        print(f"  認証ハッシュ: {len(ex_dict['auth_hash'])} bytes")
else:
    print("  拡張フィールドなし")