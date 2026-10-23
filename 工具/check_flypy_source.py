"""Compare upstream Flypy data with the pinned edition; never replace the pin."""
from __future__ import annotations
import hashlib
import json
import urllib.request
from datetime import datetime, timezone
from mode_codebooks import FLYPY_URL, FLYPY_SHA, pin_flypy


def compare(old: dict, current: dict) -> dict:
    return {
        "added": [{"char": c, "new": current[c]} for c in sorted(current.keys()-old.keys(), key=ord)],
        "removed": [{"char": c, "old": old[c]} for c in sorted(old.keys()-current.keys(), key=ord)],
        "changed": [{"char": c, "old": old[c], "new": current[c]} for c in sorted(old.keys()&current.keys(), key=ord) if old[c]!=current[c]],
    }


def check() -> dict:
    raw = urllib.request.urlopen(FLYPY_URL, timeout=25).read()
    current = json.loads(raw)
    if not isinstance(current, dict): raise ValueError("小鹤上游数据不是字符对象")
    return {"url": FLYPY_URL, "checkedAt": datetime.now(timezone.utc).isoformat(),
            "pinnedSha256": FLYPY_SHA, "currentSha256": hashlib.sha256(raw).hexdigest(),
            **compare(pin_flypy(), current)}


if __name__ == "__main__":
    print(json.dumps(check(), ensure_ascii=False, indent=2))
