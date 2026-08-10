#!/usr/bin/env python3
"""Validate the split symbol, BMP Han, and full research dictionaries."""

from __future__ import annotations

from collections import Counter
from pathlib import Path


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
    assert max(counts.values()) <= 5
    assert all(weight in {1, 500, 1000} for _, _, weight in rows)


def main() -> None:
    symbols = entries("personal_unicode_symbols")
    han = entries("personal_unicode_han_bmp")
    full = entries("personal_unicode_full")
    validate(symbols); validate(han); validate(full)
    assert len(symbols) == 56891
    assert len(han) == 28056
    assert len(full) == 159347
    symbol_chars = {display for display, _, _ in symbols}
    han_chars = {display for display, _, _ in han}
    full_chars = {display for display, _, _ in full}
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
