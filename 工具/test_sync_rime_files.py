#!/usr/bin/env python3
"""Test Rime synchronization in a temporary directory."""

from __future__ import annotations

import tempfile
from pathlib import Path

from sync_rime_files import FILES, sync


def main() -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        target, backups = root / "Rime", root / "backups"
        target.mkdir()
        (target / "personal_unicode.schema.yaml").write_text("old\n", encoding="utf-8")
        backup, synced = sync(target, backups)
        assert synced == list(FILES)
        assert (backup / "personal_unicode.schema.yaml").read_text(encoding="utf-8") == "old\n"
        assert all((target / name).is_file() for name in FILES)
        assert (backup / "manifest.json").is_file()
    print("Rime 文件备份与同步校验通过。")


if __name__ == "__main__":
    main()
