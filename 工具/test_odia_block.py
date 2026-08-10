#!/usr/bin/env python3
import csv
from collections import Counter
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[1]
TABLE = PROJECT / "数据" / "ଉ字块-编码.tsv"


def main() -> int:
    with TABLE.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    assert len(rows) == 91
    assert len({row["char"] for row in rows}) == 91
    assert all(row["prefix"] == "bo" for row in rows)
    assert all(row["input_code"] == "bo" + row["main_key"] + row["state_key"] for row in rows)
    assert max(Counter(row["input_code"] for row in rows).values()) <= 5
    assert next(row for row in rows if row["codepoint"] == "U+0B09")["input_code"] == "boki"
    print("odia block tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
