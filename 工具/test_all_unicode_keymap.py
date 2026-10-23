#!/usr/bin/env python3
"""Validate the generated complete Unicode keymap."""

from __future__ import annotations

import csv
from collections import Counter

from build_all_unicode_keymap import LOCKED_TABLES, MAX_PER_CODE, OUTPUT_PAGES, OUTPUT_TABLE, read_tsv, keyword_key, MAIN_HINTS, STATE_HINTS
from reviewed_shapes import REVIEWED_SHAPE_CODES, candidate_limit


def main() -> None:
    assert keyword_key("SUNDANESE PUNCTUATION BINDU SURYA", MAIN_HINTS) is None
    assert keyword_key("SUN", MAIN_HINTS) == "r"
    assert keyword_key("CUP", STATE_HINTS) is None
    assert keyword_key("UPWARDS ARROW", STATE_HINTS) == "u"
    assert keyword_key("V-SHAPED SYMBOL", MAIN_HINTS) == "v"
    rows = read_tsv(OUTPUT_TABLE)
    pages = read_tsv(OUTPUT_PAGES)
    assert len(rows) == 159345
    assert len({row["codepoint"] for row in rows}) == 159345
    assert len(pages) <= 676
    assert all(len(row["input_code"]) == 4 and row["input_code"].islower() for row in rows)
    assert all(row["source"].startswith("70_unicode/个人Unicode音型输入法/") for row in rows)
    counts = Counter(row["input_code"] for row in rows)
    assert all(count <= candidate_limit(code) for code, count in counts.items())
    assert candidate_limit("gsoe") == 10 and candidate_limit("zzzz") == 5
    by_cp = {int(row["codepoint"][2:], 16): row for row in rows}
    for char, code in REVIEWED_SHAPE_CODES.items():
        assert by_cp[ord(char)]["input_code"] == code
        assert by_cp[ord(char)]["status"] == "reviewed"
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
