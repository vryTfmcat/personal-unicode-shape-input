#!/usr/bin/env python3
"""Synchronize enabled graph aliases into confirmed Obsidian entity pages."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


PROJECT = Path(__file__).resolve().parents[1]
GRAPH_SOURCE = "30_项目/个人Unicode音型输入法/数据/联想图谱/association-graph.json"


def parse_simple_frontmatter(text: str) -> dict[str, Any]:
    lines = text.splitlines()
    if not lines or lines[0] != "---":
        raise ValueError("实体页缺少 frontmatter")
    end = lines.index("---", 1)
    result: dict[str, Any] = {}
    index = 1
    while index < end:
        line = lines[index]
        if not line.strip():
            index += 1; continue
        if ":" not in line or line.startswith(" "):
            index += 1; continue
        key, raw = line.split(":", 1)
        raw = raw.strip()
        if raw:
            if raw in {"true", "false"}: result[key] = raw == "true"
            elif raw.startswith("["): result[key] = json.loads(raw)
            elif raw.startswith('"'): result[key] = json.loads(raw)
            else: result[key] = raw
            index += 1; continue
        values = []
        index += 1
        while index < end and lines[index].startswith("  - "):
            values.append(lines[index][4:])
            index += 1
        result[key] = values
    return result


def scalar(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, list):
        return json.dumps(value, ensure_ascii=False)
    return json.dumps(str(value), ensure_ascii=False)


def update_fields(text: str, fields: dict[str, Any]) -> str:
    lines = text.splitlines()
    end = lines.index("---", 1)
    for key, value in fields.items():
        replacement = f"{key}: {scalar(value)}"
        found = next((index for index in range(1, end) if lines[index].startswith(key + ":")), None)
        if found is None:
            lines.insert(end, replacement); end += 1
            continue
        remove_end = found + 1
        if lines[found].strip() == key + ":":
            while remove_end < end and lines[remove_end].startswith("  - "):
                remove_end += 1
        lines[found:remove_end] = [replacement]
        end -= remove_end - found - 1
    return "\n".join(lines).rstrip() + "\n"


def new_entity(character: dict[str, Any], aliases: list[dict[str, Any]], concepts: dict[str, dict[str, Any]]) -> str:
    primary = next((item for item in aliases if item.get("primary")), aliases[0])
    primary_code = str(primary["prefix"]) + str(primary["suffix"])
    other_codes = sorted({str(item["prefix"]) + str(item["suffix"]) for item in aliases if item is not primary})
    association_ids = sorted({str(identifier) for item in aliases for identifier in item.get("associationIds", [])})
    labels = [str(concepts[item].get("label", "")) for item in association_ids if item in concepts]
    display = str(character["char"])
    fields = [
        "---",
        f"id: {character['id']}",
        "type: character",
        f"display: {json.dumps(display, ensure_ascii=False)}",
        f"codepoints: [{json.dumps(character['codepoint'], ensure_ascii=False)}]",
        f"input_code: {primary_code}",
        f"input_aliases: {json.dumps(other_codes, ensure_ascii=False)}",
        f"mnemonic: {json.dumps('、'.join(labels), ensure_ascii=False)}",
        f"association_ids: {json.dumps(association_ids, ensure_ascii=False)}",
        f"shape_tags: {json.dumps(character.get('shapeTags', []), ensure_ascii=False)}",
        "status: active",
        "export_to_rime: true",
        "sources:",
        f"  - {GRAPH_SOURCE}",
        'note: "由个人联想图谱首次创建；停用全部联想码时保留页面但停止导出。"',
        "---",
        "",
        f"# {display}",
        "",
    ]
    return "\n".join(fields)


def sync(graph: dict[str, Any], project: Path = PROJECT) -> list[Path]:
    characters = {item["id"]: item for item in graph.get("characters", [])}
    concepts = {item["id"]: item for item in graph.get("concepts", [])}
    aliases_by_character: dict[str, list[dict[str, Any]]] = {}
    for alias in graph.get("rimeAliases", []):
        if alias.get("enabled") and alias.get("characterId") in characters:
            aliases_by_character.setdefault(alias["characterId"], []).append(alias)
    entity_dir = project / "实体" / "字符"
    entity_dir.mkdir(parents=True, exist_ok=True)
    changed: list[Path] = []
    managed_ids = set(aliases_by_character)
    for path in entity_dir.glob("u-*.md"):
        try:
            record = parse_simple_frontmatter(path.read_text(encoding="utf-8"))
        except (OSError, ValueError, json.JSONDecodeError):
            continue
        if record.get("association_ids") or GRAPH_SOURCE in record.get("sources", []):
            managed_ids.add(str(record.get("id", path.stem)))
    for identifier in sorted(managed_ids):
        character = characters.get(identifier)
        if not character:
            continue
        path = entity_dir / f"{identifier}.md"
        aliases = aliases_by_character.get(identifier, [])
        if not path.exists():
            if not aliases:
                continue
            path.write_text(new_entity(character, aliases, concepts), encoding="utf-8")
            changed.append(path); continue
        original = path.read_text(encoding="utf-8")
        record = parse_simple_frontmatter(original)
        primary = str(record.get("input_code", ""))
        graph_codes = [str(item["prefix"]) + str(item["suffix"]) for item in aliases]
        association_ids = sorted({str(value) for item in aliases for value in item.get("associationIds", [])})
        fields: dict[str, Any] = {
            "input_aliases": sorted({code for code in graph_codes if code != primary}),
            "association_ids": association_ids,
        }
        sources = record.get("sources", [])
        graph_only = sources == [GRAPH_SOURCE]
        if aliases:
            fields.update({"status": "active", "export_to_rime": True})
            if graph_only and primary not in graph_codes:
                chosen = next((item for item in aliases if item.get("primary")), aliases[0])
                fields["input_code"] = str(chosen["prefix"]) + str(chosen["suffix"])
                fields["input_aliases"] = sorted({code for code in graph_codes if code != fields["input_code"]})
        elif graph_only:
            fields.update({"status": "deferred", "export_to_rime": False, "input_aliases": [], "association_ids": []})
        updated = update_fields(original, fields)
        if updated != original:
            path.write_text(updated, encoding="utf-8")
            changed.append(path)
    return changed


def main() -> None:
    graph_path = PROJECT / "数据" / "联想图谱" / "association-graph.json"
    graph = json.loads(graph_path.read_text(encoding="utf-8"))
    changed = sync(graph)
    print(f"联想图谱实体同步完成：{len(changed)} 个页面有变化。")


if __name__ == "__main__":
    main()

