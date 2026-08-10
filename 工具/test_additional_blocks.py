#!/usr/bin/env python3
"""Validate generated Armenian, math-symbol, Cuneiform, and Tamil tables."""

from __future__ import annotations

import csv
from collections import Counter

from build_additional_blocks import BLOCKS, MAX_CANDIDATES, PROJECT


def main() -> None:
    for block in BLOCKS:
        with (PROJECT / "数据" / block.output).open(encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.DictReader(handle, delimiter="\t"))
        assert len(rows) == block.expected
        assert len({row["char"] for row in rows}) == block.expected
        allowed = {prefix for prefix, _, _ in block.prefix_ranges}
        assert all(row["prefix"] in allowed for row in rows)
        assert all(row["input_code"].startswith(row["prefix"]) and len(row["input_code"]) == 4 for row in rows)
        assert max(Counter(row["input_code"] for row in rows).values()) <= MAX_CANDIDATES
        anchor = next(row for row in rows if int(row["codepoint"][2:], 16) == block.anchor)
        assert anchor["input_code"] == block.anchor_code
    dictionary = PROJECT / "原型" / "rime" / "personal_unicode_symbols.dict.yaml"
    entries = [line.split("\t")[:2] for line in dictionary.read_text(encoding="utf-8").splitlines() if "\t" in line]
    codes = Counter(code for _, code in entries)
    assert len(entries) == 56891
    assert max(codes.values()) <= MAX_CANDIDATES
    assert len(set(map(tuple, entries))) == len(entries)
    anchors = {"Պ": "ascg", "⦿": "ddoi", "𒁔": "mvma", "ஆ": "pici", "ଉ": "boki"}
    for character, code in anchors.items():
        assert entries.count([character, code]) == 1
    print("四个新增 Unicode 字块校验通过。")


if __name__ == "__main__":
    main()
