#!/usr/bin/env python3
"""Build the minimal official Unicode plane/block structure."""

from __future__ import annotations

import json
from pathlib import Path

from build_unicode_full_table import UCD_DIR, ascii_slug, parse_blocks


PROJECT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT / "数据" / "unicode全字符" / "官方结构"


def build() -> dict[str, int]:
    if OUTPUT_DIR.exists() and any(OUTPUT_DIR.iterdir()):
        raise ValueError(f"输出目录不为空，拒绝覆盖：{OUTPUT_DIR}")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    planes: set[int] = set()
    notes = 0
    for start, end, name in parse_blocks(UCD_DIR / "Blocks.txt"):
        plane = start >> 16
        if end >> 16 != plane:
            raise ValueError(f"官方区块跨平面：{name}")
        plane_dir = OUTPUT_DIR / f"plane-{plane:02d}"
        plane_dir.mkdir(exist_ok=True)
        filename = f"block-u{start:04x}-u{end:04x}-{ascii_slug(name)}.md"
        content = f"# {name}\n\nU+{start:04X}-U+{end:04X}\n"
        (plane_dir / filename).write_text(content, encoding="utf-8")
        planes.add(plane)
        notes += 1
    return {"plane_folders": len(planes), "block_notes": notes}


if __name__ == "__main__":
    print(json.dumps(build(), ensure_ascii=False, indent=2))
