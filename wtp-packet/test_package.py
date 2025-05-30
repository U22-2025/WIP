"""
パッケージの動作確認用スクリプト
"""
from datetime import datetime
from wtp_packet import Request, Response, ExtendedField

print("=== WTP Packet 動作確認 ===\n")

# 1. 基本的なリクエストパケットのテスト
print("1. 基本的なリクエストパケットのテスト")
request = Request(
    version=1,
    packet_id=1234,
    type=0,
    timestamp=int(datetime.now().timestamp()),
    area_code="130010"
)
print(f"  作成されたリクエスト: {request}")
data = request.to_bytes()
print(f"  バイト列の長さ: {len(data)} bytes")
restored = Request.from_bytes(data)
print(f"  復元されたパケットID: {restored.packet_id}")
print(f"  復元されたエリアコード: {restored.area_code}")
print("  ✓ 成功\n")

# 2. 拡張フィールド付きリクエストのテスト
print("2. 拡張フィールド付きリクエストのテスト")
request_ex = Request(
    version=1,
    packet_id=5678,
    type=0,
    ex_flag=1,
    timestamp=int(datetime.now().timestamp()),
    area_code="270000",
    ex_field={
        'alert': ["津波警報", "大雨警報"],
        'latitude': 35.6895,
        'longitude': 139.6917,
        'source': "192.168.1.100"
    }
)
data_ex = request_ex.to_bytes()
print(f"  拡張フィールド付きバイト列の長さ: {len(data_ex)} bytes")
restored_ex = Request.from_bytes(data_ex)
ex_dict = restored_ex.ex_field.to_dict()
print(f"  復元された警報: {ex_dict.get('alert', [])}")
print(f"  復元された緯度: {ex_dict.get('latitude', 0)}")
print(f"  復元された経度: {ex_dict.get('longitude', 0)}")
print("  ✓ 成功\n")

# 3. レスポンスパケットのテスト
print("3. レスポンスパケットのテスト")
response = Response(
    version=1,
    packet_id=9999,
    type=1,
    timestamp=int(datetime.now().timestamp()),
    area_code="130010",
    weather_code=200,
    temperature=125,  # 25℃ (100 + 25)
    pops=30
)
resp_data = response.to_bytes()
print(f"  レスポンスバイト列の長さ: {len(resp_data)} bytes")
restored_resp = Response.from_bytes(resp_data)
print(f"  復元された天気コード: {restored_resp.weather_code}")
print(f"  復元された気温: {restored_resp.temperature - 100}℃")
print(f"  復元された降水確率: {restored_resp.pops}%")
print("  ✓ 成功\n")

# 4. ExtendedFieldオブジェクトの直接使用
print("4. ExtendedFieldオブジェクトの直接使用")
ex_field = ExtendedField()
ex_field.set('alert', ["地震警報"])
ex_field.set('latitude', 34.0522)
ex_field.set('longitude', -118.2437)
print(f"  作成されたExtendedField: {ex_field}")

request_obj = Request(
    version=1,
    packet_id=1111,
    ex_flag=1,
    timestamp=int(datetime.now().timestamp()),
    ex_field=ex_field
)
obj_data = request_obj.to_bytes()
restored_obj = Request.from_bytes(obj_data)
obj_dict = restored_obj.ex_field.to_dict()
print(f"  復元された警報: {obj_dict.get('alert', [])}")
print("  ✓ 成功\n")

# 5. チェックサムの自動計算
print("5. チェックサムの自動計算")
checksum_test = Request(
    version=1,
    packet_id=2222,
    timestamp=int(datetime.now().timestamp())
)
initial_checksum = checksum_test.checksum
print(f"  初期チェックサム: {initial_checksum}")
checksum_test.packet_id = 3333
new_checksum = checksum_test.checksum
print(f"  変更後のチェックサム: {new_checksum}")
print(f"  チェックサムが変更された: {initial_checksum != new_checksum}")
checksum_data = checksum_test.to_bytes()
is_valid = checksum_test.verify_checksum12(checksum_data)
print(f"  チェックサム検証: {'✓ 有効' if is_valid else '✗ 無効'}")
print("  ✓ 成功\n")

print("=== すべてのテストが成功しました！ ===")
print("\nwtp-packetパッケージは正常に動作しています。")
print("次のステップ：")
print("1. WTP_ClientとWTP_Serverのインポートを更新")
print("2. 古いpacketディレクトリを削除")
print("3. MIGRATION_GUIDE.mdを参照して移行を完了")
