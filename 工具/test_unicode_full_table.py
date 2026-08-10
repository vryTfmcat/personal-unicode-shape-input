#!/usr/bin/env python3
"""Validate the generated minimal Unicode plane/block table."""

from __future__ import annotations

import re
from pathlib import Path

from build_unicode_full_table import OUTPUT_DIR, collect


ENTRY = re.compile(r"^U\+([0-9A-F]{4,6})\t", re.MULTILINE)


def main() -> int:
    grouped, expected_total = collect()
    files = sorted(OUTPUT_DIR.glob("plane-*/*.md"))
    assert files
    assert all(path.name.isascii() for path in files)
    assert len(files) == len(grouped)
    found = 0
    previous = -1
    for path in files:
        codepoints = [int(value, 16) for value in ENTRY.findall(path.read_text(encoding="utf-8"))]
        assert codepoints == sorted(codepoints)
        found += len(codepoints)
        previous = max(previous, codepoints[-1])
    assert found == expected_total
    odia = OUTPUT_DIR / "plane-00" / "block-u0b00-u0b7f-oriya.md"
    assert "U+0B09\tଉ" in odia.read_text(encoding="utf-8")
    print(f"unicode full table tests passed: {found} characters in {len(files)} blocks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
