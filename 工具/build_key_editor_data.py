#!/usr/bin/env python3
"""Build the local editor's complete Unicode 17 initial dataset."""

from __future__ import annotations

import csv
import json
from copy import deepcopy
from pathlib import Path

from build_hieroglyph_block import MAIN_LABELS, STATE_LABELS


PROJECT = Path(__file__).resolve().parents[1]
ALL_TSV = PROJECT / "数据" / "Unicode全码表" / "unicode-17-全字符编码.tsv"
PAGES_TSV = PROJECT / "数据" / "Unicode全码表" / "unicode-17-前缀页.tsv"
OUTPUT = PROJECT / "原型" / "键位编辑器" / "data" / "initial-data.json"

COMMON = [
    ("ଉ", "boki"), ("Պ", "ascg"), ("○", "yboe"), ("◌", "axde"),
    ("⦿", "ddoi"), ("●", "fpof"), ("𒁔", "mvma"), ("ᗚ", "qdcg"),
    ("ஆ", "pici"), ("ᗣ", "lnte"),
]


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def build() -> dict[str, object]:
    pages = [{
        "id": "common", "prefix": "", "name": "常用字符",
        "block": "固定收藏（不改变字符原归属）",
        "description": "拖到这里会加入收藏；从这里编辑会同步到字符本体。",
        "mainRules": deepcopy(MAIN_LABELS), "stateRules": deepcopy(STATE_LABELS),
    }]
    for row in read_tsv(PAGES_TSV):
        pages.append({
            "id": row["prefix"], "prefix": row["prefix"], "name": row["name"],
            "block": row["block"], "description": row["description"],
            "mainRules": deepcopy(MAIN_LABELS), "stateRules": deepcopy(STATE_LABELS),
        })

    favorite_codes = dict(COMMON)
    characters = []
    for row in read_tsv(ALL_TSV):
        character = row["char"]
        characters.append({
            "id": "u-" + row["codepoint"][2:].lower(),
            "char": character,
            "codepoint": row["codepoint"],
            "unicodeName": row["unicode_name"],
            "code": row["input_code"],
            "pageId": row["prefix"],
            "favorite": character in favorite_codes,
            "sourceBlock": row["block"],
            "mainKey": row["main_key"],
            "stateKey": row["state_key"],
            "note": row["status"] + "；" + row["allocation"],
        })
    by_char = {item["char"]: item for item in characters}
    for character, code in COMMON:
        if character not in by_char or by_char[character]["code"] != code:
            raise ValueError(f"常用锚点未保留：{character}={code}")
    return {
        "version": 3,
        "storageKey": "unicode-key-editor-v3",
        "pages": pages,
        "characters": characters,
        "commonOrder": [by_char[character]["id"] for character, _ in COMMON],
    }


def main() -> None:
    payload = build()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    print(f"生成编辑器数据：{len(payload['characters']):,} 个字符，{len(payload['pages']) - 1} 个前缀页，常用 {len(payload['commonOrder'])} 个。")


if __name__ == "__main__":
    main()
