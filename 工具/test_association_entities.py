#!/usr/bin/env python3
"""Validate graph-to-entity synchronization without touching the project."""

from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path

from sync_association_entities import parse_simple_frontmatter, sync


PROJECT = Path(__file__).resolve().parents[1]


def main() -> None:
    graph = json.loads((PROJECT / "数据" / "联想图谱" / "association-graph.json").read_text(encoding="utf-8"))
    graph = json.loads(json.dumps(graph, ensure_ascii=False))
    circle = next(item for item in graph["characters"] if item["char"] == "○")
    concept = next(item for item in graph["concepts"] if item["label"] == "完整")
    graph["rimeAliases"] = [{
        "id": "alias-test", "characterId": circle["id"], "prefix": "rr", "suffix": circle["shapeSuffix"],
        "enabled": True, "primary": False, "associationIds": [concept["id"]], "note": "",
    }]
    with tempfile.TemporaryDirectory() as temp:
        project = Path(temp)
        target = project / "实体" / "字符"
        target.mkdir(parents=True)
        shutil.copy2(PROJECT / "实体" / "字符" / "u-25cb.md", target / "u-25cb.md")
        changed = sync(graph, project)
        assert changed == [target / "u-25cb.md"]
        record = parse_simple_frontmatter((target / "u-25cb.md").read_text(encoding="utf-8"))
        assert record["input_code"] == "yboe"
        assert record["input_aliases"] == ["rroe"]
        assert record["association_ids"] == [concept["id"]]
        graph["rimeAliases"] = []
        sync(graph, project)
        record = parse_simple_frontmatter((target / "u-25cb.md").read_text(encoding="utf-8"))
        assert record["input_code"] == "yboe"
        assert record["input_aliases"] == []
    print("联想图谱实体页同步校验通过。")


if __name__ == "__main__":
    main()

