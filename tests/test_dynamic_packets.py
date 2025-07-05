import json
from pathlib import Path

from common.packet.core.extended_field import (
    ExtendedField,
    ExtendedFieldType,
    reload_extended_spec,
)
from common.packet.core.format_base import FormatBase
from common.packet.models.request import Request
from common.packet.models.response import Response
from common.packet.types.location_packet import LocationRequest

from common.packet.examples import example_usage


def test_specialized_packet_after_reload():
    """JSON定義読み込み後も専用パケットクラスが動作するか確認"""
    reload_extended_spec()  # デフォルト定義を再読み込み
    packet_id = example_usage.PIDG.next_id()
    req = LocationRequest.create_coordinate_lookup(
        latitude=35.0,
        longitude=139.0,
        packet_id=packet_id,
    )
    packet_bytes = req.to_bytes()
    restored = LocationRequest.from_bytes(packet_bytes)
    assert restored.get_coordinates() == (35.0, 139.0)


def test_json_change_reflects_fields(tmp_path):
    """JSON変更によるフィールド追加が反映されるか確認"""
    # 元の定義を読み込み
    spec_path = Path(__file__).resolve().parents[1] / "common/packet/format_spec/extended_fields.json"
    with open(spec_path, "r", encoding="utf-8") as f:
        spec = json.load(f)

    # 新しいフィールドを追加
    spec["extra"] = 60
    new_path = tmp_path / "new_spec.json"
    with open(new_path, "w", encoding="utf-8") as f:
        json.dump(spec, f)

    # 新定義を読み込み
    reload_extended_spec(str(new_path))
    assert hasattr(ExtendedFieldType, "EXTRA")
    assert ExtendedFieldType.EXTRA == 60
    assert hasattr(ExtendedField, "extra")

    # 新フィールド付き拡張フィールドを作成し、ビット列変換
    ex = ExtendedField({"extra": "test"})
    assert ex.extra == "test"
    bits = ex.to_bits()
    ex_restored = ExtendedField.from_bits(bits, 16 + len("test".encode("utf-8")) * 8)
    assert "extra" in ex_restored.to_dict()

    # 元に戻す
    reload_extended_spec()


def test_request_accepts_new_extended_field(tmp_path):
    """Requestが新しい拡張フィールドを受け取れるか確認"""
    spec_path = Path(__file__).resolve().parents[1] / "common/packet/format_spec/extended_fields.json"
    with open(spec_path, "r", encoding="utf-8") as f:
        spec = json.load(f)

    spec["another"] = 61
    new_path = tmp_path / "req_ext.json"
    with open(new_path, "w", encoding="utf-8") as f:
        json.dump(spec, f)

    reload_extended_spec(str(new_path))
    req = Request(ex_flag=1, another="hello")
    assert req.ex_field.another == "hello"
    reload_extended_spec()


def test_reload_base_fields(tmp_path):
    """基本フィールド定義の再読み込みを確認"""
    spec_path = Path(__file__).resolve().parents[1] / "common/packet/format_spec/request_fields.json"
    with open(spec_path, "r", encoding="utf-8") as f:
        spec = json.load(f)

    spec["new_flag"] = 1
    new_path = tmp_path / "new_base.json"
    with open(new_path, "w", encoding="utf-8") as f:
        json.dump(spec, f)

    FormatBase.reload_field_spec(str(new_path))
    assert FormatBase.FIELD_LENGTH.get("new_flag") == 1
    assert "new_flag" in FormatBase._BIT_FIELDS
    assert hasattr(FormatBase, "new_flag")

    dummy_instance = FormatBase()
    dummy_instance.new_flag = 1
    assert dummy_instance.new_flag == 1

    expected_size = sum(spec.values()) // 8
    dummy = FormatBase.__new__(FormatBase)
    assert dummy.get_min_packet_size() == expected_size

    FormatBase.reload_field_spec()


def test_field_removal_cleans_properties(tmp_path):
    """フィールド削除時にプロパティが残らないことを確認"""
    spec_path = Path(__file__).resolve().parents[1] / "common/packet/format_spec/request_fields.json"
    with open(spec_path, "r", encoding="utf-8") as f:
        spec = json.load(f)

    spec.pop("reserved")
    new_path = tmp_path / "rm_base.json"
    with open(new_path, "w", encoding="utf-8") as f:
        json.dump(spec, f)

    FormatBase.reload_field_spec(str(new_path))
    assert not hasattr(FormatBase, "reserved")
    FormatBase.reload_field_spec()


def test_request_reload_updates_offset(tmp_path):
    """Request.reload_request_spec() が開始位置を再計算するか確認"""
    spec_path = Path(__file__).resolve().parents[1] / "common/packet/format_spec/request_fields.json"
    with open(spec_path, "r", encoding="utf-8") as f:
        spec = json.load(f)

    spec["dummy"] = 2
    new_path = tmp_path / "req_spec.json"
    with open(new_path, "w", encoding="utf-8") as f:
        json.dump(spec, f)

    FormatBase.reload_field_spec(str(new_path))
    Request.reload_request_spec()

    assert Request.VARIABLE_FIELD_START == sum(FormatBase.FIELD_LENGTH.values())

    FormatBase.reload_field_spec()
    Request.reload_request_spec()
    with open(spec_path, "r", encoding="utf-8") as f:
        orig_spec = json.load(f)
    original_size = sum(orig_spec.values()) // 8
    dummy = FormatBase.__new__(FormatBase)
    assert dummy.get_min_packet_size() == original_size


def test_min_packet_size_consistency():
    """Request/Responseクラスの最小サイズ計算を確認"""
    base_size = sum(FormatBase.FIELD_LENGTH.values()) // 8
    req = Request()
    res = Response()
    assert req.get_min_packet_size() == base_size
    fixed_size = sum(Response.FIXED_FIELD_LENGTH.values()) // 8
    assert res.get_min_packet_size() == base_size + fixed_size


def test_extended_field_removal_cleans_properties(tmp_path):
    """拡張フィールド削除時のプロパティ残存を確認"""
    spec_path = Path(__file__).resolve().parents[1] / "common/packet/format_spec/extended_fields.json"
    with open(spec_path, "r", encoding="utf-8") as f:
        spec = json.load(f)

    spec.pop("source")
    new_path = tmp_path / "rm_ext.json"
    with open(new_path, "w", encoding="utf-8") as f:
        json.dump(spec, f)

    reload_extended_spec(str(new_path))
    assert not hasattr(ExtendedFieldType, "SOURCE")
    assert not hasattr(ExtendedField, "source")
    reload_extended_spec()
