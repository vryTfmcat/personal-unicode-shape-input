#!/usr/bin/env python3
"""Validate the tracked personal association graph."""

from __future__ import annotations

import json
from collections import Counter

from build_association_graph import LETTERS, MAX_SUGGESTIONS, OUTPUT, build, validate


def main() -> None:
    graph = json.loads(OUTPUT.read_text(encoding="utf-8"))
    validate(graph)
    assert len(graph["characters"]) == 2000
    assert len(graph["letters"]) == 26
    assert len(graph["pairs"]) == 676
    assert {item["key"] for item in graph["letters"]} == set(LETTERS)
    assert next(item for item in graph["letters"] if item["key"] == "v")["meanings"] == ["危险"]
    assert "完美" in next(item for item in graph["letters"] if item["key"] == "r")["meanings"]
    suggestions = [edge for edge in graph["edges"] if edge["origin"] == "machine-simple-v1"]
    assert 1 <= len(suggestions) <= MAX_SUGGESTIONS
    counts = Counter(edge["source"] for edge in suggestions)
    assert max(counts.values()) == 1
    assert all(edge["status"] == "suggested" for edge in suggestions)
    assert not graph["rimeAliases"]
    circle = next(item["id"] for item in graph["characters"] if item["char"] == "○")
    circle_targets = {edge["target"] for edge in graph["edges"] if edge["source"] == circle and edge["status"] == "confirmed"}
    labels = {item["id"]: item["label"] for item in graph["concepts"]}
    assert {labels[target] for target in circle_targets} == {"完整", "完美"}
    regenerated = build()
    assert regenerated == graph
    print(f"联想图谱校验通过：{len(suggestions)} 条机器建议。")


if __name__ == "__main__":
    main()

