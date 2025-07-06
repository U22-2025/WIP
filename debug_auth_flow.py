import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from WIP_Client import Client
from common.packet.query_packet import QueryRequest
from common.utils.auth import WIPAuth

print("=== 認証フローのデバッグ ===")
print()

# クライアントを作成
client = Client(area_code=460010, debug=True)

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

print(f"初期リクエスト:")
print(f"  packet_id: {request.packet_id}")
print(f"  timestamp: {request.timestamp}")

# 認証設定を適用
print("\n認証設定適用:")
client._setup_auth(request, 'query')

query_auth_config = client.state.get_auth_config('query')
print(f"Query server認証設定: enabled={query_auth_config.enabled}, passphrase={query_auth_config.passphrase}")

if request.is_auth_enabled():
    print(f"使用されたパスフレーズ: {request.get_auth_passphrase()}")
    
    # 手動で認証ハッシュを計算
    manual_hash = WIPAuth.calculate_auth_hash(
        request.packet_id,
        request.timestamp,
        request.get_auth_passphrase()
    )
    
    print(f"手動計算ハッシュ: {manual_hash.hex()}")
    
    if hasattr(request, 'ex_field') and request.ex_field:
        ex_dict = request.ex_field.to_dict()
        if 'auth_hash' in ex_dict:
            stored_hash = ex_dict['auth_hash']
            print(f"格納されたハッシュ: {stored_hash.hex()}")
            print(f"ハッシュ一致: {manual_hash == stored_hash}")

print()
print("Weather Server側で期待される認証:")
weather_auth_config = client.state.get_auth_config('weather')
print(f"Weather server認証設定: enabled={weather_auth_config.enabled}, passphrase={weather_auth_config.passphrase}")

if weather_auth_config.enabled and weather_auth_config.passphrase:
    # Weather Server側で計算されるであろうハッシュ
    weather_hash = WIPAuth.calculate_auth_hash(
        request.packet_id,
        request.timestamp,
        weather_auth_config.passphrase
    )
    print(f"Weather server期待ハッシュ: {weather_hash.hex()}")

print()
print("解決策の提案:")
print("1. クライアントはarea_codeを使ったリクエストの場合、最終的なweather serverのパスフレーズを使用すべき")
print("2. または、リクエストがweather serverに転送される際に認証情報を再計算すべき")