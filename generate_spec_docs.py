#!/usr/bin/env python
"""format_spec の JSON 定義から Markdown ドキュメントを生成するスクリプト"""
from pathlib import Path
from common.packet.dynamic_format import (
    load_base_fields,
    load_extended_fields,
    load_response_fields,
)


HEADER = "# WIP フォーマット仕様\n"


def _table_from_dict(title: str, data: dict, key_label: str = "Name") -> list[str]:
    lines = [f"## {title}", "", f"| {key_label} | Length/ID | Type |", "|---|---:|---|"]
    for key, info in data.items():
        length = info.get("length")
        field_id = info.get("id")
        num = length if length is not None else field_id
        lines.append(f"| {key} | {num} | {info.get('type', '')} |")
    lines.append("")
    return lines


def generate_markdown(output: Path) -> None:
    req = load_base_fields()
    res = load_response_fields()
    ext = load_extended_fields()

    lines = [HEADER]
    lines += _table_from_dict("Request Fields", req)
    lines += _table_from_dict("Response Fields", res)
    lines += _table_from_dict("Extended Fields", ext, key_label="Field")

    output.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate format spec markdown")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("common/packet/format_spec/FORMAT_SPEC.md"),
        help="出力先 Markdown ファイル",
    )
    args = parser.parse_args()
    generate_markdown(args.output)
