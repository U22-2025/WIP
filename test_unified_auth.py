import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 統一されたパスフレーズを設定
UNIFIED_PASSPHRASE = "secure_key_2024"

# 環境変数を統一されたパスフレーズで設定
os.environ["WEATHER_SERVER_AUTH_ENABLED"] = "true"
os.environ["WEATHER_SERVER_PASSPHRASE"] = UNIFIED_PASSPHRASE
os.environ["LOCATION_SERVER_AUTH_ENABLED"] = "true"
os.environ["LOCATION_SERVER_PASSPHRASE"] = UNIFIED_PASSPHRASE
os.environ["QUERY_SERVER_AUTH_ENABLED"] = "true"
os.environ["QUERY_SERVER_PASSPHRASE"] = UNIFIED_PASSPHRASE
os.environ["REPORT_SERVER_AUTH_ENABLED"] = "true"
os.environ["REPORT_SERVER_PASSPHRASE"] = UNIFIED_PASSPHRASE

# レスポンス認証設定
os.environ["WEATHER_SERVER_RESPONSE_AUTH_ENABLED"] = "true"
os.environ["LOCATION_RESOLVER_RESPONSE_AUTH_ENABLED"] = "true"
os.environ["QUERY_GENERATOR_RESPONSE_AUTH_ENABLED"] = "true"
os.environ["REPORT_SERVER_RESPONSE_AUTH_ENABLED"] = "true"

from WIP_Client import Client
from common.packet.query_packet import QueryRequest
from common.utils.auth import WIPAuth

print("=== 統一認証テスト ===")
print(f"統一パスフレーズ: {UNIFIED_PASSPHRASE}")
print()

# クライアントを作成
client = Client(area_code=460010, debug=True)

# 認証設定の確認
print("認証設定確認:")
for server_type in ['location', 'query', 'weather', 'report']:
    auth_config = client.state.get_auth_config(server_type)
    print(f"  {server_type}: enabled={auth_config.enabled}, passphrase={auth_config.passphrase}")

print()

# QueryRequestを作成
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

print(f"リクエスト作成:")
print(f"  packet_id: {request.packet_id}")
print(f"  timestamp: {request.timestamp}")

# 認証設定を適用
print("\n認証設定適用:")
client._setup_auth(request, 'query')

print(f"使用されたパスフレーズ: {request.get_auth_passphrase()}")

# 全サーバーで同じパスフレーズを使用して認証ハッシュを計算
expected_hash = WIPAuth.calculate_auth_hash(
    request.packet_id,
    request.timestamp,
    UNIFIED_PASSPHRASE
)

if hasattr(request, 'ex_field') and request.ex_field:
    ex_dict = request.ex_field.to_dict()
    if 'auth_hash' in ex_dict:
        stored_hash = ex_dict['auth_hash']
        print(f"格納されたハッシュ: {stored_hash.hex()}")
        print(f"期待されるハッシュ: {expected_hash.hex()}")
        print(f"ハッシュ一致: {stored_hash == expected_hash}")

print()
print("今度は実際にクライアントでテストしてみます...")

# 実際のリクエストをテスト
result = client.get_weather(alert=True, disaster=True)

if result:
    print("✓ 成功！")
    print(result)
else:
    print("✗ 失敗")

client.close()