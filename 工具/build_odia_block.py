#!/usr/bin/env python3
"""Build a visual first-pass bo-prefixed catalog for the Odia block."""

from __future__ import annotations

import argparse
import csv
import math
import sys
from collections import Counter
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
SOURCE = PROJECT / "数据" / "ଉOriya Sign字块.md"
OUTPUT = PROJECT / "数据" / "ଉ字块-编码.tsv"
UCD = PROJECT / "数据" / "Unicode精选" / "UCD-17.0.0" / "UnicodeData.txt"
SOURCE_RELATIVE = "30_项目/个人Unicode音型输入法/数据/ଉOriya Sign字块.md"
PREFIX = "bo"
CLUSTER_COUNT = 19
CLUSTER_CAPACITY = 5
ALGORITHM = "visual-balanced-odia-v1"
MANUAL = {0x0B09: ("k", "i", "用户锚点：ଉ=boki")}


def items() -> list[tuple[str, int, str, str]]:
    rows = [
        (chr(cp), cp, name, category)
        for cp, name, category in parse_unicode_data(UCD)
        if 0x0B00 <= cp <= 0x0B7F and category[0] in {"L", "M", "N", "P", "S"}
    ]
    if len(rows) != 91:
        raise ValueError(f"预期 91 个奥里亚字符，实际 {len(rows)} 个")
    return rows


def build(font_path: Path, font_size: int) -> list[dict[str, str]]:
    font = ImageFont.truetype(str(font_path), font_size)
    source_items = items()
    rendered = [render(("◌" + char) if category.startswith("M") else char, font) for char, _cp, _name, category in source_items]
    metrics = [item[0] for item in rendered]
    vectors = np.stack([item[1] for item in rendered])
    labels, distances, _ = balanced_kmeans(
        vectors, cluster_count=CLUSTER_COUNT, capacity=CLUSTER_CAPACITY, seed=20260810
    )
    state_keys, preferred_states, rebalanced, state_clusters = assign_states(
        labels,
        [PREFIX] * len(source_items),
        vectors,
        metrics,
        [item[1] for item in source_items],
    )
    rows: list[dict[str, str]] = []
    for index, ((char, cp, name, category), shape_metrics) in enumerate(zip(source_items, metrics)):
        cluster = int(labels[index])
        main = CLUSTER_MAIN[cluster]
        state = state_keys[index]
        note = f"奥里亚视觉聚类C{cluster};状态组S{state_clusters[index]}"
        if cp in MANUAL:
            main, state, note = MANUAL[cp]
            preferred_states[index] = state
            rebalanced[index] = False
        rows.append({
            "char": char,
            "codepoint": f"U+{cp:04X}",
            "unicode_name": name,
            "category": category,
            "prefix": PREFIX,
            "visual_cluster": str(cluster),
            "main_key": main,
            "main_shape": MAIN_LABELS[main],
            "preferred_state_key": preferred_states[index],
            "state_cluster": str(state_clusters[index]),
            "state_key": state,
            "state_shape": STATE_LABELS[state],
            "input_code": PREFIX + main + state,
            "classification_reason": note,
            "rebalanced": str(rebalanced[index]).lower(),
            "cluster_distance": f"{float(distances[index, cluster]):.6f}",
            "aspect": f"{shape_metrics.aspect:.4f}",
            "density": f"{shape_metrics.density:.4f}",
            "source": SOURCE_RELATIVE,
            "status": "machine-initial-v1",
            "algorithm": ALGORITHM,
        })
    counts = Counter(row["input_code"] for row in rows)
    if max(counts.values()) > 5:
        raise ValueError(f"同码超过 5 个候选：{counts.most_common(1)[0]}")
    anchor = next(row for row in rows if row["codepoint"] == "U+0B09")
    if anchor["input_code"] != "boki":
        raise ValueError("ଉ 未保持 boki")
    return rows


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("--font", type=Path, default=Path(r"C:\Windows\Fonts\Nirmala.ttc"))
    parser.add_argument("--font-size", type=int, default=96)
    args = parser.parse_args()
    rows = build(args.font, args.font_size)
    with OUTPUT.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    counts = Counter(row["input_code"] for row in rows)
    print(f"生成 {len(rows)} 个 bo 字块条目，使用 {len(counts)} 个四码，单码最多 {max(counts.values())} 个候选。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
