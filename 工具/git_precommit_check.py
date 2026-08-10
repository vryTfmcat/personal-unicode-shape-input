#!/usr/bin/env python3
"""Reject generated, oversized, or suspicious files before Git commits."""

from __future__ import annotations

import argparse
import re
import subprocess
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[1]
LIMIT = 10 * 1024 * 1024
FORBIDDEN = (
    re.compile(r"^数据/unicode全字符/"),
    re.compile(r"^数据/Unicode全码表/.*\.tsv$"),
    re.compile(r"^数据/Unicode精选/输出/(?!unicode-17-v1-2000(?:预览\.md|\.tsv)$)"),
    re.compile(r"^原型/键位编辑器/data/initial-data\.json$"),
    re.compile(r"^原型/rime/.*\.dict\.yaml$"),
    re.compile(r"(^|/)(?:备份|backups|__pycache__)(?:/|$)"),
)
SECRET = re.compile(r"(?i)(?:api[_-]?key|access[_-]?token|auth[_-]?token|password)\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{16,}")


def git(*args: str, text: bool = True):
    return subprocess.run(["git", *args], cwd=PROJECT, check=True, capture_output=True, text=text).stdout


def staged_files() -> list[str]:
    raw = git("diff", "--cached", "--name-only", "--diff-filter=ACMR", "-z", text=False)
    return [item.decode("utf-8") for item in raw.split(b"\0") if item]


def check(paths: list[str]) -> list[str]:
    errors: list[str] = []
    for relative in paths:
        normalized = relative.replace("\\", "/")
        if any(pattern.search(normalized) for pattern in FORBIDDEN):
            errors.append(f"禁止提交可再生成或备份文件：{normalized}")
            continue
        path = PROJECT / relative
        if path.is_file() and path.stat().st_size > LIMIT:
            errors.append(f"文件超过 10 MB：{normalized}")
        if path.is_file() and path.stat().st_size <= 2 * 1024 * 1024:
            try: content = path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError): continue
            if SECRET.search(content): errors.append(f"疑似密钥或口令：{normalized}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        assert check(["数据/unicode全字符/example.md"])
        assert check(["原型/rime/example.dict.yaml"])
        assert not check(["工具/build_catalog.py"])
        print("Git 提交检查自测通过。")
        return 0
    errors = check(staged_files())
    if errors:
        print("提交已阻止：")
        print("\n".join(f"- {error}" for error in errors))
        return 1
    print("Git 提交检查通过。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

