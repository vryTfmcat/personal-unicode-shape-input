#!/usr/bin/env python3
"""Build the minimal plane/block/character Unicode table for Obsidian."""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path

from build_unicode_selection import UNICODE_VERSION, parse_property_file, parse_unicode_data


PROJECT = Path(__file__).resolve().parents[1]
UCD_DIR = PROJECT / "数据" / "Unicode精选" / f"UCD-{UNICODE_VERSION}"
OUTPUT_DIR = PROJECT / "数据" / "unicode全字符"
ALLOWED_CATEGORY_PREFIXES = {"L", "M", "N", "P", "S"}


def ascii_slug(value: str) -> str:
    return "-".join(re.findall(r"[A-Za-z0-9]+", value.lower())) or "unnamed"


def block_filename(start: int, end: int, name: str) -> str:
    return f"block-u{start:04x}-u{end:04x}-{ascii_slug(name)}.md"


def parse_blocks(path: Path) -> list[tuple[int, int, str]]:
    blocks: list[tuple[int, int, str]] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line or ";" not in line:
            continue
        span, name = (part.strip() for part in line.split(";", 1))
        start_text, end_text = (span.split("..") + [span])[:2]
        start = int(start_text, 16)
        end = int(end_text, 16)
        blocks.append((start, end, name))
    return blocks


def block_for(cp: int, blocks: list[tuple[int, int, str]]) -> tuple[int, int, str]:
    for block in blocks:
        if block[0] <= cp <= block[1]:
            return block
    raise ValueError(f"U+{cp:04X} is not covered by Blocks.txt")


def display_sample(char: str, category: str) -> str:
    return f"◌{char}" if category.startswith("M") else char


def collect() -> tuple[dict[tuple[int, int, str], list[tuple[int, str, str]]], int]:
    blocks = parse_blocks(UCD_DIR / "Blocks.txt")
    ignorables = parse_property_file(UCD_DIR / "DerivedCoreProperties.txt", "Default_Ignorable_Code_Point")
    assert isinstance(ignorables, set)
    grouped: dict[tuple[int, int, str], list[tuple[int, str, str]]] = defaultdict(list)
    total = 0
    for cp, _name, category in parse_unicode_data(UCD_DIR / "UnicodeData.txt"):
        if category[0] not in ALLOWED_CATEGORY_PREFIXES or cp in ignorables:
            continue
        grouped[block_for(cp, blocks)].append((cp, chr(cp), category))
        total += 1
    return grouped, total


def render_block(start: int, end: int, name: str, items: list[tuple[int, str, str]]) -> str:
    lines = [f"# {name} U+{start:04X}-U+{end:04X}", ""]
    lines.extend(f"U+{cp:04X}\t{display_sample(char, category)}" for cp, char, category in items)
    return "\n".join(lines) + "\n"


def build(output_dir: Path) -> dict[str, int]:
    if output_dir.exists() and any(output_dir.iterdir()):
        raise ValueError(f"输出目录不为空，拒绝覆盖：{output_dir}")
    grouped, total = collect()
    output_dir.mkdir(parents=True, exist_ok=True)
    files = 0
    planes: set[int] = set()
    for (start, end, name), items in sorted(grouped.items()):
        plane_set = {cp >> 16 for cp, _char, _category in items}
        if len(plane_set) != 1:
            raise ValueError(f"区块跨平面：{name}")
        plane = plane_set.pop()
        plane_dir = output_dir / f"plane-{plane:02d}"
        plane_dir.mkdir(exist_ok=True)
        target = plane_dir / block_filename(start, end, name)
        target.write_text(render_block(start, end, name, items), encoding="utf-8")
        files += 1
        planes.add(plane)
    return {"characters": total, "block_notes": files, "plane_folders": len(planes)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=OUTPUT_DIR)
    args = parser.parse_args()
    result = build(args.output)
    result["unicode_version"] = UNICODE_VERSION
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
