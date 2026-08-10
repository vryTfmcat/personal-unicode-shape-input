#!/usr/bin/env python3
"""Back up and sync the two daily Rime profiles without redeploying Weasel."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import tempfile
from datetime import datetime
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[1]
SOURCE = PROJECT / "原型" / "rime"
BACKUPS = SOURCE / "备份"
FILES = (
    "personal_unicode.schema.yaml",
    "personal_unicode_han_bmp.schema.yaml",
    "personal_unicode_symbols.dict.yaml",
    "personal_unicode_han_bmp.dict.yaml",
    "default.custom.yaml",
)
LEGACY_BACKUP_ONLY = ("personal_unicode.dict.yaml",)


def atomic_copy(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temp_name = tempfile.mkstemp(prefix=target.name + ".", suffix=".tmp", dir=target.parent)
    os.close(descriptor)
    try:
        shutil.copy2(source, temp_name)
        os.replace(temp_name, target)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def sync(target_dir: Path, backup_root: Path = BACKUPS) -> tuple[Path, list[str]]:
    missing = [name for name in FILES if not (SOURCE / name).is_file()]
    if missing:
        raise FileNotFoundError("缺少 Rime 构建文件：" + "、".join(missing))
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_dir = backup_root / f"rime-sync-{stamp}"
    counter = 1
    while backup_dir.exists():
        backup_dir = backup_root / f"rime-sync-{stamp}-{counter:02d}"
        counter += 1
    backup_dir.mkdir(parents=True)
    backed_up = []
    for name in (*FILES, *LEGACY_BACKUP_ONLY):
        target = target_dir / name
        if target.is_file():
            shutil.copy2(target, backup_dir / name)
            backed_up.append(name)
    for name in FILES:
        atomic_copy(SOURCE / name, target_dir / name)
    manifest = {
        "createdAt": datetime.now().astimezone().isoformat(timespec="seconds"),
        "target": str(target_dir),
        "backedUp": backed_up,
        "synced": list(FILES),
        "weaselRedeployed": False,
    }
    (backup_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return backup_dir, list(FILES)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="perform the copy; without this flag only validate")
    parser.add_argument("--target", type=Path, default=Path(os.environ.get("APPDATA", "")) / "Rime")
    args = parser.parse_args()
    for name in FILES:
        if not (SOURCE / name).is_file():
            raise SystemExit(f"缺少 {name}；请先运行 build_catalog.py --write")
    if not args.apply:
        print("Rime 同步检查通过；加 --apply 才会复制，且不会重新部署小狼毫。")
        return
    backup, files = sync(args.target.resolve())
    print(f"已同步 {len(files)} 个 Rime 文件；备份：{backup}。尚未重新部署小狼毫。")


if __name__ == "__main__":
    main()

