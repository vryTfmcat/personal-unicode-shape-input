#!/usr/bin/env python3
"""Build a self-contained, privacy-scoped key editor archive for sharing."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import zipfile
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[1]
EDITOR = PROJECT / "原型" / "键位编辑器"
GRAPH = PROJECT / "数据" / "联想图谱" / "association-graph.json"
RELEASE = PROJECT / "发布"
NAME = "Unicode音型键位编辑器-v0.2.0-分享版"
STAGING = RELEASE / NAME
ARCHIVE = RELEASE / f"{NAME}.zip"

LAUNCHER = r'''@echo off
chcp 65001 >nul
cd /d "%~dp0"
where py >nul 2>nul
if not errorlevel 1 (
  py -3 serve.py
  goto done
)
where python >nul 2>nul
if not errorlevel 1 (
  python serve.py
  goto done
)
echo.
echo 未找到 Python 3，暂时无法启动。
echo 请先从 https://www.python.org/downloads/windows/ 安装 Python 3，
echo 安装时勾选 Add Python to PATH，然后重新双击本文件。
echo.
pause
:done
if errorlevel 1 pause
'''

README = '''# Unicode 音型键位编辑器分享版

这是一个只在本机运行的 Unicode 字符与个人联想实验编辑器，包含 159,345 个 Unicode 17 字符、26×26 双字母感觉面板和联想图谱。

## 启动

1. 完整解压 ZIP，不要直接在压缩包内运行。
2. Windows 电脑需安装 Python 3；安装时勾选 “Add Python to PATH”。
3. 双击 `启动键位编辑器.cmd`。
4. 浏览器会打开 `http://127.0.0.1:8765/`；关闭命令窗口即可停止。

程序只监听本机地址，不会发布到互联网。修改后的联想图谱保存在本文件夹的 `data/association-graph.json`，快照保存在 `backups/`。字符键位草稿仍保存在当前浏览器，并可导出 TSV。

字体是否能显示某些字符取决于电脑已安装的字体；显示方框不代表字符数据损坏。

## 隐私说明

这是从项目生成的公开演示副本，不包含个人笔记、原始资料库、文件来源路径、电脑用户名、实体页、Rime 配置或图谱个人备注。朋友的修改只保存在他自己的解压目录或浏览器中，不会连接原项目。
'''

FORBIDDEN_TEXT = (
    "C:\\Users", "C:/Users", "Documents", "AppData", "Obsidian-codx",
    "90_旧库", "冷归档", "2025Obsidian", "茂ܜ", "日记", "身份证", "住址",
)
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE = re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)")


def standalone_server(source: str) -> str:
    source = source.replace(
        'PROJECT = ROOT.parents[1]\nTOOLS = PROJECT / "工具"\nif str(TOOLS) not in sys.path:\n    sys.path.insert(0, str(TOOLS))\nfrom sync_association_entities import sync as sync_association_entities  # noqa: E402\nGRAPH_PATH = PROJECT / "数据" / "联想图谱" / "association-graph.json"\nBACKUP_DIR = PROJECT / "数据" / "联想图谱" / "备份"',
        'GRAPH_PATH = ROOT / "data" / "association-graph.json"\nBACKUP_DIR = ROOT / "backups"',
    )
    source = source.replace(
        '            if self.entity_project is not None:\n                sync_association_entities(validated, self.entity_project)\n',
        '',
    )
    source = source.replace('store = GraphStore(entity_project=PROJECT)', 'store = GraphStore()')
    source = source.replace(
        '图谱修改会直接保存到项目；关闭这个窗口即可停止本地服务。',
        '图谱修改只保存到当前解压目录；关闭这个窗口即可停止本地服务。',
    )
    if "sync_association_entities" in source or "PROJECT =" in source:
        raise RuntimeError("未能生成独立服务器：仍存在项目依赖")
    return source


def public_initial_data() -> dict:
    """Keep only fields required by the editor; drop free-form per-character notes."""
    source = json.loads((EDITOR / "data" / "initial-data.json").read_text(encoding="utf-8"))
    page_fields = ("id", "prefix", "name", "block", "description", "mainRules", "stateRules")
    char_fields = (
        "id", "char", "codepoint", "unicodeName", "code", "pageId", "favorite",
        "sourceBlock", "mainKey", "stateKey",
    )
    return {
        "version": source["version"],
        "storageKey": "unicode-key-editor-public-demo-v1",
        "pages": [{key: page[key] for key in page_fields if key in page} for page in source["pages"]],
        "characters": [{key: char[key] for key in char_fields if key in char} for char in source["characters"]],
    }


def public_graph() -> dict:
    """Strip personal notes, provenance, aliases, timestamps, and saved canvas state."""
    graph = json.loads(GRAPH.read_text(encoding="utf-8"))
    for letter in graph["letters"]:
        for key in ("note", "description"):
            if key in letter:
                letter[key] = ""
    for pair in graph["pairs"]:
        for key in ("note", "description"):
            if key in pair:
                pair[key] = ""
    for collection in ("characters", "concepts", "themes"):
        for node in graph[collection]:
            node.pop("note", None)
            node.pop("modifiedBy", None)
            node.pop("updatedAt", None)
    for edge in graph["edges"]:
        edge.pop("note", None)
        edge.pop("modifiedBy", None)
        edge.pop("updatedAt", None)
    graph["rimeAliases"] = []
    graph["views"] = {"focusDepth": 2, "positions": {"global": {}, "theme": {}}}
    graph.pop("updatedAt", None)
    graph["metadata"] = {
        "selectionSize": len(graph["characters"]),
        "machineSuggestionCount": sum(edge.get("status") == "suggested" for edge in graph["edges"]),
        "machinePolicy": "obvious-shape-and-common-symbolism-v1",
        "privacyScope": "public-demo-no-personal-notes",
    }
    return graph


def audit_privacy(root: Path) -> None:
    failures: list[str] = []
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in {".html", ".css", ".js", ".py", ".json", ".md", ".cmd"}:
            continue
        text = path.read_text(encoding="utf-8-sig", errors="strict")
        for needle in FORBIDDEN_TEXT:
            if needle.casefold() in text.casefold():
                failures.append(f"{path.relative_to(root)}：包含 {needle}")
        if EMAIL.search(text):
            failures.append(f"{path.relative_to(root)}：疑似邮箱")
        if PHONE.search(text):
            failures.append(f"{path.relative_to(root)}：疑似手机号")
    if failures:
        raise RuntimeError("分享包隐私检查失败：\n" + "\n".join(failures))


def build() -> tuple[Path, str]:
    RELEASE.mkdir(exist_ok=True)
    if STAGING.exists():
        shutil.rmtree(STAGING)
    STAGING.mkdir()
    (STAGING / "data").mkdir()
    for name in ("index.html", "styles.css", "app.js", "association.js"):
        shutil.copy2(EDITOR / name, STAGING / name)
    (STAGING / "data" / "initial-data.json").write_text(
        json.dumps(public_initial_data(), ensure_ascii=False, separators=(",", ":")), encoding="utf-8", newline="\n"
    )
    (STAGING / "data" / "association-graph.json").write_text(
        json.dumps(public_graph(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    server = standalone_server((EDITOR / "serve.py").read_text(encoding="utf-8"))
    (STAGING / "serve.py").write_text(server, encoding="utf-8", newline="\n")
    (STAGING / "启动键位编辑器.cmd").write_text(LAUNCHER, encoding="utf-8", newline="\r\n")
    (STAGING / "请先看我.md").write_text(README, encoding="utf-8", newline="\n")
    audit_privacy(STAGING)

    if ARCHIVE.exists():
        ARCHIVE.unlink()
    with zipfile.ZipFile(ARCHIVE, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(STAGING.rglob("*")):
            if path.is_file():
                archive.write(path, (Path(NAME) / path.relative_to(STAGING)).as_posix())
    shutil.rmtree(STAGING)
    digest = hashlib.sha256(ARCHIVE.read_bytes()).hexdigest()
    (RELEASE / f"{NAME}.sha256").write_text(f"{digest}  {ARCHIVE.name}\n", encoding="utf-8")
    return ARCHIVE, digest


if __name__ == "__main__":
    archive, digest = build()
    print(f"已生成：{archive}")
    print(f"SHA-256：{digest}")
