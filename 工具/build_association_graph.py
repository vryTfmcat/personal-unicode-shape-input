#!/usr/bin/env python3
"""Create the initial personal association graph from the curated 2000 set."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[1]
SELECTION = PROJECT / "数据" / "Unicode精选" / "输出" / "unicode-17-v1-2000.tsv"
OUTPUT = PROJECT / "数据" / "联想图谱" / "association-graph.json"
LETTERS = "abcdefghijklmnopqrstuvwxyz"
MAX_SUGGESTIONS = 500

NAME_ASSOCIATIONS = (
    (("CIRCLE", "RING", "ROUND"), "完整、圆满"),
    (("STAR", "SUN", "RAY"), "闪耀"),
    (("HEART",), "情感"),
    (("ARROW", "POINTING"), "方向、指引"),
    (("WAVE", "WAVY"), "流动"),
    (("SPIRAL", "LOOP", "CYCLE"), "循环"),
    (("BALANCE", "SCALES"), "平衡"),
    (("EYE",), "注视"),
    (("MOON",), "夜晚"),
    (("FLOWER", "BLOSSOM"), "生长、绽放"),
    (("TREE", "LEAF", "PLANT"), "生命、生长"),
    (("FISH", "BIRD", "ANIMAL"), "生命"),
    (("FIRE", "FLAME"), "能量"),
    (("WATER", "DROP"), "流动、滋养"),
    (("MOUNTAIN",), "稳定"),
    (("CROSS", "INTERSECTION"), "相遇、交叉"),
    (("SQUARE", "BOX", "RECTANGLE"), "稳定、边界"),
    (("TRIANGLE", "WEDGE"), "尖锐、方向"),
    (("INFINITY",), "无限"),
    (("WARNING", "DANGER", "HAZARD"), "危险、警示"),
    (("MUSIC", "NOTE"), "声音、节奏"),
    (("KEY", "LOCK"), "开启、守护"),
    (("HAND",), "行动、触碰"),
    (("FACE", "SMILING", "FROWNING"), "情绪"),
)

SHAPE_ASSOCIATIONS = (
    ("圆", "完整、圆满"),
    ("星芒", "闪耀"),
    ("波浪", "流动"),
    ("螺旋", "循环"),
    ("方向", "方向、指引"),
    ("对称", "平衡"),
    ("方", "稳定、边界"),
    ("角", "转折"),
    ("交叉", "相遇、交叉"),
    ("曲线", "柔和"),
    ("线", "连接"),
    ("点", "起点"),
)


def stable_id(prefix: str, value: str) -> str:
    digest = hashlib.sha1(value.encode("utf-8")).hexdigest()[:12]
    return f"{prefix}-{digest}"


def read_selection() -> list[dict[str, str]]:
    with SELECTION.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    if len(rows) != 2000:
        raise ValueError(f"精选字符不是 2000 个：{len(rows)}")
    return rows


def association_for(row: dict[str, str]) -> str | None:
    name = row["name"].upper()
    for tokens, label in NAME_ASSOCIATIONS:
        if any(re.search(rf"\b{re.escape(token)}\b", name) for token in tokens):
            return label
    hints = {hint.strip() for hint in row.get("shape_hints", "").split(",") if hint.strip()}
    for hint, label in SHAPE_ASSOCIATIONS:
        if hint in hints:
            return label
    return None


def character_record(row: dict[str, str]) -> dict[str, object]:
    cp = row["codepoint"]
    return {
        "id": "u-" + cp[2:].lower(),
        "char": row["char"],
        "codepoint": cp,
        "unicodeName": row["name"],
        "block": row["block"],
        "shapeTags": [item for item in row.get("shape_hints", "").split(",") if item],
        "selectionRank": int(row["rank"]),
    }


def build() -> dict[str, object]:
    rows = read_selection()
    characters = [character_record(row) for row in rows]
    character_ids = {item["char"]: item["id"] for item in characters}

    letters = [
        {"key": key, "meanings": [], "note": "", "color": ""}
        for key in LETTERS
    ]
    by_letter = {item["key"]: item for item in letters}
    by_letter["v"].update({"meanings": ["危险"], "note": "字母本身带来危险、尖锐的感觉。", "color": "#a9482d"})
    by_letter["r"].update({"meanings": ["圆满", "完美"], "note": "来自 yuan → ruan 的个人音变联想。", "color": "#c88b38"})

    pairs = [
        {"code": first + second, "labels": [], "description": "", "tags": [], "color": "", "updatedAt": ""}
        for first in LETTERS for second in LETTERS
    ]
    themes = [
        {"id": "theme-complete", "label": "完整", "color": "#c88b38"},
        {"id": "theme-danger", "label": "危险", "color": "#a9482d"},
        {"id": "theme-life", "label": "生命", "color": "#557b52"},
    ]

    concepts: dict[str, dict[str, object]] = {}
    edges: list[dict[str, object]] = []

    def concept(label: str, status: str, source: str) -> str:
        identifier = stable_id("concept", label)
        existing = concepts.get(identifier)
        if existing is None:
            concepts[identifier] = {
                "id": identifier, "label": label, "synonyms": [], "themes": [],
                "status": status, "source": source, "note": "",
            }
        elif status == "confirmed":
            existing["status"] = "confirmed"
            existing["source"] = "user-confirmed"
        return identifier

    def edge(source: str, target: str, relation: str, status: str, origin: str) -> None:
        key = f"{source}|{relation}|{target}"
        edges.append({
            "id": stable_id("edge", key), "source": source, "target": target,
            "relation": relation, "status": status, "origin": origin, "note": "",
        })

    danger = concept("危险", "confirmed", "user-confirmed")
    complete = concept("完整", "confirmed", "user-confirmed")
    perfect = concept("完美", "confirmed", "user-confirmed")
    fullness = concept("圆满", "confirmed", "user-confirmed")
    edge("letter-v", danger, "唤起", "confirmed", "user-confirmed")
    for target in (complete, perfect, fullness):
        edge("letter-r", target, "唤起", "confirmed", "user-confirmed")
    circle_id = character_ids.get("○")
    if not circle_id:
        raise ValueError("精选 2000 中缺少 ○")
    edge(circle_id, complete, "象征", "confirmed", "user-confirmed")
    edge(circle_id, perfect, "象征", "confirmed", "user-confirmed")

    confirmed_character_ids = {circle_id}
    suggestion_count = 0
    suggested_characters: set[str] = set()
    for row, char_item in zip(rows, characters):
        if suggestion_count >= MAX_SUGGESTIONS:
            break
        if char_item["id"] in confirmed_character_ids or row.get("requires_base") == "true":
            continue
        label = association_for(row)
        if not label:
            continue
        concept_id = concept(label, "suggested", "machine-simple-v1")
        edge(char_item["id"], concept_id, "联想", "suggested", "machine-simple-v1")
        suggested_characters.add(str(char_item["id"]))
        suggestion_count += 1

    graph = {
        "version": 1,
        "createdAt": "2026-08-10",
        "updatedAt": "2026-08-10",
        "letters": letters,
        "pairs": pairs,
        "characters": characters,
        "concepts": sorted(concepts.values(), key=lambda item: str(item["id"])),
        "themes": themes,
        "edges": edges,
        "rimeAliases": [],
        "views": {"focusDepth": 2, "positions": {"global": {}, "theme": {}}},
        "metadata": {
            "selectionSize": 2000,
            "machineSuggestionCount": suggestion_count,
            "machineSuggestedCharacterCount": len(suggested_characters),
            "machinePolicy": "obvious-shape-and-common-symbolism-v1",
        },
    }
    return graph


def validate(graph: dict[str, object]) -> None:
    if graph.get("version") != 1:
        raise ValueError("图谱版本必须为 1")
    letters = graph.get("letters")
    pairs = graph.get("pairs")
    if not isinstance(letters, list) or {item["key"] for item in letters} != set(LETTERS):
        raise ValueError("图谱必须包含 26 个字母")
    expected_pairs = {a + b for a in LETTERS for b in LETTERS}
    if not isinstance(pairs, list) or {item["code"] for item in pairs} != expected_pairs:
        raise ValueError("图谱必须包含 676 个双字母")
    metadata = graph.get("metadata", {})
    if not isinstance(metadata, dict) or not 1 <= int(metadata.get("machineSuggestionCount", 0)) <= MAX_SUGGESTIONS:
        raise ValueError("机器建议数量不合法")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    if args.output.exists() and not args.force:
        raise SystemExit(f"图谱已存在，拒绝覆盖：{args.output}")
    graph = build()
    validate(graph)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(graph, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"生成联想图谱：{len(graph['characters']):,} 字符，{len(graph['pairs'])} 双字母，"
        f"{graph['metadata']['machineSuggestionCount']} 条机器建议。"
    )


if __name__ == "__main__":
    main()

