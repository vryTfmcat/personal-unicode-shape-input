"""Independent Unicode codebooks; deterministic drafts and versioned edits."""
from __future__ import annotations

import argparse
import collections
import copy
import hashlib
import json
import math
import os
import re
import tempfile
import urllib.request
from functools import lru_cache
from pathlib import Path

from build_all_unicode_keymap import (collect_blocks, prefix_candidates, keyword_key,
                                     MAIN_HINTS, STATE_HINTS, read_tsv, UCD)
from build_unicode_selection import parse_unicode_data
from build_hieroglyph_block import MAIN_LABELS, STATE_LABELS
from reviewed_shapes import REVIEWED_SHAPE_CODES

PROJECT = Path(__file__).resolve().parents[1]
DATA = PROJECT / "数据" / "三模式"
BOOK_PATH = DATA / "codebooks.json"
BASE_PATH = PROJECT / "原型" / "键位编辑器" / "data" / "mode-data.json"
FLYPY_PATH = DATA / "flypy-ixdata-20260930.json"
FLYPY_URL = "https://flypy.cc/ix/ixdata.json"
FLYPY_SHA = "4d3b84355fc52f76f8504efb824af09645c652208db4724a2c735d46a3c59262"
LETTERS = "abcdefghijklmnopqrstuvwxyz"
PAIRS = [a + b for a in LETTERS for b in LETTERS]
RULE_VERSION = "block-balanced-v1"


def atomic_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(value, handle, ensure_ascii=False, separators=(",", ":"))
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def is_han_block(name: str) -> bool:
    return name.startswith(("CJK Unified Ideographs", "CJK Compatibility Ideographs"))


def pin_flypy() -> dict:
    if not FLYPY_PATH.exists():
        raw = urllib.request.urlopen(FLYPY_URL, timeout=30).read()
        if hashlib.sha256(raw).hexdigest() != FLYPY_SHA:
            raise ValueError("小鹤来源已变化；请先审核差异，不能替换锁定版本")
        FLYPY_PATH.parent.mkdir(parents=True, exist_ok=True)
        FLYPY_PATH.write_bytes(raw)
    raw = FLYPY_PATH.read_bytes()
    if hashlib.sha256(raw).hexdigest() != FLYPY_SHA:
        raise ValueError("锁定小鹤数据的 SHA256 不符")
    return json.loads(raw)


def han_codes() -> tuple[dict, list]:
    result, issues = {}, []
    for char, item in pin_flypy().items():
        tokens = str(item.get("1", "")).split()
        codes = []
        for token in tokens:
            match = re.fullmatch(r"([a-z]{4})([-+*]*)", token)
            if match:
                codes.append({"code": match[1], "marks": match[2]})
            else:
                issues.append({"char": char, "raw": token, "reason": "不是完整四字母码"})
        if codes:
            result[char] = {"codes": codes, "pinyin": item.get("4", ""),
                            "structure": item.get("2", ""), "components": item.get("3", ""),
                            "extended": not 0x4E00 <= ord(char) <= 0x9FFF}
    return result, issues


def coarse_shape(cp: int, name: str, category: str) -> dict | None:
    char = chr(cp)
    # These are glyph suggestions, never inherited machine slot assignments.
    simple = {"0": "oe", "O": "oe", "o": "oe", "Ο": "oe", "ο": "oe", "О": "oe", "о": "oe",
              "○": "oe", "◌": "de", "●": "of", "⦿": "oi", "ᗚ": "cg", "ᗣ": "te"}
    code = simple.get(char) or (REVIEWED_SHAPE_CODES.get(char, "")[2:] or None)
    origin = "参考旧人工字形判断，重新待核对" if code else "Unicode 名称的完整形状词，待核对"
    if not code:
        main = keyword_key(name, MAIN_HINTS)
        if "CIRCLED" in name.split():
            main = "o"
        if not main:
            return None
        state = keyword_key(name, STATE_HINTS)
        if not state:
            state = {"o": "e", "t": "e", "s": "e", "x": "s", "r": "s",
                     "l": "h", "d": "e", "w": "h", "c": "g", "v": "g"}.get(main)
        if not state:
            return None
        code = main + state
    return {"mode": "shape", "coarse": code, "detail": None, "status": "draft", "ruleVersion": "coarse-v1",
            "reference": "Segoe UI Symbol / Segoe UI；缺字时待补字体", "evidence": origin}


