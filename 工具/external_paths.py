"""Local engineering inputs stay outside the Obsidian vault."""
from pathlib import Path
import os
import sys

PROJECT = Path(__file__).resolve().parents[1]

def external_root():
    override = os.environ.get("UNICODE_EXTERNAL_ROOT")
    if override:
        return Path(override).expanduser().resolve()
    base = Path.home()/"Documents"/"Codex"
    if sys.platform == "win32":
        base = base/"codex资料"
    return base/"项目"/"个人Unicode音型输入法"

def shape_dependency_dir():
    external = external_root()/"tools"/"shape-dependencies"
    legacy = PROJECT/"工具"/".形状实验依赖"
    return external if external.is_dir() or not legacy.is_dir() else legacy

def font_work_dir():
    external = external_root()/"cache"/"font-sources"/"editor-fonts"
    legacy = PROJECT/"工具"/"work"/"editor-fonts"
    return external if external.is_dir() or not legacy.is_dir() else legacy


def vault_root():
    import json
    override = os.environ.get("OBSIDIAN_VAULT_ROOT")
    if override:
        return Path(override).expanduser().resolve()
    location = PROJECT/"vault-location.json"
    if location.is_file():
        return Path(json.loads(location.read_text("utf-8"))["vaultRoot"])
    return PROJECT.parents[1]
