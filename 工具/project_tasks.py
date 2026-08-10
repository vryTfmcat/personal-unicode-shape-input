#!/usr/bin/env python3
"""Unified build, test, packaging, and local deployment entry point."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[1]
TOOLS = PROJECT / "工具"
FULL_TABLE = PROJECT / "数据" / "unicode全字符"
OFFICIAL = FULL_TABLE / "官方结构"
NODE_CANDIDATES = (
    Path(os.environ.get("CODEX_NODE", "")),
    Path.home() / ".cache" / "codex-runtimes" / "codex-primary-runtime" / "dependencies" / "node" / "bin" / "node.exe",
)
PYTHON_CANDIDATES = (
    Path(os.environ.get("CODEX_PYTHON", "")),
    Path.home() / ".cache" / "codex-runtimes" / "codex-primary-runtime" / "dependencies" / "python" / "python.exe",
    Path(sys.executable),
)
TESTS = (
    "test_build_catalog.py",
    "test_unicode_selection.py",
    "test_unicode_full_table.py",
    "test_all_unicode_keymap.py",
    "test_hieroglyph_block.py",
    "test_odia_block.py",
    "test_additional_blocks.py",
    "test_association_graph.py",
    "test_association_entities.py",
    "test_association_server.py",
    "test_key_editor_data.py",
    "test_key_editor_static.py",
    "test_rime_profiles.py",
    "test_sync_rime_files.py",
)


def run(*arguments: str) -> None:
    print("→", " ".join(arguments), flush=True)
    subprocess.run(arguments, cwd=PROJECT, check=True)


def find_python() -> str:
    """Prefer a reproducible Python that includes the image-analysis dependencies."""
    for candidate in PYTHON_CANDIDATES:
        if not candidate.is_file():
            continue
        probe = subprocess.run(
            [str(candidate), "-c", "import numpy; from PIL import Image"],
            capture_output=True,
        )
        if probe.returncode == 0:
            return str(candidate)
    raise FileNotFoundError("找不到同时提供 NumPy 与 Pillow 的 Python；请在 Codex 工作区中运行")


def python_script(name: str, *arguments: str) -> None:
    run(find_python(), str(TOOLS / name), *arguments)


def ensure_full_table() -> None:
    if list(FULL_TABLE.glob("plane-*/*.md")):
        return
    FULL_TABLE.mkdir(parents=True, exist_ok=True)
    python_script("build_unicode_full_table.py")


def ensure_official_structure() -> None:
    if list(OFFICIAL.glob("plane-*/*.md")):
        return
    python_script("build_unicode_official_structure.py")


def build(vault_root: Path | None = None) -> None:
    ensure_full_table()
    ensure_official_structure()
    python_script("build_all_unicode_keymap.py")
    python_script("build_key_editor_data.py")
    graph = PROJECT / "数据" / "联想图谱" / "association-graph.json"
    if not graph.is_file():
        python_script("build_association_graph.py")
    python_script("sync_association_entities.py")
    catalog_args = ["--write"]
    if vault_root:
        catalog_args.extend(("--vault-root", str(vault_root)))
    python_script("build_catalog.py", *catalog_args)


def find_node() -> str:
    system = shutil.which("node")
    if system:
        return system
    for candidate in NODE_CANDIDATES:
        if str(candidate) and candidate.is_file():
            return str(candidate)
    raise FileNotFoundError("找不到 Node.js，无法校验编辑器 JavaScript")


def test() -> None:
    for name in TESTS:
        python_script(name)
    node = find_node()
    run(node, "--check", str(PROJECT / "原型" / "键位编辑器" / "app.js"))
    run(node, "--check", str(PROJECT / "原型" / "键位编辑器" / "association.js"))


def main() -> None:
    parser = argparse.ArgumentParser(description="个人 Unicode 音型输入法统一任务入口")
    parser.add_argument("command", choices=("build", "test", "check", "rime", "sync-rime"))
    parser.add_argument("--apply", action="store_true", help="sync-rime 时实际复制；默认只检查")
    parser.add_argument("--vault-root", type=Path, help="从项目目录外运行时，指定只读冷归档所在的 Obsidian 库根目录")
    args = parser.parse_args()
    if args.command == "build": build(args.vault_root)
    elif args.command == "test": test()
    elif args.command == "check": build(args.vault_root); test()
    elif args.command == "rime":
        catalog_args = ["--write"]
        if args.vault_root: catalog_args.extend(("--vault-root", str(args.vault_root)))
        python_script("build_catalog.py", *catalog_args)
    elif args.command == "sync-rime":
        python_script("sync_rime_files.py", *(["--apply"] if args.apply else []))


if __name__ == "__main__":
    main()