def seed_codebooks() -> dict:
    book = {"version": 1, "blockOverrides": {}, "shapeOverrides": {}, "prefixOverrides": {},
            "rules": {}, "personal": {}, "metadata": {}, "commonOrder": [], "migrations": {}}
    def add(item_id, code, note, origin):
        if not re.fullmatch(r"[a-z]{2,4}", code):
            return
        aliases = book["personal"].setdefault(item_id, [])
        if not any(a["code"] == code for a in aliases):
            aliases.append({"mode": "personal", "code": code, "enabled": False, "status": "pending", "ruleVersion": "legacy-migration-v1", "note": note, "origin": origin})
    from build_catalog import parse_frontmatter
    for path in (PROJECT / "实体" / "字符").glob("*.md"):
        entry = parse_frontmatter(path)
        if entry.get("status") == "active":
            add(entry["id"], entry.get("input_code", ""), entry.get("note", ""), "旧人工码")
            if entry.get("note"):
                book["metadata"].setdefault(entry["id"], {})["note"] = entry["note"]
    for char, code in REVIEWED_SHAPE_CODES.items():
        add(f"u-{ord(char):04x}", code, "2026-10-05 图形确认记录；新收藏默认停用", "旧图形复核")
    graph_file = PROJECT / "数据" / "联想图谱" / "association-graph.json"
    if graph_file.exists():
        graph = json.loads(graph_file.read_text(encoding="utf-8"))
        for alias in graph.get("rimeAliases", []):
            add(alias["characterId"], alias["prefix"] + alias["suffix"], alias.get("note", ""), "旧联想别名")
    initial = PROJECT / "原型" / "键位编辑器" / "data" / "initial-data.json"
    if initial.exists():
        old = json.loads(initial.read_text(encoding="utf-8"))
        book["commonOrder"] = old.get("commonOrder", [])
        for c in old.get("characters", []):
            if c.get("favorite"):
                book["metadata"].setdefault(c["id"], {})["favorite"] = True
    book["migrations"]["project-legacy-v1"] = True
    return book


