#!/usr/bin/env python3
"""Generate a complete Unicode 17 four-letter keymap from the local block table.

Existing reviewed block tables and user anchors win. Remaining characters use
block-name-derived two-letter prefixes and deterministic shape-hint suffixes.
Large blocks may span several prefixes. Every exact code is capped at five
candidates.
"""

from __future__ import annotations

import csv
import math
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

from build_hieroglyph_block import MAIN_LABELS, STATE_LABELS
from build_unicode_selection import parse_unicode_data


PROJECT = Path(__file__).resolve().parents[1]
VAULT = PROJECT.parents[1]
FULL_TABLE = PROJECT / "数据" / "unicode全字符"
UCD = PROJECT / "数据" / "Unicode精选" / "UCD-17.0.0" / "UnicodeData.txt"
OUTPUT_DIR = PROJECT / "数据" / "Unicode全码表"
OUTPUT_TABLE = OUTPUT_DIR / "unicode-17-全字符编码.tsv"
OUTPUT_PAGES = OUTPUT_DIR / "unicode-17-前缀页.tsv"
MAX_PER_CODE = 5
MAX_PER_PREFIX = 26 * 26 * MAX_PER_CODE
LETTERS = "abcdefghijklmnopqrstuvwxyz"

LOCKED_TABLES = (
    PROJECT / "数据" / "𓆟字块-编码.tsv",
    PROJECT / "数据" / "ଉ字块-编码.tsv",
    PROJECT / "数据" / "ՊArmenian字块-编码.tsv",
    PROJECT / "数据" / "⦿数学符号B字块-编码.tsv",
    PROJECT / "数据" / "𒁔Cuneiform字块-编码.tsv",
    PROJECT / "数据" / "ஆTamil字块-编码.tsv",
)

# Four-letter anchors outside the fully managed block tables.
MANUAL_FOUR_CODES = {
    0x25CB: "yboe",  # ○
    0x25CC: "axde",  # ◌
    0x25CF: "fpof",  # ●
    0x15DA: "qdcg",  # ᗚ
    0x15E3: "lnte",  # ᗣ
    0x071C: "mcck",  # ܜ
    0x00A4: "qtrs",  # ¤
}

PAGE_OVERRIDES = {
    "jj": ("生命形", "Egyptian Hieroglyphs：人物、身体、动物、鸟与鱼"),
    "jn": ("自然", "Egyptian Hieroglyphs：自然、天地、水和植物"),
    "jw": ("器物", "Egyptian Hieroglyphs：器物、建筑和工具"),
    "jx": ("抽象", "Egyptian Hieroglyphs：图形、抽象与未分类"),
    "bo": ("奥里亚", "Odia / Oriya（U+0B00–U+0B7F）"),
    "as": ("亚美尼亚", "Armenian（U+0530–U+058F）"),
    "dd": ("数学符号 B", "Miscellaneous Mathematical Symbols-B（U+2980–U+29FF）"),
    "mv": ("楔形文字 I", "Cuneiform I（U+12000–U+120FF）"),
    "mu": ("楔形文字 II", "Cuneiform II（U+12100–U+121FF）"),
    "mn": ("楔形文字 III", "Cuneiform III（U+12200–U+122FF）"),
    "mw": ("楔形文字 IV", "Cuneiform IV（U+12300–U+12399）"),
    "pi": ("泰米尔", "Tamil（U+0B80–U+0BFF）"),
}

# User-confirmed block mnemonic prefixes. Reserve them before processing other
# blocks whose initials happen to collide.
BLOCK_PREFIX_OVERRIDES = {
    "Kirat Rai": "kr",
}


