#!/usr/bin/env python3
"""Build a broad Unicode 17 catalog and a diverse 2,000-character V1 set.

The Unicode Character Database is downloaded only from unicode.org and cached
inside the project.  The script uses only Python's standard library, including
a small TrueType/OpenType cmap reader for local Windows font coverage.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import struct
import urllib.request
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path


UNICODE_VERSION = "17.0.0"
UCD_BASE = f"https://www.unicode.org/Public/{UNICODE_VERSION}/ucd"
FILES = {
    "UnicodeData.txt": f"{UCD_BASE}/UnicodeData.txt",
    "Blocks.txt": f"{UCD_BASE}/Blocks.txt",
    "Scripts.txt": f"{UCD_BASE}/Scripts.txt",
    "DerivedAge.txt": f"{UCD_BASE}/DerivedAge.txt",
    "DerivedCoreProperties.txt": f"{UCD_BASE}/DerivedCoreProperties.txt",
    "emoji-data.txt": f"{UCD_BASE}/emoji/emoji-data.txt",
    "ReadMe.txt": f"{UCD_BASE}/ReadMe.txt",
    "Unicode-License.txt": "https://www.unicode.org/license.txt",
}

ANCHORS = {
    "¤": "qtrs",
    "𓆟": "jj",
    "ܜ": "mcck",
    "ଉ": "boki",
    "Պ": "ascg",
    "○": "yboe",
    "◌": "axde",
    "⦿": "ddoi",
    "●": "fpof",
    "𒁔": "mvma",
    "ᗚ": "qdcg",
    "ஆ": "pici",
    "ᗣ": "lnte",
    "༳": "my",
}

SHAPE_WORDS = {
    "圆": ("CIRCLE", "ROUND", "RING", "DISC", "ELLIPSE", "SPHERE", "ORB"),
    "点": ("DOT", "POINT", "BULLET", "COLON", "DOTTED"),
    "线": ("LINE", "BAR", "STROKE", "DASH", "WAVE", "ARC", "TILDE"),
    "角": ("ANGLE", "CORNER", "TRIANGLE", "WEDGE", "CHEVRON"),
    "方向": ("LEFT", "RIGHT", "UP", "DOWN", "NORTH", "SOUTH", "EAST", "WEST", "ARROW"),
    "对称": ("SYMMETRIC", "MIRROR", "EQUAL", "BALANCE", "DOUBLE", "QUAD", "CROSS"),
    "方": ("SQUARE", "BOX", "RECTANGLE", "BLOCK", "CUBE"),
    "星芒": ("STAR", "ASTERISK", "SUN", "RAY", "SPARK", "FLOWER"),
    "曲线": ("SPIRAL", "CURL", "LOOP", "HOOK", "HEART", "MOON"),
}

VISUAL_WORDS = tuple({word for words in SHAPE_WORDS.values() for word in words}) + (
    "FACE", "EYE", "HAND", "ORNAMENT", "MUSIC", "NOTE", "DIAMOND", "KNOT",
)

PRIORITY_BLOCK_WORDS = (
    "Geometric", "Arrow", "Mathematical", "Dingbat", "Miscellaneous Symbols",
    "Enclosed", "Box Drawing", "Block Elements", "Braille", "Technical",
    "Musical", "Pictograph", "Emoticon", "Transport", "Map Symbols",
    "Alchemical", "Domino", "Mahjong", "Chess", "Playing Cards",
)


@dataclass(frozen=True)
class Record:
    cp: int
    char: str
    name: str
    category: str
    script: str
    block: str
    age: str
    emoji: bool
    requires_base: bool
    standalone_safe: bool
    font_covered: bool
    shape_hints: str


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download_files(ucd_dir: Path, refresh: bool) -> dict[str, dict[str, str | int]]:
    ucd_dir.mkdir(parents=True, exist_ok=True)
    manifest: dict[str, dict[str, str | int]] = {}
    for name, url in FILES.items():
        target = ucd_dir / name
        if refresh or not target.exists():
            request = urllib.request.Request(url, headers={"User-Agent": "Personal-Unicode-IME/1.0"})
            with urllib.request.urlopen(request, timeout=60) as response:
                data = response.read()
            target.write_bytes(data)
        manifest[name] = {"url": url, "sha256": sha256(target), "bytes": target.stat().st_size}
    (ucd_dir / "SHA256SUMS.json").write_text(
        json.dumps({"unicode_version": UNICODE_VERSION, "files": manifest}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return manifest


def parse_range(text: str) -> tuple[int, int]:
    ends = text.strip().split("..")
    start = int(ends[0], 16)
    return start, int(ends[-1], 16)


def parse_property_file(path: Path, wanted: str | None = None) -> dict[int, str] | set[int]:
    if wanted:
        result_set: set[int] = set()
    else:
        result_map: dict[int, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line or ";" not in line:
            continue
        span, value = (part.strip() for part in line.split(";", 1))
        if wanted and value != wanted:
            continue
        start, end = parse_range(span)
        if wanted:
            result_set.update(range(start, end + 1))
        else:
            for cp in range(start, end + 1):
                result_map[cp] = value
    return result_set if wanted else result_map


def expanded_name(base: str, cp: int) -> str:
    stem = re.sub(r", First$", "", base.strip("<>"), flags=re.IGNORECASE).upper()
    if "CJK IDEOGRAPH" in stem:
        return f"CJK UNIFIED IDEOGRAPH-{cp:04X}"
    if "TANGUT IDEOGRAPH" in stem:
        return f"TANGUT IDEOGRAPH-{cp:04X}"
    return f"{stem}-{cp:04X}"


def parse_unicode_data(path: Path) -> list[tuple[int, str, str]]:
    rows: list[tuple[int, str, str]] = []
    pending: tuple[int, str, str] | None = None
    for line in path.read_text(encoding="utf-8").splitlines():
        fields = line.split(";")
        cp, name, category = int(fields[0], 16), fields[1], fields[2]
        if name.endswith(", First>"):
            pending = (cp, name, category)
        elif name.endswith(", Last>"):
            if pending is None:
                raise ValueError(f"Range end without start at U+{cp:04X}")
            start, base, first_category = pending
            rows.extend((item, expanded_name(base, item), first_category) for item in range(start, cp + 1))
            pending = None
        else:
            rows.append((cp, name, category))
    if pending:
        raise ValueError("Unclosed UnicodeData range")
    return rows


def be16(data: bytes, offset: int) -> int:
    return struct.unpack_from(">H", data, offset)[0]


def be32(data: bytes, offset: int) -> int:
    return struct.unpack_from(">I", data, offset)[0]


def font_faces(data: bytes) -> list[int]:
    if data[:4] == b"ttcf" and len(data) >= 12:
        count = be32(data, 8)
        return [be32(data, 12 + index * 4) for index in range(count)]
    return [0]


def cmap_codepoints(data: bytes, face: int) -> set[int]:
    covered: set[int] = set()
    if face + 12 > len(data):
        return covered
    table_count = be16(data, face + 4)
    cmap_offset = None
    for index in range(table_count):
        record = face + 12 + index * 16
        if record + 16 > len(data):
            break
        if data[record:record + 4] == b"cmap":
            cmap_offset = be32(data, record + 8)
            break
    if cmap_offset is None or cmap_offset + 4 > len(data):
        return covered
    subtable_count = be16(data, cmap_offset + 2)
    seen: set[int] = set()
    for index in range(subtable_count):
        rec = cmap_offset + 4 + index * 8
        if rec + 8 > len(data):
            break
        platform, encoding = be16(data, rec), be16(data, rec + 2)
        if not (platform == 0 or (platform == 3 and encoding in (1, 10))):
            continue
        sub = cmap_offset + be32(data, rec + 4)
        if sub in seen or sub + 2 > len(data):
            continue
        seen.add(sub)
        fmt = be16(data, sub)
        try:
            if fmt == 0 and sub + 262 <= len(data):
                for cp, glyph in enumerate(data[sub + 6:sub + 262]):
                    if glyph:
                        covered.add(cp)
            elif fmt == 4:
                length = be16(data, sub + 2)
                seg_count = be16(data, sub + 6) // 2
                if sub + length > len(data) or not seg_count:
                    continue
                end_base = sub + 14
                start_base = end_base + seg_count * 2 + 2
                delta_base = start_base + seg_count * 2
                range_base = delta_base + seg_count * 2
                for seg in range(seg_count):
                    start, end = be16(data, start_base + seg * 2), be16(data, end_base + seg * 2)
                    delta = be16(data, delta_base + seg * 2)
                    ro_pos = range_base + seg * 2
                    ro = be16(data, ro_pos)
                    if start > end:
                        continue
                    for cp in range(start, min(end, 0xFFFE) + 1):
                        if ro == 0:
                            glyph = (cp + delta) & 0xFFFF
                        else:
                            glyph_pos = ro_pos + ro + 2 * (cp - start)
                            glyph = be16(data, glyph_pos) if glyph_pos + 2 <= sub + length else 0
                            if glyph:
                                glyph = (glyph + delta) & 0xFFFF
                        if glyph:
                            covered.add(cp)
            elif fmt in (12, 13):
                length, groups = be32(data, sub + 4), be32(data, sub + 12)
                if sub + length > len(data):
                    continue
                for group in range(groups):
                    pos = sub + 16 + group * 12
                    start, end, glyph = be32(data, pos), be32(data, pos + 4), be32(data, pos + 8)
                    if glyph and start <= end <= 0x10FFFF:
                        covered.update(range(start, end + 1))
        except (IndexError, struct.error):
            continue
    return covered


def compress_ranges(values: set[int]) -> list[list[int]]:
    if not values:
        return []
    ordered = sorted(values)
    ranges: list[list[int]] = []
    start = previous = ordered[0]
    for value in ordered[1:]:
        if value != previous + 1:
            ranges.append([start, previous])
            start = value
        previous = value
    ranges.append([start, previous])
    return ranges


def windows_font_coverage(font_dir: Path, cache_path: Path) -> tuple[set[int], dict[str, int | str]]:
    fonts = sorted(path for path in font_dir.glob("*") if path.suffix.lower() in {".ttf", ".otf", ".ttc"})
    fingerprint_text = "\n".join(f"{path.name}|{path.stat().st_size}|{path.stat().st_mtime_ns}" for path in fonts)
    fingerprint = hashlib.sha256(fingerprint_text.encode()).hexdigest()
    if cache_path.exists():
        cached = json.loads(cache_path.read_text(encoding="utf-8"))
        if cached.get("fingerprint") == fingerprint:
            covered = {cp for start, end in cached["ranges"] for cp in range(start, end + 1)}
            return covered, cached["summary"]
    covered: set[int] = set()
    readable = 0
    for path in fonts:
        try:
            data = path.read_bytes()
            for face in font_faces(data):
                covered.update(cmap_codepoints(data, face))
            readable += 1
        except (OSError, struct.error):
            continue
    summary: dict[str, int | str] = {
        "font_directory": str(font_dir),
        "font_files_found": len(fonts),
        "font_files_read": readable,
        "covered_codepoints": len(covered),
    }
    cache_path.write_text(
        json.dumps({"fingerprint": fingerprint, "summary": summary, "ranges": compress_ranges(covered)}, indent=2) + "\n",
        encoding="utf-8",
    )
    return covered, summary


def shape_hints(name: str) -> str:
    return ",".join(label for label, words in SHAPE_WORDS.items() if any(word in name for word in words))


def build_records(ucd_dir: Path, font_covered: set[int]) -> tuple[list[Record], dict[str, int]]:
    blocks = parse_property_file(ucd_dir / "Blocks.txt")
    scripts = parse_property_file(ucd_dir / "Scripts.txt")
    ages = parse_property_file(ucd_dir / "DerivedAge.txt")
    ignorables = parse_property_file(ucd_dir / "DerivedCoreProperties.txt", "Default_Ignorable_Code_Point")
    emoji = parse_property_file(ucd_dir / "emoji-data.txt", "Emoji")
    assert isinstance(blocks, dict) and isinstance(scripts, dict) and isinstance(ages, dict)
    assert isinstance(ignorables, set) and isinstance(emoji, set)
    rows = parse_unicode_data(ucd_dir / "UnicodeData.txt")
    counts = Counter()
    records: list[Record] = []
    for cp, name, category in rows:
        counts["unicode_data_assigned_rows"] += 1
        if category[0] not in {"L", "M", "N", "P", "S"}:
            counts[f"excluded_category_{category[0]}"] += 1
            continue
        if cp in ignorables:
            counts["excluded_default_ignorable"] += 1
            continue
        requires_base = category.startswith("M")
        records.append(Record(
            cp=cp,
            char=chr(cp),
            name=name,
            category=category,
            script=scripts.get(cp, "Unknown"),
            block=blocks.get(cp, "No_Block"),
            age=ages.get(cp, "Unknown"),
            emoji=cp in emoji,
            requires_base=requires_base,
            standalone_safe=not requires_base,
            font_covered=cp in font_covered,
            shape_hints=shape_hints(name),
        ))
    counts["broad_catalog"] = len(records)
    counts["combining_marks_retained"] = sum(record.requires_base for record in records)
    counts["broad_font_covered"] = sum(record.font_covered for record in records)
    return records, dict(counts)


def candidate_score(record: Record) -> int:
    score = {"So": 85, "Sm": 72, "Sk": 58, "Sc": 52, "Po": 46, "Pd": 44, "Ps": 44,
             "Pe": 44, "Pi": 42, "Pf": 42, "No": 38, "Nl": 34, "Lu": 25, "Ll": 22,
             "Lo": 20, "Lt": 20, "Nd": 15}.get(record.category, 10)
    if record.emoji:
        score += 35
    score += 14 * sum(word in record.name for word in VISUAL_WORDS)
    if any(word.lower() in record.block.lower() for word in PRIORITY_BLOCK_WORDS):
        score += 45
    if record.shape_hints:
        score += 30
    if record.script == "Common":
        score += 16
    if "CJK UNIFIED IDEOGRAPH" in record.name:
        score -= 38
    if record.cp < 0x80:
        score -= 100
    return score


def block_cap(block: str) -> int:
    if any(word.lower() in block.lower() for word in PRIORITY_BLOCK_WORDS):
        return 150
    if any(word in block for word in ("CJK", "Hangul", "Tangut")):
        return 55
    return 80


SCRIPT_CAPS = defaultdict(lambda: 95, {
    "Common": 900,
    "Latin": 180,
    "Han": 120,
    "Inherited": 60,
    "Arabic": 110,
    "Greek": 110,
    "Cyrillic": 110,
})


def select_v1(records: list[Record], target: int) -> tuple[list[Record], dict[int, str]]:
    by_cp = {record.cp: record for record in records}
    selected: list[Record] = []
    selected_cps: set[int] = set()
    reasons: dict[int, str] = {}
    block_counts = Counter()
    script_counts = Counter()

    def add(record: Record, reason: str) -> bool:
        if record.cp in selected_cps:
            return False
        selected.append(record)
        selected_cps.add(record.cp)
        block_counts[record.block] += 1
        script_counts[record.script] += 1
        reasons[record.cp] = reason
        return True

    for char, code in ANCHORS.items():
        cp = ord(char)
        if cp not in by_cp:
            raise ValueError(f"Anchor {char} U+{cp:04X} was filtered from the broad catalog")
        add(by_cp[cp], f"已确认锚点:{code}")

    pool = [
        record for record in records
        if record.standalone_safe and record.font_covered and record.cp > 0x7E and record.cp not in selected_cps
    ]
    pool.sort(key=lambda record: (-candidate_score(record), record.block, record.cp))
    for record in pool:
        if len(selected) >= target:
            break
        if block_counts[record.block] >= block_cap(record.block):
            continue
        if script_counts[record.script] >= SCRIPT_CAPS[record.script]:
            continue
        reason = "形态词命中" if record.shape_hints else "区块与文字系统多样性"
        if record.emoji:
            reason += "+Emoji"
        add(record, reason)
    if len(selected) < target:
        for record in pool:
            if len(selected) >= target:
                break
            add(record, "补足多样性配额")
    if len(selected) != target:
        raise ValueError(f"Could select only {len(selected)} of {target} characters")
    selected.sort(key=lambda record: (-candidate_score(record), record.cp))
    for anchor in ANCHORS:
        # Anchors remain included even after display-order sorting.
        assert ord(anchor) in {record.cp for record in selected}
    return selected, reasons


FIELDS = [
    "char", "display_sample", "codepoint", "name", "category", "script", "block", "age",
    "emoji", "requires_base", "standalone_safe", "windows_font_covered", "shape_hints",
]


def record_row(record: Record) -> dict[str, str]:
    return {
        "char": record.char,
        "display_sample": ("◌" + record.char) if record.requires_base else record.char,
        "codepoint": f"U+{record.cp:04X}",
        "name": record.name,
        "category": record.category,
        "script": record.script,
        "block": record.block,
        "age": record.age,
        "emoji": str(record.emoji).lower(),
        "requires_base": str(record.requires_base).lower(),
        "standalone_safe": str(record.standalone_safe).lower(),
        "windows_font_covered": str(record.font_covered).lower(),
        "shape_hints": record.shape_hints,
    }


def write_tsv(path: Path, records: list[Record], reasons: dict[int, str] | None = None) -> None:
    fields = (["rank", "selection_reason"] if reasons is not None else []) + FIELDS
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        for rank, record in enumerate(records, 1):
            row = record_row(record)
            if reasons is not None:
                row = {"rank": str(rank), "selection_reason": reasons[record.cp], **row}
            writer.writerow(row)


def markdown_preview(path: Path, selected: list[Record], counts: dict[str, int], font_summary: dict[str, int | str]) -> None:
    blocks: dict[str, list[Record]] = defaultdict(list)
    for record in selected:
        blocks[record.block].append(record)
    category_counts = Counter(record.category[0] for record in selected)
    script_counts = Counter(record.script for record in selected)
    lines = [
        "---", "title: Unicode 17 首版 2000 字符预览", "project: 个人 Unicode 音型输入法",
        "unicode_version: 17.0.0", "count: 2000", "status: 待试用", "---", "",
        "# Unicode 17 首版 2000 字符预览", "",
        "这是一份可回滚、可重新生成的试验语料，不代表 2000 个字符已经获得输入码。",
        "前两键必须来自个人音感、情绪或联想；本页只提供字符、形态标签和本机显示覆盖依据。", "",
        "## 摘要", "",
        f"- 总库：{counts['broad_catalog']:,} 个；其中组合附加符 {counts['combining_marks_retained']:,} 个，均保留并标为需依附基字符。",
        f"- 首版：{len(selected):,} 个单字符；已强制包含 {len(ANCHORS)} 个现有输入法锚点。",
        f"- 本机字体扫描：{font_summary['font_files_read']}/{font_summary['font_files_found']} 个字体文件可读，合计覆盖 {int(font_summary['covered_codepoints']):,} 个码位。",
        f"- 大类：{', '.join(f'{key}={value}' for key, value in sorted(category_counts.items()))}。",
        f"- 文字系统前十：{', '.join(f'{key}={value}' for key, value in script_counts.most_common(10))}。", "",
        "## 现有锚点", "",
        "| 字符 | 输入码 | 码位 | 本机字体 |", "| --- | --- | --- | --- |",
    ]
    selected_by_cp = {record.cp: record for record in selected}
    for char, code in ANCHORS.items():
        record = selected_by_cp[ord(char)]
        lines.append(f"| {char} | `{code}` | U+{record.cp:04X} | {'是' if record.font_covered else '否；仍按用户确认保留'} |")
    lines += ["", "## 按区块预览", ""]
    for block, items in sorted(blocks.items(), key=lambda item: (-len(item[1]), item[0])):
        lines += [f"### {block}（{len(items)}）", ""]
        glyphs = [record.char for record in sorted(items, key=lambda item: item.cp)]
        for start in range(0, len(glyphs), 48):
            lines.append(" ".join(glyphs[start:start + 48]))
        lines.append("")
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def write_readme(path: Path, records: list[Record], selected: list[Record], counts: dict[str, int], manifest: dict[str, dict[str, str | int]]) -> None:
    category_counts = Counter(record.category for record in records)
    lines = [
        "---", "title: Unicode 精选说明", "project: 个人 Unicode 音型输入法", "unicode_version: 17.0.0", "---", "",
        "# Unicode 精选说明", "",
        "## 两层语料", "",
        f"1. `输出/unicode-17-全量精选.tsv`：{len(records):,} 个候选。保留 Unicode 17 中已编码的字母、组合附加符、数字、标点和符号。",
        f"2. `输出/unicode-17-v1-2000.tsv`：{len(selected):,} 个首版试验字符。除 {len(ANCHORS)} 个已确认锚点外，要求可独立输入并被当前 Windows 字体覆盖。", "",
        "总库不因当前电脑缺少字体而删除字符。`windows_font_covered=false` 只表示这台电脑目前没有在已安装字体的 cmap 中声明它；未来安装字体后可以改变。", "",
        "## 排除边界", "",
        "- 排除控制、格式、代理、私用区、未分配、空白与段落分隔类字符。",
        "- 排除 `Default_Ignorable_Code_Point`，避免变体选择符、标签字符等在单独上屏时不可见或干扰文本。",
        f"- 保留 {counts['combining_marks_retained']:,} 个组合附加符，`requires_base=true`，预览时以虚线圆 `◌` 承载。",
        "- 不自动采用兼容归一化替换；码位身份原样保留。", "",
        "## 四码容量", "",
        "`26^4 = 456,976`，不是五十多万。即使从中预留一些短码前缀、控制码和实验空间，承载十几万字符仍有余量。两码 `jj` 若设为自动上屏，应把 `jj??` 的 676 个四码视为被该短码占用。", "",
        "## 可复现来源", "",
    ]
    for name, data in manifest.items():
        lines.append(f"- `{name}`：[{data['url']}]({data['url']})；SHA-256 `{data['sha256']}`")
    lines += ["", "## 总库类别统计", ""]
    lines.extend(f"- `{category}`：{count:,}" for category, count in sorted(category_counts.items()))
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--refresh", action="store_true", help="redownload official UCD files")
    parser.add_argument("--target", type=int, default=2000)
    parser.add_argument("--font-dir", type=Path, default=Path(r"C:\Windows\Fonts"))
    args = parser.parse_args()

    project = Path(__file__).resolve().parents[1]
    root = project / "数据" / "Unicode精选"
    ucd_dir = root / f"UCD-{UNICODE_VERSION}"
    output = root / "输出"
    output.mkdir(parents=True, exist_ok=True)

    manifest = download_files(ucd_dir, args.refresh)
    font_covered, font_summary = windows_font_coverage(args.font_dir, output / "windows-font-coverage.json")
    records, counts = build_records(ucd_dir, font_covered)
    selected, reasons = select_v1(records, args.target)

    write_tsv(output / "unicode-17-全量精选.tsv", records)
    write_tsv(output / "unicode-17-v1-2000.tsv", selected, reasons)
    markdown_preview(output / "unicode-17-v1-2000预览.md", selected, counts, font_summary)
    write_readme(root / "Unicode精选说明.md", records, selected, counts, manifest)

    result = {
        "unicode_version": UNICODE_VERSION,
        "broad_catalog": len(records),
        "v1": len(selected),
        "anchors": len(ANCHORS),
        "combining_marks_retained": counts["combining_marks_retained"],
        "broad_font_covered": counts["broad_font_covered"],
        "font_scan": font_summary,
        "outputs": {
            "broad_tsv": str(output / "unicode-17-全量精选.tsv"),
            "v1_tsv": str(output / "unicode-17-v1-2000.tsv"),
            "preview": str(output / "unicode-17-v1-2000预览.md"),
        },
    }
    (output / "build-summary.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
