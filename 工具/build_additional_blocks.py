#!/usr/bin/env python3
"""Build visually balanced four-letter codes for user-selected Unicode blocks."""

from __future__ import annotations

import csv
import math
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import ImageFont

from build_hieroglyph_block import (
    CLUSTER_MAIN,
    MAIN_LABELS,
    STATE_LABELS,
    assign_states,
    balanced_kmeans,
    render,
)
from build_unicode_selection import parse_unicode_data


PROJECT = Path(__file__).resolve().parents[1]
VAULT = PROJECT.parents[1]
UCD = PROJECT / "数据" / "Unicode精选" / "UCD-17.0.0" / "UnicodeData.txt"
ALGORITHM = "visual-balanced-unicode-block-v1"
MAX_CANDIDATES = 5


@dataclass(frozen=True)
class Block:
    key: str
    start: int
    end: int
    expected: int
    prefix_ranges: tuple[tuple[str, int, int], ...]
    source: str
    output: str
    font: str
    font_size: int
    anchor: int
    anchor_code: str


BLOCKS = (
    Block(
        "armenian", 0x0530, 0x058F, 91, (("as", 0x0530, 0x058F),),
        "30_项目/个人Unicode音型输入法/数据/unicode全字符/plane-00-Basic Multilingual Plane/block-u0530-u058f-armenian.md",
        "ՊArmenian字块-编码.tsv", "C:/Windows/Fonts/sylfaen.ttf", 76, 0x054A, "ascg",
    ),
    Block(
        "math-symbols-b", 0x2980, 0x29FF, 128, (("dd", 0x2980, 0x29FF),),
        "30_项目/个人Unicode音型输入法/数据/unicode全字符/plane-00-Basic Multilingual Plane/block-u2980-u29ff-miscellaneous-mathematical-symbols-b.md",
        "⦿数学符号B字块-编码.tsv", "C:/Windows/Fonts/cambria.ttc", 76, 0x29BF, "ddoi",
    ),
    Block(
        "cuneiform", 0x12000, 0x123FF, 922, (
            ("mv", 0x12000, 0x120FF),
            ("mu", 0x12100, 0x121FF),
            ("mn", 0x12200, 0x122FF),
            ("mw", 0x12300, 0x12399),
        ),
        "30_项目/个人Unicode音型输入法/数据/unicode全字符/plane-01-Supplementary Multilingual Plane/block-u12000-u123ff-cuneiform.md",
        "𒁔Cuneiform字块-编码.tsv", "C:/Windows/Fonts/seguihis.ttf", 72, 0x12054, "mvma",
    ),
    Block(
        "tamil", 0x0B80, 0x0BFF, 72, (("pi", 0x0B80, 0x0BFF),),
        "30_项目/个人Unicode音型输入法/数据/unicode全字符/plane-00-Basic Multilingual Plane/block-u0b80-u0bff-tamil.md",
        "ஆTamil字块-编码.tsv", "C:/Windows/Fonts/Nirmala.ttc", 76, 0x0B86, "pici",
    ),
)

FIELDNAMES = (
    "char", "codepoint", "unicode_name", "category", "block", "prefix",
    "visual_cluster", "main_key", "main_shape", "preferred_state_key",
    "state_cluster", "state_key", "state_shape", "input_code",
    "classification_reason", "rebalanced", "cluster_distance", "aspect",
    "density", "source", "status", "algorithm",
)


def source_codepoints(block: Block) -> list[int]:
    path = VAULT / block.source
    matches = [int(value, 16) for value in re.findall(r"^U\+([0-9A-F]+)\t", path.read_text(encoding="utf-8"), re.MULTILINE)]
    if len(matches) != block.expected or len(set(matches)) != block.expected:
        raise ValueError(f"{block.key} 预期 {block.expected} 个唯一字符，实际 {len(matches)} 个")
    if any(not block.start <= codepoint <= block.end for codepoint in matches):
        raise ValueError(f"{block.key} 存在区块范围外码位")
    return matches


def prefix_for(block: Block, codepoint: int) -> str:
    matches = [prefix for prefix, start, end in block.prefix_ranges if start <= codepoint <= end]
    if len(matches) != 1:
        raise ValueError(f"{block.key} U+{codepoint:04X} 没有唯一内部前缀")
    return matches[0]


