#!/usr/bin/env python3
"""Validate the generated complete Unicode keymap."""

from __future__ import annotations

import csv
from collections import Counter

from build_all_unicode_keymap import LOCKED_TABLES, MAX_PER_CODE, OUTPUT_PAGES, OUTPUT_TABLE, read_tsv


def main() -> None:
    rows = read_tsv(OUTPUT_TABLE)
    pages = read_tsv(OUTPUT_PAGES)
    assert len(rows) == 159345
    assert len({row["codepoint"] for row in rows}) == 159345
    assert len(pages) <= 676
    assert all(len(row["input_code"]) == 4 and row["input_code"].islower() for row in rows)
    assert all(row["source"].startswith("30_项目/个人Unicode音型输入法/") for row in rows)
    counts = Counter(row["input_code"] for row in rows)
    assert max(counts.values()) <= MAX_PER_CODE
    by_cp = {int(row["codepoint"][2:], 16): row for row in rows}
    for path in LOCKED_TABLES:
        for locked in read_tsv(path):
            codepoint = int(locked["codepoint"][2:], 16)
            assert by_cp[codepoint]["input_code"] == locked["input_code"]
    anchors = {0x25CB: "yboe", 0x25CC: "axde", 0x25CF: "fpof", 0x15DA: "qdcg", 0x15E3: "lnte", 0x071C: "mcck", 0x00A4: "qtrs"}
    for codepoint, code in anchors.items():
        assert by_cp[codepoint]["input_code"] == code
    kirat = [row for row in rows if row["block"] == "Kirat Rai"]
    assert kirat and all(row["prefix"] == "kr" for row in kirat)
    print(f"全量 Unicode 码表校验通过：{len(rows):,} 字符，{len(pages)} 前缀页，{len(counts):,} 个唯一四码。")


if __name__ == "__main__":
    main()
