#!/usr/bin/env python3
import csv
import sys
from collections import Counter
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[1]
TABLE = PROJECT / "数据" / "𓆟字块-编码.tsv"
MAIN_KEYS = set("abcdefghijklmnopqrstuvwxyz")
STATE_KEYS = set("abcdefghijklmnopqrstuvwxyz")


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    with TABLE.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    assert len(rows) == 1072
    assert len({row["char"] for row in rows}) == 1072
    assert rows[0]["codepoint"] == "U+13000"
    assert rows[-1]["codepoint"] == "U+1342F"
    assert all(row["main_key"] in MAIN_KEYS for row in rows)
    assert all(row["state_key"] in STATE_KEYS for row in rows)
    assert Counter(row["prefix"] for row in rows) == {"jj": 429, "jn": 163, "jw": 274, "jx": 206}
    assert all(row["input_code"] == row["prefix"] + row["main_key"] + row["state_key"] for row in rows)
    assert all(row["status"] in {"machine-initial-v3", "reviewed"} for row in rows)
    code_counts = Counter(row["input_code"] for row in rows)
    assert len(code_counts) == 303
    assert max(code_counts.values()) <= 5
    fish = next(row for row in rows if row["char"] == "𓆟")
    assert fish["input_code"] == "jjgh"
    print("hieroglyph block tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