def build_block(block: Block, ucd: dict[int, tuple[str, str]]) -> list[dict[str, str]]:
    font_path = Path(block.font)
    if not font_path.is_file():
        raise FileNotFoundError(f"字体不存在：{font_path}")
    font = ImageFont.truetype(str(font_path), block.font_size)
    codepoints = source_codepoints(block)
    metrics = []
    vectors = []
    for codepoint in codepoints:
        measured, vector = render(chr(codepoint), font)
        metrics.append(measured)
        vectors.append(vector)
    vector_array = np.stack(vectors)
    prefixes = [prefix_for(block, codepoint) for codepoint in codepoints]
    labels = np.zeros(len(codepoints), dtype=np.int64)
    chosen_distances = np.zeros(len(codepoints), dtype=np.float64)
    for prefix in dict.fromkeys(prefixes):
        indices = [index for index, value in enumerate(prefixes) if value == prefix]
        cluster_count = min(26, math.ceil(len(indices) / MAX_CANDIDATES))
        cluster_capacity = math.ceil(len(indices) / cluster_count)
        local_labels, local_distances, _ = balanced_kmeans(
            vector_array[np.asarray(indices)],
            cluster_count=cluster_count,
            capacity=cluster_capacity,
            seed=20260810 + block.start + sum(map(ord, prefix)),
        )
        for local_index, global_index in enumerate(indices):
            labels[global_index] = local_labels[local_index]
            chosen_distances[global_index] = local_distances[local_index, local_labels[local_index]]
    states, preferred, rebalanced, state_clusters = assign_states(
        labels, prefixes, vector_array, metrics, codepoints
    )
    rows: list[dict[str, str]] = []
    for index, codepoint in enumerate(codepoints):
        cluster = int(labels[index])
        main_key = CLUSTER_MAIN[cluster]
        state_key = states[index]
        prefix = prefixes[index]
        input_code = prefix + main_key + state_key
        reason = f"{block.key}视觉聚类C{cluster};状态组S{state_clusters[index]}"
        if codepoint == block.anchor:
            main_key = block.anchor_code[2]
            state_key = block.anchor_code[3]
            input_code = block.anchor_code
            reason = f"用户锚点：{chr(codepoint)}={block.anchor_code}"
        name, category = ucd[codepoint]
        rows.append({
            "char": chr(codepoint),
            "codepoint": f"U+{codepoint:04X}",
            "unicode_name": name,
            "category": category,
            "block": block.key,
            "prefix": prefix,
            "visual_cluster": str(cluster),
            "main_key": main_key,
            "main_shape": MAIN_LABELS[main_key],
            "preferred_state_key": preferred[index],
            "state_cluster": str(state_clusters[index]),
            "state_key": state_key,
            "state_shape": STATE_LABELS[state_key],
            "input_code": input_code,
            "classification_reason": reason,
            "rebalanced": str(rebalanced[index]).lower(),
            "cluster_distance": f"{chosen_distances[index]:.6f}",
            "aspect": f"{metrics[index].aspect:.4f}",
            "density": f"{metrics[index].density:.4f}",
            "source": block.source,
            "status": "machine-initial-v1",
            "algorithm": ALGORITHM,
        })
    counts = Counter(row["input_code"] for row in rows)
    if max(counts.values()) > MAX_CANDIDATES:
        raise ValueError(f"{block.key} 单码候选超过 {MAX_CANDIDATES}")
    if next(row for row in rows if int(row["codepoint"][2:], 16) == block.anchor)["input_code"] != block.anchor_code:
        raise ValueError(f"{block.key} 锚点未保留")
    return rows


def write_table(block: Block, rows: list[dict[str, str]]) -> None:
    path = PROJECT / "数据" / block.output
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES, delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    ucd = {codepoint: (name, category) for codepoint, name, category in parse_unicode_data(UCD)}
    for block in BLOCKS:
        rows = build_block(block, ucd)
        write_table(block, rows)
        counts = Counter(row["input_code"] for row in rows)
        prefix_counts = Counter(row["prefix"] for row in rows)
        print(f"{block.key} {dict(prefix_counts)}: {len(rows)} 字符，{len(counts)} 个四码，单码最多 {max(counts.values())} 个。")


if __name__ == "__main__":
    main()