@lru_cache(maxsize=1)
def base_data() -> dict:
    blocks = sorted(collect_blocks(), key=lambda b: b.start)
    ucd = {cp: (name, category) for cp, name, category in parse_unicode_data(UCD)}
    han, issues = han_codes()
    characters, block_rows = [], []
    used = set()
    for block in blocks:
        block_id = f"block-{block.start:04x}"
        chars = []
        prefixes = []
        if not is_han_block(block.name):
            candidates = prefix_candidates(block.name)
            # Avoid the round shape namespace first; retain it as a capacity fallback.
            candidates.sort(key=lambda p: p.startswith("o"))
            prefixes = [p for p in candidates if p not in used][:math.ceil(len(block.codepoints) / 676)]
            if len(prefixes) != math.ceil(len(block.codepoints) / 676):
                raise ValueError("前缀资源不足")
            used.update(prefixes)
        for cp in block.codepoints:
            name, category = ucd[cp]
            chars.append({"id": f"u-{cp:04x}", "char": chr(cp), "codepoint": f"U+{cp:04X}",
                          "unicodeName": name, "category": category, "plane": cp >> 16,
                          "blockId": block_id, "sourceBlock": block.name, "han": is_han_block(block.name),
                          "blockCode": None, "shape": None if is_han_block(block.name) else coarse_shape(cp, name, category),
                          "chinese": han.get(chr(cp))})
        ordered = sorted(chars, key=lambda c: ((c["shape"] or {}).get("coarse", "zz"), c["codepoint"]))
        for index, c in enumerate(ordered if prefixes else []):
            # A diagonal traversal spreads both letters in small blocks without invented geometry.
            slot = index % 676
            suffix = LETTERS[slot % 26] + LETTERS[(slot // 26 + slot % 26) % 26]
            c["blockCode"] = {"mode": "block", "code": prefixes[index // 676] + suffix, "status": "draft",
                              "ruleVersion": RULE_VERSION, "evidence": "局部形族排序＋均衡序位；机器暂有码"}
        block_rows.append({"id": block_id, "name": block.name, "plane": block.start >> 16,
                           "start": f"U+{block.start:04X}", "end": f"U+{block.end:04X}",
                           "count": len(chars), "han": is_han_block(block.name), "prefixes": prefixes,
                           "rules": {"main": {k: f"局部组 {i+1}（待核对）" for i, k in enumerate(LETTERS)},
                                     "state": {k: f"组内位置 {i+1}（待核对）" for i, k in enumerate(LETTERS)},
                                     "note": "键义仅属于本区块；机器序位不代表已确认字形", "version": RULE_VERSION}})
        characters.extend(chars)
    result = {"version": 4, "unicodeVersion": "17.0.0", "characters": characters, "blocks": block_rows,
            "shapeRules": {"main": MAIN_LABELS, "state": STATE_LABELS},
            "chineseSource": {"url": FLYPY_URL, "sha256": FLYPY_SHA, "sourceModified": "2026-09-30",
                              "readDate": "2026-10-05",
                              "uro": sum(not v["extended"] for v in han.values()),
                              "extended": sum(v["extended"] for v in han.values()), "issues": issues},
            "statistics": {"characters": len(characters), "nonHan": sum(not c["han"] for c in characters),
                           "prefixes": len(used), "blocks": sum(not b["han"] for b in block_rows)}}
    stage_path = DATA / "shape-stage.json"
    if stage_path.exists():
        stage = json.loads(stage_path.read_text(encoding="utf-8"))
        result["shapeStage"] = {key: stage[key] for key in ("format", "id", "date", "title", "statistics")}
        result["shapeStage"]["url"] = "data/shape-stage.json"
    return result


def validate_codebooks(book: object, base: dict | None = None) -> dict:
    if not isinstance(book, dict) or book.get("version") != 1:
        raise ValueError("码本必须是 version 1 对象")
    base = base or base_data()
    by_id = {c["id"]: c for c in base["characters"]}
    prefix_owner = {p: b["id"] for b in base["blocks"] for p in b["prefixes"]}
    for key in ("blockOverrides", "shapeOverrides", "prefixOverrides", "rules", "personal", "metadata", "migrations"):
        if not isinstance(book.get(key), dict):
            raise ValueError(f"缺少 {key}")
    if not isinstance(book.get("commonOrder"), list) or any(i not in by_id for i in book["commonOrder"]):
        raise ValueError("收藏顺序包含未知字符")
    overrides = book["prefixOverrides"]
    if any(p not in prefix_owner or not re.fullmatch(r"[a-z]{2}", str(v)) for p, v in overrides.items()):
        raise ValueError("前缀必须是两字母且对应已有分配")
    final_prefixes = [overrides.get(p, p) for p in prefix_owner]
    if len(set(final_prefixes)) != len(final_prefixes):
        raise ValueError("不同前缀页不能占用同一前缀")
    final_owner = {overrides.get(p, p): b for p, b in prefix_owner.items()}
    for key in ("blockOverrides", "shapeOverrides", "personal", "metadata"):
        if any(item_id not in by_id for item_id in book[key]):
            raise ValueError(f"{key} 包含未知字符")
    for item_id, value in book["blockOverrides"].items():
        c = by_id[item_id]
        if c["han"] or not isinstance(value, dict) or not re.fullmatch(r"[a-z]{4}", str(value.get("code", ""))):
            raise ValueError("区块码必须是非汉字的四字母码")
        if final_owner.get(value["code"][:2]) != c["blockId"]:
            raise ValueError("只能使用字符真实区块拥有的前缀")
        if value.get("status") not in ("draft", "reviewed"):
            raise ValueError("未知审核状态")
        value.setdefault("mode", "block"); value.setdefault("ruleVersion", RULE_VERSION)
        if value["mode"] != "block" or not isinstance(value["ruleVersion"], str): raise ValueError("区块记录模式或规则版本错误")
    for value in book["shapeOverrides"].values():
        if not isinstance(value, dict) or value.get("detail") is not None:
            raise ValueError("兼容 detail 字段保持空值；细分使用 paths 列表")
        if value.get("coarse") is not None and not re.fullmatch(r"[a-z]{2}", str(value["coarse"])):
            raise ValueError("全形粗码必须为空或两字母")
        if value.get("status") not in ("draft", "reviewed"):
            raise ValueError("未知审核状态")
        value.setdefault("mode", "shape"); value.setdefault("ruleVersion", "coarse-v1")
        if value["mode"] != "shape" or not isinstance(value["ruleVersion"], str): raise ValueError("全形记录模式或规则版本错误")
        paths = value.get("paths", [])
        if not isinstance(paths, list): raise ValueError("全形 paths 应为列表")
        seen_paths = set()
        for path in paths:
            if not isinstance(path, dict) or not re.fullmatch(r"[a-z]{4}", str(path.get("code", ""))):
                raise ValueError("全形路径需要四字母码")
            if path["code"] in seen_paths: raise ValueError("同字同码不能重复")
            if path.get("status") not in ("draft", "reviewed") or not isinstance(path.get("enabled"), bool):
                raise ValueError("路径需要审核与启用状态")
            if any(not isinstance(path.get(k), str) or not path[k].strip() for k in ("basis", "font", "ruleVersion")):
                raise ValueError("路径需有取形依据、字体与规则版本")
            seen_paths.add(path["code"])
    for aliases in book["personal"].values():
        if not isinstance(aliases, list):
            raise ValueError("收藏别名应是列表")
        seen = set()
        for alias in aliases:
            if not isinstance(alias, dict) or not re.fullmatch(r"[a-z]{2,4}", str(alias.get("code", ""))) or not isinstance(alias.get("enabled"), bool):
                raise ValueError("收藏码应为 2–4 字母并有启用状态")
            if alias["code"] in seen:
                raise ValueError("同一字符收藏码重复")
            alias.setdefault("mode", "personal"); alias.setdefault("status", "reviewed" if alias["enabled"] else "pending"); alias.setdefault("ruleVersion", "personal-v1")
            if alias["mode"] != "personal" or alias["status"] not in ("pending","draft","reviewed") or not isinstance(alias["ruleVersion"], str): raise ValueError("收藏记录模式、审核状态或规则版本错误")
            seen.add(alias["code"])
    block_ids = {b["id"] for b in base["blocks"]}
    for block_id, rules in book["rules"].items():
        if block_id not in block_ids or not isinstance(rules, dict):
            raise ValueError("未知区块规则")
        for field in ("main", "state"):
            if not isinstance(rules.get(field), dict) or any(k not in LETTERS or not isinstance(v, str) for k, v in rules[field].items()):
                raise ValueError("局部规则应以 a–z 为键")
    for value in book["metadata"].values():
        if not isinstance(value, dict) or any(k not in ("favorite", "note", "ipa", "language", "pronunciationText", "pronunciationSource", "pronunciationStatus") for k in value):
            raise ValueError("无效的字符资料字段")
        if any((not isinstance(v, bool) if k == "favorite" else not isinstance(v, str)) for k, v in value.items()):
            raise ValueError("字符资料应为文本，收藏状态应为布尔值")
    experiments = book.get("shapeExperiments", {})
    if not isinstance(experiments, dict) or any(not re.fullmatch(r"[a-z]{2}", code) or not isinstance(note, str) for code,note in experiments.items()):
        raise ValueError("全形试验资料必须是两码形族的文本说明")
    return book


def effective_data(base: dict, book: dict) -> dict:
    result = copy.deepcopy(base)
    from shape_review_profile import load,assignments
    review=load()
    review_rows=assignments(review[1]) if review else {}
    if review:
        result['shapeReviewProfile']=review[0]
        result['shapeReviewOrder']=list(review_rows)
    for block in result["blocks"]:
        block["prefixes"] = [book["prefixOverrides"].get(p, p) for p in block["prefixes"]]
        if block["id"] in book["rules"]:
            block["rules"] = book["rules"][block["id"]]
    for c in result["characters"]:
        if c["blockCode"]:
            old = c["blockCode"]["code"]
            c["blockCode"]["code"] = book["prefixOverrides"].get(old[:2], old[:2]) + old[2:]
        if c["id"] in book["blockOverrides"]:
            c["blockCode"] = book["blockOverrides"][c["id"]]
        if c["id"] in book["shapeOverrides"]:
            c["shape"] = book["shapeOverrides"][c["id"]]
        c["personal"] = book["personal"].get(c["id"], [])
        c["metadata"] = book["metadata"].get(c["id"], {})
        if review:c['shapeReview']=review_rows.get(ord(c['char']))
    return result


def candidate_index(data: dict) -> dict:
    index = {key: collections.defaultdict(list) for key in ("personal", "block", "shape", "chinese", "extended")}
    for c in data["characters"]:
        for alias in c["personal"]:
            if alias["enabled"]:
                index["personal"][alias["code"]].append(c)
        if c["blockCode"]:
            index["block"][c["blockCode"]["code"]].append(c)
        if data.get('shapeReviewProfile'):
            pass # Preserve the immutable review-index order in the second pass.
        elif c["shape"] and c["shape"].get("coarse"):
            index["shape"][c["shape"]["coarse"]].append(c)
        for path in ([] if data.get('shapeReviewProfile') else (c.get("shape") or {}).get("paths", [])):
            if path["enabled"] and path["status"] == "reviewed":
                for length in (2, 3, 4):
                    key = path["code"][:length]
                    if not any(x["id"] == c["id"] for x in index["shape"][key]): index["shape"][key].append(c)
        if c["chinese"]:
            layer = "extended" if c["chinese"]["extended"] else "chinese"
            for item in c["chinese"]["codes"]:
                index[layer][item["code"]].append(c)
    if data.get('shapeReviewProfile'):
        from shape_review_profile import codes
        lookup={ord(c['char']):c for c in data['characters']}
        for cp in data['shapeReviewOrder']:
            c=lookup[cp]
            for code in codes(c['shapeReview']):index['shape'][code].append(c)
    return index


def query_candidates(index: dict, code: str, modes: list[str], chinese=False, extended=False) -> list:
    result = {}
    for layer in ("personal", "block", "shape", "chinese", "extended"):
        enabled = layer in modes if layer in ("personal", "block", "shape") else chinese and (layer != "extended" or extended)
        if not enabled:
            continue
        for c in index[layer].get(code, []):
            row = result.setdefault(c["id"], {"id": c["id"], "char": c["char"], "sources": []})
            if layer not in row["sources"]:
                row["sources"].append(layer)
    return list(result.values())


def write() -> dict:
    base = base_data()
    atomic_json(BASE_PATH, base)
    if (DATA / "shape-stage.json").exists():
        atomic_json(BASE_PATH.parent / "shape-stage.json", json.loads((DATA / "shape-stage.json").read_text(encoding="utf-8")))
    if not BOOK_PATH.exists():
        atomic_json(BOOK_PATH, seed_codebooks())
    book = json.loads(BOOK_PATH.read_text(encoding="utf-8"))
    before = json.dumps(book, ensure_ascii=False, sort_keys=True)
    validate_codebooks(book, base)
    if json.dumps(book, ensure_ascii=False, sort_keys=True) != before:
        atomic_json(BOOK_PATH, book)
    atomic_json(DATA / "flypy-source.json", base["chineseSource"])
    return base


if __name__ == "__main__":
    write()
    print("Unicode 三模式数据已生成；已有人工码本保留。")
