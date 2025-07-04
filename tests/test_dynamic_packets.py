import json
from pathlib import Path

from common.packet.core.extended_field import (
    ExtendedField,
    ExtendedFieldType,
    reload_extended_spec,
)
from common.packet.core.format_base import FormatBase
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

    # 新フィールド付き拡張フィールドを作成し、ビット列変換
    ex = ExtendedField({"extra": "test"})
    bits = ex.to_bits()
    ex_restored = ExtendedField.from_bits(bits, 16 + len("test".encode("utf-8")) * 8)
    assert "extra" in ex_restored.to_dict()

    # 元に戻す
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

    FormatBase.reload_field_spec()