@dataclass(frozen=True)
class Block:
    name: str
    start: int
    end: int
    plane: str
    source: str
    codepoints: tuple[int, ...]


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def collect_blocks() -> list[Block]:
    blocks: list[Block] = []
    header = re.compile(r"^# (.+) U\+([0-9A-F]+)-U\+([0-9A-F]+)$")
    row = re.compile(r"^U\+([0-9A-F]+)\t")
    for path in sorted(path for path in FULL_TABLE.rglob("block-*.md") if "官方结构" not in path.parts):
        lines = path.read_text(encoding="utf-8").splitlines()
        match = header.match(lines[0])
        if not match:
            raise ValueError(f"无法解析区块标题：{path}")
        codepoints = tuple(int(found.group(1), 16) for line in lines[1:] if (found := row.match(line)))
        blocks.append(Block(
            name=match.group(1),
            start=int(match.group(2), 16),
            end=int(match.group(3), 16),
            plane=path.parent.name,
            source=path.relative_to(VAULT).as_posix(),
            codepoints=codepoints,
        ))
    if sum(len(block.codepoints) for block in blocks) != 159345:
        raise ValueError("本地 Unicode 全字符表不是预期的 159,345 个字符")
    return blocks


def locked_rows() -> dict[int, dict[str, str]]:
    locked: dict[int, dict[str, str]] = {}
    for path in LOCKED_TABLES:
        for row in read_tsv(path):
            codepoint = int(row["codepoint"][2:], 16)
            if codepoint in locked:
                raise ValueError(f"锁定码位重复：U+{codepoint:04X}")
            locked[codepoint] = row
    return locked


def preferred_prefix(name: str) -> str:
    words = re.findall(r"[A-Za-z]+", name.lower())
    if not words:
        return "ux"
    if len(words) >= 2:
        return words[0][0] + words[1][0]
    word = words[0]
    return (word + "x")[:2]


def prefix_candidates(name: str) -> list[str]:
    words = re.findall(r"[A-Za-z]+", name.lower()) or ["unicode"]
    base = preferred_prefix(name)
    candidates = [base]
    candidates.extend(words[0][0] + character for character in "".join(words)[1:])
    candidates.extend(a[0] + b[0] for index, a in enumerate(words) for b in words[index + 1:])
    candidates.extend(base[0] + character for character in LETTERS)
    candidates.extend(character + base[1] for character in LETTERS)
    candidates.extend(a + b for a in LETTERS for b in LETTERS)
    return list(dict.fromkeys(code for code in candidates if len(code) == 2 and code.isalpha()))


def keyword_key(name: str, mapping: tuple[tuple[tuple[str, ...], str], ...]) -> str | None:
    upper = name.upper()
    for words, key in mapping:
        if any(word in upper for word in words):
            return key
    return None


MAIN_HINTS = (
    (("CIRCLE", "RING", "ROUND"), "o"), (("DOT", "POINT"), "d"),
    (("LINE", "BAR", "STROKE"), "l"), (("ARC", "CURVE"), "c"),
    (("ANGLE", "CORNER"), "a"), (("TRIANGLE", "WEDGE"), "t"),
    (("SQUARE", "BOX", "RECTANGLE"), "s"), (("CROSS", "SALTIRE"), "x"),
    (("OPEN", "V-SHAPED"), "v"), (("STAR", "SUN", "RAY"), "r"),
    (("WAVE", "WAVY"), "w"), (("SPIRAL", "LOOP"), "p"),
    (("BLOCK", "FULL"), "b"), (("BRANCH", "TREE"), "h"),
)
STATE_HINTS = (
    (("WHITE", "HOLLOW"), "e"), (("BLACK", "FILLED", "SOLID"), "f"),
    (("WITH", "INSIDE", "ENCLOSED"), "i"), (("OPEN", "BROKEN"), "g"),
    (("PAIR", "DOUBLE", "TWO"), "p"), (("TRIPLE", "MULTIPLE"), "m"),
    (("UP", "UPWARDS", "NORTH"), "u"), (("DOWN", "DOWNWARDS", "SOUTH"), "d"),
    (("LEFT", "WEST"), "l"), (("RIGHT", "EAST"), "r"),
    (("HORIZONTAL",), "h"), (("VERTICAL",), "v"),
    (("CROSSING", "OVERLAY"), "x"), (("HOOK",), "k"),
)


