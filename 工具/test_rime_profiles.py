#!/usr/bin/env python3
"""Validate the split symbol, BMP Han, and full research dictionaries."""

from __future__ import annotations

from collections import Counter
import csv
from pathlib import Path
from reviewed_shapes import candidate_limit, REVIEWED_SHAPE_CODES


PROJECT = Path(__file__).resolve().parents[1]
RIME = PROJECT / "原型" / "rime"


def entries(name: str) -> list[tuple[str, str, int]]:
    path = RIME / f"{name}.dict.yaml"
    result = []
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        if "\t" not in line:
            continue
        display, code, weight = line.split("\t")[:3]
        result.append((display, code, int(weight)))
    return result


def validate(rows: list[tuple[str, str, int]]) -> None:
    assert len(rows) == len({(display, code) for display, code, _ in rows})
    assert all(2 <= len(code) <= 4 and code.isascii() and code.islower() for _, code, _ in rows)
    counts = Counter(code for _, code, _ in rows)
    assert all(count <= candidate_limit(code) for code, count in counts.items())
    assert all(weight in {1, 500, 1000} for _, _, weight in rows)


def main() -> None:
    symbols = entries("personal_unicode_symbols")
    han = entries("personal_unicode_han_bmp")
    full = entries("personal_unicode_full")
    validate(symbols); validate(han); validate(full)
    for char, code in REVIEWED_SHAPE_CODES.items():
        assert any(display == char and actual == code for display, actual, _ in symbols)
    assert len(symbols) == 56891
    assert len(han) == 28056
    assert len(full) == 159347
    symbol_chars = {display for display, _, _ in symbols}
    han_chars = {display for display, _, _ in han}
    full_chars = {display for display, _, _ in full}
    # A dictionary can contain every approved sample while still retaining
    # stale machine codes elsewhere. Check the entire generated base table.
    with (PROJECT / "数据" / "Unicode全码表" / "unicode-17-全字符编码.tsv").open(encoding="utf-8-sig", newline="") as handle:
        base_rows = list(csv.DictReader(handle, delimiter="\t"))
    for entries_, characters_ in ((symbols, symbol_chars), (han, han_chars), (full, full_chars)):
        pairs = {(display, code) for display, code, _ in entries_}
        assert all((row["char"], row["input_code"]) in pairs for row in base_rows if row["char"] in characters_)
    assert len(symbol_chars) == 56889
    assert len(han_chars) == 28056
    assert len(full_chars) == 159345
    assert not symbol_chars & han_chars
    assert symbol_chars | han_chars <= full_chars
    assert "○" in symbol_chars and "一" not in symbol_chars
    assert "一" in han_chars and "○" not in han_chars
    assert "𠀀" in full_chars and "𠀀" not in han_chars
    assert any(weight == 1000 for _, _, weight in symbols)
    schema = (RIME / "personal_unicode.schema.yaml").read_text(encoding="utf-8")
    han_schema = (RIME / "personal_unicode_han_bmp.schema.yaml").read_text(encoding="utf-8")
    assert "dictionary: personal_unicode_symbols" in schema
    assert "dictionary: personal_unicode_han_bmp" in han_schema
    print("Rime 分层词典校验通过。")


if __name__ == "__main__":
    main()
