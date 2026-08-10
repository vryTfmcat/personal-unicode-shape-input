#!/usr/bin/env python3
"""Build source inventories, a review queue, and a Rime dictionary.

The configured cold-archive paths are read-only inputs. Entity Markdown pages
and explicitly generated project block tables are editable Rime sources.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import unicodedata
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_VAULT_ROOT = PROJECT_ROOT.parents[1]

SOURCE_GROUPS = (
    (
        "字符候选：时间的方向/符号/𓆟",
        "symbol",
        Path("90_旧库冷归档/2025Obsidian备份_只读/时间的方向/符号/𓆟"),
    ),
    (
        "字符候选：时间的方向/符号/𓆟⊙",
        "symbol",
        Path("90_旧库冷归档/2025Obsidian备份_只读/时间的方向/符号/𓆟⊙"),
    ),
    (
        "字符候选：茂ܜ/符号/字符",
        "symbol",
        Path("90_旧库冷归档/Unicode原库_迁移前快照/茂ܜ/符号/字符"),
    ),
    (
        "字符候选：茂ܜ/符号/自创语",
        "symbol",
        Path("90_旧库冷归档/Unicode原库_迁移前快照/茂ܜ/符号/自创语"),
    ),
    (
        "词汇候选：茂ܜ/词汇",
        "term",
        Path("90_旧库冷归档/Unicode原库_迁移前快照/茂ܜ/词汇"),
    ),
)

REQUIRED_FIELDS = {
    "id",
    "type",
    "display",
    "codepoints",
    "input_code",
    "mnemonic",
    "shape_tags",
    "status",
    "export_to_rime",
    "sources",
    "note",
}
VALID_TYPES = {"character", "sequence", "term"}
VALID_STATUSES = {"candidate", "active", "deferred"}
HIEROGLYPH_BLOCK_TABLE = PROJECT_ROOT / "数据" / "𓆟字块-编码.tsv"
ODIA_BLOCK_TABLE = PROJECT_ROOT / "数据" / "ଉ字块-编码.tsv"
ADDITIONAL_BLOCK_TABLES = (
    ("ՊArmenian字块-编码.tsv", (("as", 0x0530, 0x058F),), 91, 0x054A, "Armenian"),
    ("⦿数学符号B字块-编码.tsv", (("dd", 0x2980, 0x29FF),), 128, 0x29BF, "数学符号B"),
    ("𒁔Cuneiform字块-编码.tsv", (("mv", 0x12000, 0x120FF), ("mu", 0x12100, 0x121FF), ("mn", 0x12200, 0x122FF), ("mw", 0x12300, 0x12399)), 922, 0x12054, "Cuneiform"),
    ("ஆTamil字块-编码.tsv", (("pi", 0x0B80, 0x0BFF),), 72, 0x0B86, "Tamil"),
)
ALL_UNICODE_TABLE = PROJECT_ROOT / "数据" / "Unicode全码表" / "unicode-17-全字符编码.tsv"
ALL_UNICODE_PAGES = PROJECT_ROOT / "数据" / "Unicode全码表" / "unicode-17-前缀页.tsv"
ASSOCIATION_GRAPH = PROJECT_ROOT / "数据" / "联想图谱" / "association-graph.json"
RIME_DIR = PROJECT_ROOT / "原型" / "rime"
RIME_OUTPUTS = {
    "symbols": ("personal_unicode_symbols", RIME_DIR / "personal_unicode_symbols.dict.yaml"),
    "han-bmp": ("personal_unicode_han_bmp", RIME_DIR / "personal_unicode_han_bmp.dict.yaml"),
    "full": ("personal_unicode_full", RIME_DIR / "personal_unicode_full.dict.yaml"),
}


@dataclass(frozen=True)
class SourceNote:
    group: str
    kind: str
    path: str
    title: str
    sequences: tuple[str, ...]


def markdown_files(root: Path) -> list[Path]:
    return sorted(
        path
        for path in root.rglob("*.md")
        if path.is_file() and not path.name.startswith("._")
    )


def is_cjk(character: str) -> bool:
    codepoint = ord(character)
    return (
        0x3400 <= codepoint <= 0x4DBF
        or 0x4E00 <= codepoint <= 0x9FFF
        or 0xF900 <= codepoint <= 0xFAFF
        or 0x20000 <= codepoint <= 0x2EBEF
    )


def is_unicode_candidate_character(character: str) -> bool:
    """Keep uncommon scripts, modifiers, numbers, and symbols; reject Han text."""
    if ord(character) <= 0x7F or is_cjk(character):
        return False
    return unicodedata.category(character)[0] in {"L", "M", "N", "S"}


def cleaned_title(title: str) -> str:
    title = unicodedata.normalize("NFC", title.strip())
    return re.sub(r"\s*[（(]\d+[)）]\s*$", "", title)


def extract_symbol_sequences(title: str) -> tuple[str, ...]:
    """Extract title fragments that contain a non-ASCII Unicode candidate.

    This deliberately favors recall over precision. The resulting list is a
    human review queue, never an automatic input-method dictionary.
    """
    title = cleaned_title(title)
    fragments: list[str] = []
    current: list[str] = []

    def flush() -> None:
        if any(is_unicode_candidate_character(character) for character in current):
            fragment = "".join(current).strip(" ._-，,;；：:")
            if fragment:
                fragments.append(unicodedata.normalize("NFC", fragment))
        current.clear()

    for character in title:
        if is_cjk(character) or character.isspace() or character.isascii() and character.isalnum():
            flush()
            continue
        current.append(character)
    flush()
    return tuple(dict.fromkeys(fragments))


def collect_sources(vault_root: Path) -> tuple[list[SourceNote], dict[str, int]]:
    notes: list[SourceNote] = []
    counts: dict[str, int] = {}
    for group, kind, relative_root in SOURCE_GROUPS:
        root = vault_root / relative_root
        if not root.is_dir():
            raise FileNotFoundError(f"配置的来源目录不存在：{relative_root}")
        files = markdown_files(root)
        counts[group] = len(files)
        for path in files:
            title = path.stem
            sequences = extract_symbol_sequences(title) if kind == "symbol" else ()
            notes.append(
                SourceNote(
                    group=group,
                    kind=kind,
                    path=path.relative_to(vault_root).as_posix(),
                    title=title,
                    sequences=sequences,
                )
            )
    return notes, counts


def codepoints(text: str) -> list[str]:
    return [f"U+{ord(character):04X}" for character in text]


def markdown_escape(text: str) -> str:
    return text.replace("`", "'").replace("\n", " ")


def source_manifest(notes: list[SourceNote], counts: dict[str, int]) -> str:
    lines = ["# 限定来源清单", "", "本清单由 `工具/build_catalog.py` 生成。它只列出获准扫描的来源，冷归档未被改写。", ""]
    lines.append("## 统计")
    for group, count in counts.items():
        lines.append(f"- {group}：{count} 篇 Markdown")
    lines.extend(["", "## 文件", ""])
    for note in notes:
        extracted = "、".join(f"`{markdown_escape(item)}`" for item in note.sequences) or "无自动字符候选"
        lines.extend(
            [
                f"### {markdown_escape(note.title)}",
                f"- 分类：{note.group}",
                f"- 来源：`{note.path}`",
                f"- 自动候选：{extracted}",
                "",
            ]
        )
    return "\n".join(lines) + "\n"


def candidate_report(notes: list[SourceNote], counts: dict[str, int], records: list[dict[str, Any]]) -> str:
    symbols: dict[str, list[SourceNote]] = defaultdict(list)
    terms: list[SourceNote] = []
    for note in notes:
        if note.kind == "term":
            terms.append(note)
        else:
            for sequence in note.sequences:
                symbols[sequence].append(note)
    active_codes = {
        str(record["display"]): str(record["input_code"])
        for record in records
        if record["status"] == "active" and record["export_to_rime"]
    }

    lines = [
        "# 个人 Unicode 音型输入法：首批待确认候选",
        "",
        "生成时间不作为事实字段维护；每次运行 `工具/build_catalog.py --write` 会按当前限定来源重建本清单。",
        "冷归档保持只读。自动提取仅供筛选，不能直接进入实体页或 Rime 词典。",
        "",
        "## 来源统计",
    ]
    for group, count in counts.items():
        lines.append(f"- {group}：{count} 篇 Markdown")
    lines.extend(["", f"## 字符与符号组合候选（{len(symbols)} 项）", ""])
    for sequence, sources in sorted(symbols.items(), key=lambda pair: (len(pair[0]), pair[0])):
        candidate_type = "字符" if len(sequence) == 1 else "符号组合"
        lines.extend(
            [
                f"### `{markdown_escape(sequence)}`",
                f"- 建议类别：{candidate_type}",
                f"- 码位：{', '.join(codepoints(sequence))}",
                f"- 来源数：{len(sources)}",
            ]
        )
        for source in sources:
            lines.append(f"- 来源：`{source.path}`")
        if sequence in active_codes:
            lines.append(f"- 确认状态：已确认并导出，输入码：`{active_codes[sequence]}`")
        else:
            lines.append("- 确认状态：待确认")
        lines.append("")
    lines.extend([f"## 词汇候选（{len(terms)} 项）", ""])
    for term in sorted(terms, key=lambda item: item.title):
        status = "待确认"
        if term.title in active_codes:
            status = f"已确认并导出，输入码：`{active_codes[term.title]}`"
        lines.extend(
            [
                f"### {markdown_escape(term.title)}",
                "- 建议类别：词汇",
                f"- 来源：`{term.path}`",
                "- 默认导出到 Rime：否",
                f"- 确认状态：{status}",
                "",
            ]
        )
    return "\n".join(lines) + "\n"


def parse_scalar(value: str) -> Any:
    value = value.strip()
    if value in {"true", "false"}:
        return value == "true"
    if value.startswith("[") and value.endswith("]"):
        return json.loads(value)
    if value.startswith('"') and value.endswith('"'):
        return json.loads(value)
    return value


def parse_frontmatter(path: Path) -> dict[str, Any]:
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0] != "---":
        raise ValueError("缺少 YAML frontmatter")
    try:
        end = lines.index("---", 1)
    except ValueError as error:
        raise ValueError("frontmatter 未闭合") from error
    result: dict[str, Any] = {}
    index = 1
    while index < end:
        line = lines[index]
        if not line.strip():
            index += 1
            continue
        if ":" not in line or line.startswith(" "):
            raise ValueError(f"无法解析 frontmatter 行：{line}")
        key, raw_value = line.split(":", 1)
        value = raw_value.strip()
        if value:
            result[key] = parse_scalar(value)
            index += 1
            continue
        values: list[str] = []
        index += 1
        while index < end and lines[index].startswith("  - "):
            values.append(str(parse_scalar(lines[index][4:])))
            index += 1
        result[key] = values
    return result


def is_valid_input_code(code: str) -> bool:
    return bool(re.fullmatch(r"[a-z]{2,4}", code))


def entity_files(project_root: Path) -> list[Path]:
    roots = [project_root / "实体" / name for name in ("字符", "符号组合", "词汇")]
    return sorted(path for root in roots for path in root.glob("*.md") if path.is_file())


def validate_entities(project_root: Path, vault_root: Path) -> tuple[list[dict[str, Any]], list[str], dict[str, list[str]]]:
    records: list[dict[str, Any]] = []
    errors: list[str] = []
    codes: dict[str, list[str]] = defaultdict(list)
    for path in entity_files(project_root):
        try:
            record = parse_frontmatter(path)
        except (OSError, ValueError, json.JSONDecodeError) as error:
            errors.append(f"{path.relative_to(project_root)}：{error}")
            continue
        missing = REQUIRED_FIELDS - record.keys()
        if missing:
            errors.append(f"{path.relative_to(project_root)}：缺少字段 {', '.join(sorted(missing))}")
            continue
        label = str(path.relative_to(project_root))
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", str(record["id"])):
            errors.append(f"{label}：id 必须为稳定 ASCII 标识")
        if record["type"] not in VALID_TYPES:
            errors.append(f"{label}：type 无效")
        if record["status"] not in VALID_STATUSES:
            errors.append(f"{label}：status 无效")
        if not isinstance(record["codepoints"], list) or not isinstance(record["shape_tags"], list) or not isinstance(record["sources"], list):
            errors.append(f"{label}：codepoints、shape_tags、sources 必须为列表")
        if not isinstance(record["export_to_rime"], bool):
            errors.append(f"{label}：export_to_rime 必须为布尔值")
        if not record["sources"]:
            errors.append(f"{label}：sources 不能为空")
        for source in record["sources"]:
            if not (vault_root / source).is_file():
                errors.append(f"{label}：来源不存在：{source}")
        if record["type"] in {"character", "sequence"}:
            expected = codepoints(str(record["display"]))
            if record["codepoints"] != expected:
                errors.append(f"{label}：codepoints 必须与 display 完全一致")
            if record["type"] == "character" and len(str(record["display"])) != 1:
                errors.append(f"{label}：character 必须只包含一个 Unicode 标量")
        elif record["codepoints"]:
            errors.append(f"{label}：term 的 codepoints 必须为空列表")
        code = str(record["input_code"])
        if code and not is_valid_input_code(code):
            errors.append(f"{label}：input_code 必须为空或 2 至 4 个小写字母")
        if record["export_to_rime"]:
            if record["status"] != "active" or not is_valid_input_code(code):
                errors.append(f"{label}：导出到 Rime 的条目必须 active 且填写 2 至 4 位码")
            codes[code].append(label)
        aliases = record.get("input_aliases", [])
        association_ids = record.get("association_ids", [])
        if not isinstance(aliases, list) or not isinstance(association_ids, list):
            errors.append(f"{label}：input_aliases 与 association_ids 必须为列表")
            aliases = []
        valid_aliases: list[str] = []
        for alias in aliases:
            alias = str(alias)
            if not is_valid_input_code(alias):
                errors.append(f"{label}：无效 input_aliases：{alias}")
                continue
            if alias == code or alias in valid_aliases:
                continue
            valid_aliases.append(alias)
            if record["export_to_rime"]:
                codes[alias].append(label + "（别名）")
        record["catalog_origin"] = "实体主码"
        records.append(record)
        if record["export_to_rime"] and record["status"] == "active":
            for alias in valid_aliases:
                alias_record = dict(record)
                alias_record["input_code"] = alias
                alias_record["catalog_origin"] = "实体别名"
                alias_record["note"] = f"实体页启用别名；{record.get('note', '')}"
                records.append(alias_record)
    collisions = {code: labels for code, labels in codes.items() if len(labels) > 1}
    return records, errors, collisions


def load_hieroglyph_block(vault_root: Path) -> tuple[list[dict[str, Any]], list[str]]:
    records: list[dict[str, Any]] = []
    errors: list[str] = []
    if not HIEROGLYPH_BLOCK_TABLE.is_file():
        return records, ["数据/𓆟字块-编码.tsv：文件不存在，请先运行 build_hieroglyph_block.py"]
    with HIEROGLYPH_BLOCK_TABLE.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    required = {"char", "codepoint", "input_code", "main_key", "state_key", "source", "status"}
    if not rows:
        return records, ["数据/𓆟字块-编码.tsv：没有条目"]
    missing = required - rows[0].keys()
    if missing:
        return records, [f"数据/𓆟字块-编码.tsv：缺少列 {', '.join(sorted(missing))}"]
    seen: set[str] = set()
    for line_number, row in enumerate(rows, 2):
        label = f"数据/𓆟字块-编码.tsv:{line_number}"
        character = row["char"]
        code = row["input_code"]
        if len(character) != 1 or not 0x13000 <= ord(character) <= 0x1342F:
            errors.append(f"{label}：char 不是埃及象形文字单一标量")
            continue
        if character in seen:
            errors.append(f"{label}：字符重复 {character}")
        seen.add(character)
        if row["codepoint"] != f"U+{ord(character):04X}":
            errors.append(f"{label}：codepoint 与字符不一致")
        if row["prefix"] not in {"jj", "jn", "jw", "jx"}:
            errors.append(f"{label}：prefix 必须为 jj、jn、jw 或 jx")
        if not is_valid_input_code(code) or len(code) != 4 or not code.startswith(row["prefix"]):
            errors.append(f"{label}：input_code 必须以前缀列开头并使用四个小写字母")
        if code != row["prefix"] + row["main_key"] + row["state_key"]:
            errors.append(f"{label}：input_code 与 main_key/state_key 不一致")
        source = row["source"]
        if not (vault_root / source).is_file():
            errors.append(f"{label}：来源不存在：{source}")
        if row["status"] not in {"machine-initial-v3", "reviewed"}:
            errors.append(f"{label}：status 必须为 machine-initial-v3 或 reviewed")
        records.append({
            "id": f"hieroglyph-{ord(character):05x}",
            "type": "character",
            "display": character,
            "codepoints": [row["codepoint"]],
            "input_code": code,
            "mnemonic": "𓆟字块",
            "shape_tags": [row["main_key"], row["state_key"]],
            "status": "active",
            "export_to_rime": True,
            "sources": [source],
            "note": f"{row['status']}；{row.get('classification_reason', '')}",
            "catalog_origin": "𓆟字块",
        })
    if len(records) != 1072:
        errors.append(f"数据/𓆟字块-编码.tsv：预期 1072 条，实际 {len(records)} 条")
    return records, errors


def load_odia_block(vault_root: Path) -> tuple[list[dict[str, Any]], list[str]]:
    records: list[dict[str, Any]] = []
    errors: list[str] = []
    if not ODIA_BLOCK_TABLE.is_file():
        return records, ["数据/ଉ字块-编码.tsv：文件不存在，请先运行 build_odia_block.py"]
    with ODIA_BLOCK_TABLE.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    required = {"char", "codepoint", "input_code", "main_key", "state_key", "source", "status"}
    if len(rows) != 91:
        errors.append(f"数据/ଉ字块-编码.tsv：预期 91 条，实际 {len(rows)} 条")
    if rows and required - rows[0].keys():
        return records, [f"数据/ଉ字块-编码.tsv：缺少列 {', '.join(sorted(required - rows[0].keys()))}"]
    seen: set[str] = set()
    for line_number, row in enumerate(rows, 2):
        label = f"数据/ଉ字块-编码.tsv:{line_number}"
        character = row["char"]
        code = row["input_code"]
        if len(character) != 1 or not 0x0B00 <= ord(character) <= 0x0B7F:
            errors.append(f"{label}：char 不是奥里亚区块单一标量")
            continue
        if character in seen:
            errors.append(f"{label}：字符重复 {character}")
        seen.add(character)
        if row["codepoint"] != f"U+{ord(character):04X}":
            errors.append(f"{label}：codepoint 与字符不一致")
        if row["prefix"] != "bo" or code != "bo" + row["main_key"] + row["state_key"]:
            errors.append(f"{label}：input_code 必须为 bo 加两位形态键")
        if not is_valid_input_code(code) or len(code) != 4:
            errors.append(f"{label}：input_code 必须为四个小写字母")
        source = row["source"]
        if not (vault_root / source).is_file():
            errors.append(f"{label}：来源不存在：{source}")
        if row["status"] not in {"machine-initial-v1", "reviewed"}:
            errors.append(f"{label}：status 必须为 machine-initial-v1 或 reviewed")
        # U+0B09 is already supplied by its manually managed entity page.
        if ord(character) == 0x0B09:
            continue
        records.append({
            "id": f"odia-{ord(character):04x}",
            "type": "character",
            "display": character,
            "codepoints": [row["codepoint"]],
            "input_code": code,
            "mnemonic": "ଉ字块",
            "shape_tags": [row["main_key"], row["state_key"]],
            "status": "active",
            "export_to_rime": True,
            "sources": [source],
            "note": f"{row['status']}；{row.get('classification_reason', '')}",
            "catalog_origin": "ଉ字块",
        })
    return records, errors


def load_additional_blocks(vault_root: Path) -> tuple[list[dict[str, Any]], list[str], dict[str, int]]:
    records: list[dict[str, Any]] = []
    errors: list[str] = []
    counts: dict[str, int] = {}
    required = {"char", "codepoint", "input_code", "main_key", "state_key", "source", "status", "prefix"}
    for filename, prefix_ranges, expected, anchor, block_name in ADDITIONAL_BLOCK_TABLES:
        path = PROJECT_ROOT / "数据" / filename
        if not path.is_file():
            errors.append(f"数据/{filename}：文件不存在，请先运行 build_additional_blocks.py")
            continue
        with path.open(encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.DictReader(handle, delimiter="\t"))
        for prefix, start, end in prefix_ranges:
            counts[prefix] = sum(1 for row in rows if row.get("prefix") == prefix)
        if len(rows) != expected:
            errors.append(f"数据/{filename}：预期 {expected} 条，实际 {len(rows)} 条")
        if rows and required - rows[0].keys():
            errors.append(f"数据/{filename}：缺少列 {', '.join(sorted(required - rows[0].keys()))}")
            continue
        seen: set[str] = set()
        for line_number, row in enumerate(rows, 2):
            label = f"数据/{filename}:{line_number}"
            character = row["char"]
            code = row["input_code"]
            matching_ranges = [(prefix, start, end) for prefix, start, end in prefix_ranges if start <= ord(character) <= end]
            if len(character) != 1 or len(matching_ranges) != 1:
                errors.append(f"{label}：char 不是 {block_name} 区块单一标量")
                continue
            prefix = matching_ranges[0][0]
            if character in seen:
                errors.append(f"{label}：字符重复 {character}")
            seen.add(character)
            if row["codepoint"] != f"U+{ord(character):04X}":
                errors.append(f"{label}：codepoint 与字符不一致")
            if row["prefix"] != prefix or code != prefix + row["main_key"] + row["state_key"]:
                errors.append(f"{label}：input_code 必须为 {prefix} 加两位形态键")
            if not is_valid_input_code(code) or len(code) != 4:
                errors.append(f"{label}：input_code 必须为四个小写字母")
            source = row["source"]
            if not (vault_root / source).is_file():
                errors.append(f"{label}：来源不存在：{source}")
            if row["status"] not in {"machine-initial-v1", "reviewed"}:
                errors.append(f"{label}：status 必须为 machine-initial-v1 或 reviewed")
            # The user-managed entity page supplies the anchor with the same code.
            if ord(character) == anchor:
                continue
            records.append({
                "id": f"block-{prefix}-{ord(character):05x}",
                "type": "character",
                "display": character,
                "codepoints": [row["codepoint"]],
                "input_code": code,
                "mnemonic": f"{block_name}字块",
                "shape_tags": [row["main_key"], row["state_key"]],
                "status": "active",
                "export_to_rime": True,
                "sources": [source],
                "note": f"{row['status']}；{row.get('classification_reason', '')}",
                "catalog_origin": f"{prefix}字块",
            })
    return records, errors, counts


def load_all_unicode_table(vault_root: Path) -> tuple[list[dict[str, Any]], list[str], int]:
    records: list[dict[str, Any]] = []
    errors: list[str] = []
    if not ALL_UNICODE_TABLE.is_file() or not ALL_UNICODE_PAGES.is_file():
        return records, ["数据/Unicode全码表：全量码表不存在，请先运行 build_all_unicode_keymap.py"], 0
    with ALL_UNICODE_TABLE.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    with ALL_UNICODE_PAGES.open(encoding="utf-8-sig", newline="") as handle:
        pages = list(csv.DictReader(handle, delimiter="\t"))
    required = {"char", "codepoint", "input_code", "main_key", "state_key", "source", "status", "prefix", "block"}
    if len(rows) != 159345:
        errors.append(f"数据/Unicode全码表：预期 159345 条，实际 {len(rows)} 条")
    if rows and required - rows[0].keys():
        return records, [f"数据/Unicode全码表：缺少列 {', '.join(sorted(required - rows[0].keys()))}"], len(pages)
    page_prefixes = {page["prefix"] for page in pages}
    seen: set[int] = set()
    source_exists: dict[str, bool] = {}
    code_counts: dict[str, int] = defaultdict(int)
    for line_number, row in enumerate(rows, 2):
        label = f"数据/Unicode全码表/unicode-17-全字符编码.tsv:{line_number}"
        character = row["char"]
        if len(character) != 1:
            errors.append(f"{label}：char 不是单一 Unicode 标量")
            continue
        codepoint = ord(character)
        code = row["input_code"]
        if codepoint in seen:
            errors.append(f"{label}：字符重复 U+{codepoint:04X}")
        seen.add(codepoint)
        if row["codepoint"] != f"U+{codepoint:04X}":
            errors.append(f"{label}：codepoint 与字符不一致")
        if row["prefix"] not in page_prefixes:
            errors.append(f"{label}：prefix 不在前缀页清单中")
        if not is_valid_input_code(code) or len(code) != 4 or code != row["prefix"] + row["main_key"] + row["state_key"]:
            errors.append(f"{label}：input_code 必须为前缀加两位形态键")
        code_counts[code] += 1
        source = row["source"]
        if source not in source_exists:
            source_exists[source] = (vault_root / source).is_file()
        if not source_exists[source]:
            errors.append(f"{label}：来源不存在：{source}")
        if row["status"] not in {"managed-existing", "manual-anchor", "machine-balanced-v1", "reviewed"}:
            errors.append(f"{label}：未知状态 {row['status']}")
        records.append({
            "id": f"unicode-{codepoint:06x}",
            "type": "character",
            "display": character,
            "codepoints": [row["codepoint"]],
            "input_code": code,
            "mnemonic": row["block"],
            "shape_tags": [row["main_key"], row["state_key"]],
            "status": "active",
            "export_to_rime": True,
            "sources": [source],
            "note": f"{row['status']}；{row.get('allocation', '')}",
            "catalog_origin": "Unicode全码表",
            "unicode_block": row["block"],
        })
    for code, count in code_counts.items():
        if count > 5:
            errors.append(f"{code}：全量码表有 {count} 个候选，超过 5 个上限")
    return records, errors, len(pages)


def load_association_aliases() -> tuple[list[dict[str, Any]], list[str]]:
    records: list[dict[str, Any]] = []
    errors: list[str] = []
    if not ASSOCIATION_GRAPH.is_file():
        return records, ["数据/联想图谱/association-graph.json：文件不存在"]
    try:
        graph = json.loads(ASSOCIATION_GRAPH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        return records, [f"数据/联想图谱/association-graph.json：{error}"]
    if graph.get("version") != 1:
        return records, ["数据/联想图谱/association-graph.json：版本必须为 1"]
    characters = {item.get("id"): item for item in graph.get("characters", []) if isinstance(item, dict)}
    concepts = {item.get("id"): item for item in graph.get("concepts", []) if isinstance(item, dict)}
    pair_codes = {item.get("code") for item in graph.get("pairs", []) if isinstance(item, dict)}
    seen: set[tuple[str, str]] = set()
    for index, alias in enumerate(graph.get("rimeAliases", []), 1):
        label = f"联想图谱 rimeAliases[{index}]"
        if not isinstance(alias, dict) or not alias.get("enabled"):
            continue
        character = characters.get(alias.get("characterId"))
        if not character:
            errors.append(f"{label}：字符不存在")
            continue
        prefix, suffix = str(alias.get("prefix", "")), str(alias.get("suffix", ""))
        code = prefix + suffix
        if prefix not in pair_codes or not re.fullmatch(r"[a-z]{4}", code):
            errors.append(f"{label}：输入码必须是已定义双字母加两位形码")
            continue
        display = str(character.get("char", ""))
        if len(display) != 1:
            errors.append(f"{label}：display 必须是单一 Unicode 标量")
            continue
        key = (display, code)
        if key in seen:
            continue
        seen.add(key)
        association_ids = [str(item) for item in alias.get("associationIds", [])]
        labels = [str(concepts[item].get("label", "")) for item in association_ids if item in concepts]
        records.append({
            "id": str(alias.get("id", f"graph-alias-{index}")),
            "type": "character",
            "display": display,
            "codepoints": [str(character.get("codepoint", f"U+{ord(display):04X}"))],
            "input_code": code,
            "mnemonic": "、".join(labels),
            "shape_tags": list(character.get("shapeTags", [])),
            "status": "active",
            "export_to_rime": True,
            "sources": ["30_项目/个人Unicode音型输入法/数据/联想图谱/association-graph.json"],
            "note": "个人联想图谱启用码",
            "catalog_origin": "联想主码" if alias.get("primary") else "联想别名",
            "unicode_block": str(character.get("block", "")),
            "association_ids": association_ids,
        })
    return records, errors


def is_han_record(record: dict[str, Any]) -> bool:
    block = str(record.get("unicode_block", record.get("mnemonic", "")))
    if block:
        return block.startswith("CJK Unified Ideographs") or block == "CJK Compatibility Ideographs"
    display = str(record.get("display", ""))
    if len(display) != 1:
        return False
    codepoint = ord(display)
    return (
        0x3400 <= codepoint <= 0x4DBF
        or 0x4E00 <= codepoint <= 0x9FFF
        or 0xF900 <= codepoint <= 0xFAFF
    )


def profile_records(records: list[dict[str, Any]], profile: str) -> list[dict[str, Any]]:
    if profile == "full":
        return list(records)
    if profile == "symbols":
        return [record for record in records if not is_han_record(record)]
    if profile == "han-bmp":
        return [record for record in records if is_han_record(record) and len(str(record.get("display", ""))) == 1 and ord(str(record["display"])) <= 0xFFFF]
    raise ValueError(f"未知 Rime profile：{profile}")


def record_weight(record: dict[str, Any]) -> int:
    origin = str(record.get("catalog_origin", ""))
    if origin in {"实体主码", "联想主码"}:
        return 1000
    if origin in {"实体别名", "联想别名"}:
        return 500
    return 1


def deduplicate_exact_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[str, str]] = set()
    result: list[dict[str, Any]] = []
    for record in records:
        key = (str(record["display"]), str(record["input_code"]))
        if key in seen:
            continue
        seen.add(key)
        result.append(record)
    return result


def collision_map(records: list[dict[str, Any]]) -> dict[str, list[str]]:
    codes: dict[str, list[str]] = defaultdict(list)
    for record in records:
        if record.get("export_to_rime") and record.get("status") == "active":
            origin = record.get("catalog_origin", "实体")
            codes[str(record["input_code"])].append(f"{origin}:{record['display']}")
    return {code: labels for code, labels in codes.items() if len(labels) > 1}


def rime_dictionary(records: list[dict[str, Any]], dictionary_name: str = "personal_unicode") -> str:
    lines = [
        "# Generated by 工具/build_catalog.py. Do not edit entries here.",
        "---",
        f"name: {dictionary_name}",
        'version: "0.2"',
        "sort: by_weight",
        "use_preset_vocabulary: false",
        "...",
    ]
    active = sorted(
        (record for record in records if record["export_to_rime"] and record["status"] == "active"),
        key=lambda record: (record["input_code"], record["display"]),
    )
    lines.extend(f"{record['display']}\t{record['input_code']}\t{record_weight(record)}" for record in active)
    return "\n".join(lines) + "\n"


def build_report(records: list[dict[str, Any]], errors: list[str], collisions: dict[str, list[str]], entity_count: int = 0, full_unicode_count: int = 0, prefix_page_count: int = 0, profile_counts: dict[str, int] | None = None, association_count: int = 0) -> str:
    active = [record for record in records if record["export_to_rime"] and record["status"] == "active"]
    lines = ["# 构建报告", "", f"- 已校验实体记录：{entity_count}", f"- 已载入 Unicode 17 全量字符：{full_unicode_count}", f"- 已启用联想码：{association_count}", f"- 前缀页：{prefix_page_count}"]
    if profile_counts:
        lines.extend(f"- {profile} profile 条目：{count}" for profile, count in profile_counts.items())
    lines.extend([f"- 已导出 Rime 条目：{len(active)}", f"- 校验错误：{len(errors)}", f"- 重码：{len(collisions)}", ""])
    if collisions:
        lines.append("## 重码（会作为 Rime 候选显示）")
        for code, labels in list(sorted(collisions.items()))[:200]:
            lines.append(f"- `{code}`：{', '.join(labels)}")
        if len(collisions) > 200:
            lines.append(f"- ……其余 {len(collisions) - 200:,} 组省略；完整约束由自动测试校验。")
        lines.append("")
    if errors:
        lines.append("## 错误")
        lines.extend(f"- {error}" for error in errors)
        lines.append("")
    return "\n".join(lines)


def write_outputs(vault_root: Path) -> tuple[int, int, int, int, dict[str, int]]:
    notes, counts = collect_sources(vault_root)
    (PROJECT_ROOT / "来源" / "来源清单.md").write_text(source_manifest(notes, counts), encoding="utf-8")
    records, errors, _ = validate_entities(PROJECT_ROOT, vault_root)
    unicode_records, unicode_errors, prefix_page_count = load_all_unicode_table(vault_root)
    errors.extend(unicode_errors)
    association_records, association_errors = load_association_aliases()
    errors.extend(association_errors)
    all_records = deduplicate_exact_records(records + unicode_records + association_records)
    collisions = collision_map(all_records)
    for code, labels in collisions.items():
        if len(labels) > 5:
            errors.append(f"{code}：共有 {len(labels)} 个候选，超过单页 5 个上限")
    queue = vault_root / "80_Codex工作区" / "待确认清单" / "个人Unicode音型输入法-首批候选.md"
    queue.write_text(candidate_report(notes, counts, records), encoding="utf-8")
    profile_counts: dict[str, int] = {}
    for profile, (dictionary_name, output) in RIME_OUTPUTS.items():
        selected = deduplicate_exact_records(profile_records(all_records, profile))
        selected_collisions = collision_map(selected)
        for code, labels in selected_collisions.items():
            if len(labels) > 5:
                errors.append(f"{profile}:{code}：共有 {len(labels)} 个候选，超过单页 5 个上限")
        output.write_text(rime_dictionary(selected, dictionary_name), encoding="utf-8")
        profile_counts[profile] = len(selected)
    (PROJECT_ROOT / "来源" / "构建报告.md").write_text(build_report(all_records, errors, collisions, len(records), len(unicode_records), prefix_page_count, profile_counts, len(association_records)), encoding="utf-8")
    if errors:
        raise ValueError("实体校验失败；详情见 来源/构建报告.md")
    return len(notes), len(records), len(unicode_records), prefix_page_count, profile_counts


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("--vault-root", type=Path, default=DEFAULT_VAULT_ROOT)
    parser.add_argument("--write", action="store_true", help="write manifests, review queue, report, and dictionary")
    args = parser.parse_args()
    vault_root = args.vault_root.resolve()
    if args.write:
        note_count, record_count, unicode_count, prefix_page_count, profile_counts = write_outputs(vault_root)
        profiles = ", ".join(f"{name}={count}" for name, count in profile_counts.items())
        print(f"Wrote inventories for {note_count} source notes, validated {record_count} entity records, and loaded {unicode_count} Unicode characters across {prefix_page_count} prefix pages ({profiles}).")
        return 0
    notes, counts = collect_sources(vault_root)
    print(f"Read {len(notes)} source notes: " + ", ".join(f"{group}={count}" for group, count in counts.items()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