def preferred_suffix(codepoint: int, name: str, category: str) -> tuple[str, str, str]:
    mixed = (codepoint * 2654435761 + 0x9E3779B9) & 0xFFFFFFFF
    main = keyword_key(name, MAIN_HINTS)
    state = keyword_key(name, STATE_HINTS)
    reason = "name-shape-hint" if main or state else "balanced-placeholder"
    if main is None:
        main = LETTERS[mixed % 26]
    if state is None:
        state = LETTERS[(mixed // 26 + ord(category[0])) % 26]
    return main, state, reason


def suffix_candidates(main: str, state: str, codepoint: int) -> list[str]:
    main_offset = (codepoint * 17) % 26
    state_offset = (codepoint * 29) % 26
    candidates = [main + state]
    candidates.extend(main + LETTERS[(state_offset + index) % 26] for index in range(26))
    candidates.extend(LETTERS[(main_offset + index) % 26] + state for index in range(26))
    start = (codepoint * 1315423911) % 676
    candidates.extend(LETTERS[((start + index) % 676) // 26] + LETTERS[(start + index) % 26] for index in range(676))
    return list(dict.fromkeys(candidates))


def build() -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    blocks = collect_blocks()
    ucd = {codepoint: (name, category) for codepoint, name, category in parse_unicode_data(UCD)}
    locked = locked_rows()
    all_codepoints = {codepoint for block in blocks for codepoint in block.codepoints}
    if set(locked) - all_codepoints:
        raise ValueError("锁定码表含有本地全字符表之外的码位")

    assignments: dict[int, str] = {}
    page_blocks: dict[str, list[tuple[Block, str]]] = defaultdict(list)
    page_members: dict[str, list[int]] = defaultdict(list)
    code_usage: dict[str, Counter[str]] = defaultdict(Counter)

    for codepoint, row in locked.items():
        prefix = row["prefix"]
        assignments[codepoint] = row["input_code"]
        page_members[prefix].append(codepoint)
        code_usage[prefix][row["input_code"][2:]] += 1
    for codepoint, code in MANUAL_FOUR_CODES.items():
        if codepoint in locked:
            continue
        prefix = code[:2]
        assignments[codepoint] = code
        page_members[prefix].append(codepoint)
        code_usage[prefix][code[2:]] += 1

    exclusive_prefixes = set(page_members)
    general_prefixes: set[str] = set()
    reserved_prefixes = {prefix: block for block, prefix in BLOCK_PREFIX_OVERRIDES.items()}
    fully_locked = set(locked)
    for block in blocks:
        remaining = [cp for cp in block.codepoints if cp not in fully_locked and cp not in MANUAL_FOUR_CODES]
        if not remaining:
            for prefix in sorted({locked[cp]["prefix"] for cp in block.codepoints}):
                page_blocks[prefix].append((block, "既有锁定码表"))
            continue
        cursor = 0
        candidates = prefix_candidates(block.name)
        if block.name in BLOCK_PREFIX_OVERRIDES:
            preferred = BLOCK_PREFIX_OVERRIDES[block.name]
            candidates = [preferred, *[prefix for prefix in candidates if prefix != preferred]]
        part = 1
        while cursor < len(remaining):
            chosen = None
            for prefix in candidates:
                # A generated page belongs to one Unicode block only. This
                # keeps large blocks on their own related prefixes instead of
                # filling unused capacity on an unrelated block's page.
                if prefix in exclusive_prefixes or prefix in general_prefixes:
                    continue
                if prefix in reserved_prefixes and reserved_prefixes[prefix] != block.name:
                    continue
                free = MAX_PER_PREFIX - len(page_members[prefix])
                if free > 0:
                    chosen = prefix
                    break
            if chosen is None:
                raise ValueError(f"没有可用前缀承载 {block.name}")
            general_prefixes.add(chosen)
            amount = min(MAX_PER_PREFIX - len(page_members[chosen]), len(remaining) - cursor)
            chunk = remaining[cursor:cursor + amount]
            page_members[chosen].extend(chunk)
            for codepoint in chunk:
                assignments[codepoint] = chosen
            label = block.name if len(remaining) <= amount and part == 1 else f"{block.name} · 分区 {part}"
            page_blocks[chosen].append((block, label))
            cursor += amount
            part += 1

    block_by_cp = {codepoint: block for block in blocks for codepoint in block.codepoints}
    rows: list[dict[str, str]] = []
    for prefix, members in page_members.items():
        for codepoint in sorted(members):
            name, category = ucd[codepoint]
            block = block_by_cp[codepoint]
            if codepoint in locked:
                source_row = locked[codepoint]
                code = source_row["input_code"]
                main_key, state_key = code[2], code[3]
                status = "managed-existing"
                allocation = source_row.get("classification_reason", "既有码表")
                source = source_row["source"]
            elif codepoint in MANUAL_FOUR_CODES:
                code = MANUAL_FOUR_CODES[codepoint]
                main_key, state_key = code[2], code[3]
                status = "manual-anchor"
                allocation = "用户指定四码"
                source = block.source
            else:
                preferred_main, preferred_state, reason = preferred_suffix(codepoint, name, category)
                selected = next(
                    suffix for suffix in suffix_candidates(preferred_main, preferred_state, codepoint)
                    if code_usage[prefix][suffix] < MAX_PER_CODE
                )
                code_usage[prefix][selected] += 1
                code = prefix + selected
                main_key, state_key = selected
                status = "machine-balanced-v1"
                allocation = reason if selected == preferred_main + preferred_state else reason + ";capacity-balanced"
                source = block.source
            rows.append({
                "char": chr(codepoint),
                "codepoint": f"U+{codepoint:04X}",
                "unicode_name": name,
                "category": category,
                "plane": block.plane,
                "block": block.name,
                "prefix": code[:2],
                "main_key": main_key,
                "main_shape": MAIN_LABELS[main_key],
                "state_key": state_key,
                "state_shape": STATE_LABELS[state_key],
                "input_code": code,
                "source": source,
                "status": status,
                "allocation": allocation,
            })

    rows.sort(key=lambda row: int(row["codepoint"][2:], 16))
    if len(rows) != 159345 or len({row["codepoint"] for row in rows}) != 159345:
        raise ValueError("统一码表未覆盖 159,345 个唯一字符")
    counts = Counter(row["input_code"] for row in rows)
    if max(counts.values()) > MAX_PER_CODE:
        raise ValueError("统一码表存在超过 5 个候选的四码")

    page_rows: list[dict[str, str]] = []
    for prefix, members in page_members.items():
        blocks_here = []
        for codepoint in members:
            name = block_by_cp[codepoint].name
            if name not in blocks_here:
                blocks_here.append(name)
        override = PAGE_OVERRIDES.get(prefix)
        display_name = override[0] if override else (blocks_here[0] if len(blocks_here) == 1 else f"{blocks_here[0]} 等 {len(blocks_here)} 区块")
        block_text = override[1] if override else "；".join(blocks_here)
        page_rows.append({
            "prefix": prefix,
            "name": display_name,
            "block": block_text,
            "description": f"{len(members):,} 个字符；{len(blocks_here)} 个 Unicode 区块；机器初稿可在编辑器中微调。",
            "character_count": str(len(members)),
            "start": f"U+{min(members):04X}",
            "end": f"U+{max(members):04X}",
            "block_count": str(len(blocks_here)),
            "allocation": "locked" if prefix in exclusive_prefixes else "block-initials-balanced",
        })
    page_rows.sort(key=lambda row: (int(row["start"][2:], 16), row["prefix"]))
    return rows, page_rows


def write() -> tuple[int, int]:
    rows, pages = build()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with OUTPUT_TABLE.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0].keys(), delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)
    with OUTPUT_PAGES.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=pages[0].keys(), delimiter="\t")
        writer.writeheader()
        writer.writerows(pages)
    return len(rows), len(pages)


def main() -> None:
    character_count, page_count = write()
    print(f"生成 {character_count:,} 个全量字符、{page_count} 个前缀页；每个四码最多 {MAX_PER_CODE} 个候选。")


if __name__ == "__main__":
    main()
