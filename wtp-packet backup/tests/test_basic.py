"""
基本的なパケット機能のテスト
"""
import pytest
from datetime import datetime
from wtp_packet import Request, Response, ExtendedField, BitFieldError


def test_request_basic():
    """基本的なリクエストパケットのテスト"""
    # リクエストパケットの作成
    request = Request(
        version=1,
        packet_id=1234,
        type=0,
        timestamp=int(datetime.now().timestamp()),
        area_code="130010"
    )
    
    # バイト列への変換
    data = request.to_bytes()
    assert len(data) >= 32  # 最低32バイト
    
    # バイト列からの復元
    restored = Request.from_bytes(data)
    assert restored.version == 1
    assert restored.packet_id == 1234
    assert restored.type == 0
    assert restored.area_code == "130010"


def test_request_with_extended_field():
    """拡張フィールド付きリクエストパケットのテスト"""
    # 拡張フィールド付きリクエスト
    request = Request(
        version=1,
        packet_id=5678,
        type=0,
        ex_flag=1,
        timestamp=int(datetime.now().timestamp()),
        area_code="270000",
        ex_field={
            'alert': ["津波警報", "大雨警報"],
            'disaster': ["土砂崩れ"],
            'latitude': 35.6895,
            'longitude': 139.6917,
            'source': "192.168.1.100"
        }
    )
    
    # バイト列への変換と復元
    data = request.to_bytes()
    restored = Request.from_bytes(data)
    
    # 基本フィールドの確認
    assert restored.version == 1
    assert restored.packet_id == 5678
    assert restored.ex_flag == 1
    
    # 拡張フィールドの確認
    ex_dict = restored.ex_field.to_dict()
    assert 'alert' in ex_dict
    assert len(ex_dict['alert']) == 2
    assert "津波警報" in ex_dict['alert']
    assert "大雨警報" in ex_dict['alert']
    assert ex_dict['latitude'] == pytest.approx(35.6895, rel=1e-5)
    assert ex_dict['longitude'] == pytest.approx(139.6917, rel=1e-5)
    assert ex_dict['source'] == "192.168.1.100"


def test_response_basic():
    """基本的なレスポンスパケットのテスト"""
    # レスポンスパケットの作成
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
    
    # バイト列への変換
    data = response.to_bytes()
    
    # バイト列からの復元
    restored = Response.from_bytes(data)
    assert restored.version == 1
    assert restored.packet_id == 9999
    assert restored.type == 1
    assert restored.weather_code == 200
    assert restored.temperature == 125
    assert restored.pops == 30


def test_extended_field_object():
    """ExtendedFieldオブジェクトの直接使用テスト"""
    # ExtendedFieldオブジェクトの作成
    ex_field = ExtendedField()
    ex_field.set('alert', ["地震警報"])
    ex_field.set('latitude', 34.0522)
    ex_field.set('longitude', -118.2437)
    
    # リクエストに設定
    request = Request(
        version=1,
        packet_id=1111,
        ex_flag=1,
        timestamp=int(datetime.now().timestamp()),
        ex_field=ex_field  # ExtendedFieldオブジェクトを直接渡す
    )
    
    # 変換と確認
    data = request.to_bytes()
    restored = Request.from_bytes(data)
    
    ex_dict = restored.ex_field.to_dict()
    assert ex_dict['alert'] == ["地震警報"]
    assert ex_dict['latitude'] == pytest.approx(34.0522, rel=1e-5)
    assert ex_dict['longitude'] == pytest.approx(-118.2437, rel=1e-5)


def test_checksum_validation():
    """チェックサムの自動計算と検証のテスト"""
    # パケットの作成
    request = Request(
        version=1,
        packet_id=2222,
        timestamp=int(datetime.now().timestamp())
    )
    
    # チェックサムが自動計算される
    initial_checksum = request.checksum
    assert initial_checksum != 0
    
    # フィールドを変更するとチェックサムが再計算される
    request.packet_id = 3333
    assert request.checksum != initial_checksum
    
    # バイト列に変換して検証
    data = request.to_bytes()
    assert request.verify_checksum12(data)


def test_invalid_field_values():
    """不正なフィールド値のテスト"""
    # packet_idが範囲外
    with pytest.raises(BitFieldError):
        Request(packet_id=4096)  # 12ビットの最大値は4095
    
    # versionが範囲外
    with pytest.raises(BitFieldError):
        Request(version=16)  # 4ビットの最大値は15
    
    # 拡張フィールドの不正なキー
    with pytest.raises(ValueError):
        ex_field = ExtendedField()
        ex_field.set('invalid_key', "value")
    
    # 緯度が範囲外
    with pytest.raises(ValueError):
        ex_field = ExtendedField()
        ex_field.set('latitude', 91.0)  # -90～90の範囲外


def test_area_code_string_handling():
    """エリアコードの文字列処理テスト"""
    # 文字列として設定
    request = Request(area_code="001234")
    assert request.area_code == "001234"
    
    # 数値として設定
    request = Request(area_code=1234)
    assert request.area_code == "001234"  # 6桁にパディング
    
    # バイト列変換と復元
    data = request.to_bytes()
    restored = Request.from_bytes(data)
    assert restored.area_code == "001234"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
