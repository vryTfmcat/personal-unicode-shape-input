#!/usr/bin/env python3
"""Serve the local editor and persist its association graph safely."""

from __future__ import annotations

import functools
import hashlib
import http.server
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import webbrowser
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parents[1]
TOOLS = PROJECT / "工具"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))
from sync_association_entities import sync as sync_association_entities  # noqa: E402
from mode_codebooks import BOOK_PATH, BASE_PATH, validate_codebooks, write as build_modes  # noqa: E402
GRAPH_PATH = PROJECT / "数据" / "联想图谱" / "association-graph.json"
BACKUP_DIR = PROJECT / "数据" / "联想图谱" / "备份"
LETTERS = "abcdefghijklmnopqrstuvwxyz"
MAX_BODY = 10 * 1024 * 1024
BACKUP_LIMIT = 50
BACKUP_INTERVAL = 600
INITIAL_DATA = ROOT / "data" / "initial-data.json"
ALL_KEYMAP = PROJECT / "数据" / "Unicode全码表" / "unicode-17-全字符编码.tsv"


def ensure_initial_data() -> None:
    """Rebuild ignored editor artifacts after a fresh clone or project move."""
    if not BASE_PATH.is_file() or not BOOK_PATH.is_file():
        build_modes()
    if INITIAL_DATA.is_file() and INITIAL_DATA.stat().st_size > 1_000_000:
        return
    print("检测到编辑器初始数据缺失，正在自动重建（首次约需一分钟）……", flush=True)
    scripts: list[Path] = []
    if not ALL_KEYMAP.is_file():
        scripts.append(TOOLS / "build_all_unicode_keymap.py")
    scripts.append(TOOLS / "build_key_editor_data.py")
    try:
        for script in scripts:
            subprocess.run([sys.executable, str(script)], cwd=PROJECT, check=True)
    except (OSError, subprocess.CalledProcessError) as error:
        raise SystemExit(
            "无法自动重建编辑器数据。请保留此窗口并安装 NumPy 与 Pillow，"
            "或在项目目录运行：python 工具/project_tasks.py build"
        ) from error
    if not INITIAL_DATA.is_file():
        raise SystemExit("初始数据重建完成但文件仍不存在，请检查磁盘空间和项目写入权限。")


class GraphValidationError(ValueError):
    pass


def canonical_bytes(graph: dict[str, Any]) -> bytes:
    return (json.dumps(graph, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def revision_for(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def validate_graph(graph: Any) -> dict[str, Any]:
    if not isinstance(graph, dict) or graph.get("version") != 1:
        raise GraphValidationError("图谱必须是 version 1 对象")
    required_lists = ("letters", "pairs", "characters", "concepts", "themes", "edges", "rimeAliases")
    if any(not isinstance(graph.get(key), list) for key in required_lists):
        raise GraphValidationError("图谱缺少必要列表")
    letter_keys = {item.get("key") for item in graph["letters"] if isinstance(item, dict)}
    if letter_keys != set(LETTERS) or len(graph["letters"]) != 26:
        raise GraphValidationError("字母节点必须恰好包含 a-z")
    pair_codes = {item.get("code") for item in graph["pairs"] if isinstance(item, dict)}
    expected_pairs = {a + b for a in LETTERS for b in LETTERS}
    if pair_codes != expected_pairs or len(graph["pairs"]) != 676:
        raise GraphValidationError("双字母节点必须恰好包含 676 个组合")

    node_ids = {f"letter-{key}" for key in LETTERS} | {f"pair-{code}" for code in pair_codes}
    for collection in ("characters", "concepts", "themes"):
        for item in graph[collection]:
            if not isinstance(item, dict) or not isinstance(item.get("id"), str):
                raise GraphValidationError(f"{collection} 存在无效节点")
            if item["id"] in node_ids:
                raise GraphValidationError(f"节点 ID 重复：{item['id']}")
            node_ids.add(item["id"])
    edge_ids: set[str] = set()
    for edge in graph["edges"]:
        if not isinstance(edge, dict) or not isinstance(edge.get("id"), str):
            raise GraphValidationError("关系缺少 ID")
        if edge["id"] in edge_ids:
            raise GraphValidationError(f"关系 ID 重复：{edge['id']}")
        edge_ids.add(edge["id"])
        if edge.get("source") not in node_ids or edge.get("target") not in node_ids:
            raise GraphValidationError(f"关系指向不存在节点：{edge['id']}")

    character_ids = {item["id"] for item in graph["characters"]}
    for alias in graph["rimeAliases"]:
        if not isinstance(alias, dict) or alias.get("characterId") not in character_ids:
            raise GraphValidationError("Rime 别名指向不存在字符")
        prefix = alias.get("prefix", "")
        suffix = alias.get("suffix", "")
        if not re.fullmatch(r"[a-z]{2}", prefix) or prefix not in pair_codes:
            raise GraphValidationError("Rime 别名前缀必须是已定义双字母")
        if not re.fullmatch(r"[a-z]{2}", suffix):
            raise GraphValidationError("Rime 别名后缀必须是两个小写字母")
        if not isinstance(alias.get("enabled", False), bool):
            raise GraphValidationError("Rime 别名 enabled 必须为布尔值")
    if not isinstance(graph.get("views"), dict) or not isinstance(graph.get("metadata"), dict):
        raise GraphValidationError("图谱缺少视图或元数据")
    return graph


class GraphStore:
    def __init__(self, path: Path = GRAPH_PATH, backup_dir: Path = BACKUP_DIR, entity_project: Path | None = None, validator=validate_graph) -> None:
        self.path = path
        self.backup_dir = backup_dir
        self.lock = threading.RLock()
        self.last_backup = 0.0
        self.entity_project = entity_project
        self.validator = validator

    def read(self) -> tuple[dict[str, Any], str]:
        with self.lock:
            data = self.path.read_bytes()
            graph = self.validator(json.loads(data.decode("utf-8-sig")))
            return graph, revision_for(canonical_bytes(graph))

    def snapshot(self, force: bool = True) -> str | None:
        with self.lock:
            if not self.path.exists():
                return None
            now = time.time()
            if not force and self.last_backup and now - self.last_backup < BACKUP_INTERVAL:
                return None
            self.backup_dir.mkdir(parents=True, exist_ok=True)
            stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
            target = self.backup_dir / f"{self.path.stem}.{stamp}.json"
            counter = 1
            while target.exists():
                target = self.backup_dir / f"{self.path.stem}.{stamp}-{counter:02d}.json"
                counter += 1
            shutil.copy2(self.path, target)
            self.last_backup = now
            backups = sorted(self.backup_dir.glob(f"{self.path.stem}.*.json"), key=lambda item: item.name)
            for old in backups[:-BACKUP_LIMIT]:
                old.unlink()
            return target.name

    def write(self, graph: Any, base_revision: str) -> str:
        with self.lock:
            current_graph, current_revision = self.read()
            if base_revision != current_revision:
                raise RuntimeError("revision-conflict")
            validated = self.validator(graph)
            if validated == current_graph:
                return current_revision
            self.snapshot(force=False)
            validated["updatedAt"] = datetime.now().astimezone().isoformat(timespec="seconds")
            data = canonical_bytes(validated)
            self.path.parent.mkdir(parents=True, exist_ok=True)
            descriptor, temp_name = tempfile.mkstemp(prefix="association-graph.", suffix=".tmp", dir=self.path.parent)
            try:
                with os.fdopen(descriptor, "wb") as handle:
                    handle.write(data)
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(temp_name, self.path)
            finally:
                if os.path.exists(temp_name):
                    os.unlink(temp_name)
            if self.entity_project is not None:
                sync_association_entities(validated, self.entity_project)
            return revision_for(data)


class CodebookStore(GraphStore):
    def __init__(self, path: Path = BOOK_PATH, backup_dir: Path | None = None, validator=validate_codebooks):
        super().__init__(path, backup_dir or path.parent / "备份", validator=validator)


    def write(self, data, base_revision):
        if not isinstance(data, dict): raise ValueError("码本必须是对象")
        with self.lock:
            current, _ = self.read()
            for identity, value in current.get("shapeOverrides", {}).items():
                if value.get("paths") and "paths" not in data.get("shapeOverrides", {}).get(identity, {}):
                    raise ValueError("新版本细分路径不能被旧编辑器或旧码本静默删除；请导出草稿并刷新")
            return super().write(data, base_revision)


def handler_factory(store: GraphStore, directory: Path = ROOT, codebook_store: CodebookStore | None = None, publisher=None):
    books = codebook_store or CodebookStore()
    class EditorHandler(http.server.SimpleHTTPRequestHandler):
        def end_headers(self) -> None:
            # Revalidate static files so HTML and scripts stay in sync after edits.
            if not self.path.startswith("/api/"):
                self.send_header("Cache-Control", "no-cache")
            super().end_headers()

        def _json(self, status: int, payload: dict[str, Any]) -> None:
            data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)

        def _body(self) -> dict[str, Any]:
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError as error:
                raise GraphValidationError("Content-Length 无效") from error
            if length <= 0 or length > MAX_BODY:
                raise GraphValidationError("请求正文大小不合法")
            try:
                value = json.loads(self.rfile.read(length).decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as error:
                raise GraphValidationError("请求不是有效 JSON") from error
            if not isinstance(value, dict):
                raise GraphValidationError("请求必须是 JSON 对象")
            return value

        def do_GET(self) -> None:  # noqa: N802
            if self.path.startswith('/api/shape-overview/'):
                from shape_overview import handle
                handle(self)
                return
            if self.path == "/api/codebooks/source-check":
                try:
                    from check_flypy_source import check
                    self._json(200, check())
                except (OSError, ValueError) as error:
                    self._json(502, {"error": str(error)})
                return
            if self.path == "/api/codebooks":
                try:
                    codebooks, revision = books.read()
                    self._json(200, {"revision": revision, "codebooks": codebooks})
                except (OSError, ValueError) as error:
                    self._json(500, {"error": str(error)})
                return
            if self.path == "/api/association-graph":
                try:
                    graph, revision = store.read()
                    self._json(200, {"revision": revision, "graph": graph})
                except (OSError, ValueError, GraphValidationError) as error:
                    self._json(500, {"error": str(error)})
                return
            super().do_GET()

        def do_PUT(self) -> None:  # noqa: N802
            if self.path == "/api/codebooks":
                try:
                    body = self._body()
                    revision = books.write(body.get("codebooks"), str(body.get("baseRevision", "")))
                    self._json(200, {"revision": revision})
                except RuntimeError as error:
                    _, revision = books.read()
                    self._json(409, {"error": str(error), "revision": revision})
                except ValueError as error:
                    self._json(400, {"error": str(error)})
                except OSError as error:
                    self._json(500, {"error": str(error)})
                return
            if self.path != "/api/association-graph":
                self._json(404, {"error": "not-found"})
                return
            try:
                body = self._body()
                revision = store.write(body.get("graph"), str(body.get("baseRevision", "")))
                self._json(200, {"revision": revision})
            except RuntimeError as error:
                if str(error) == "revision-conflict":
                    _, revision = store.read()
                    self._json(409, {"error": "revision-conflict", "revision": revision})
                else:
                    self._json(500, {"error": str(error)})
            except (ValueError, GraphValidationError) as error:
                self._json(400, {"error": str(error)})
            except OSError as error:
                self._json(500, {"error": str(error)})

        def do_POST(self) -> None:  # noqa: N802
            if self.path == '/api/pictorial-review/save':
                if (self.headers.get('Origin') != f"http://{self.headers.get('Host')}"
                        or self.headers.get('Content-Type', '').split(';')[0] != 'application/json'):
                    self._json(403, {'error': '只允许同源审核页面保存JSON'})
                    return
                try:
                    from save_shape_pictorial_review import save_snapshot
                    self._json(200, save_snapshot(self._body()))
                except (ValueError, GraphValidationError) as error:
                    self._json(400, {'error': str(error)})
                except OSError as error:
                    self._json(500, {'error': str(error)})
                return
            if self.path == "/api/codebooks/snapshot":
                self._json(200, {"snapshot": books.snapshot(force=True)})
                return
            if self.path == "/api/codebooks/publish":
                if publisher is None:
                    self._json(503, {"error": "此服务未配置小狼毫发布"})
                    return
                try:
                    body = self._body()
                    with books.lock:
                        codebooks, revision = books.read()
                        if body.get("baseRevision") != revision:
                            self._json(409, {"error": "revision-conflict", "revision": revision})
                            return
                        result = publisher(codebooks)
                    self._json(200, result)
                except (ValueError, OSError, RuntimeError) as error:
                    self._json(500, {"error": str(error)})
                return
            if self.path != "/api/association-graph/snapshot":
                self._json(404, {"error": "not-found"})
                return
            try:
                name = store.snapshot(force=True)
                _, revision = store.read()
                self._json(200, {"snapshot": name, "revision": revision})
            except OSError as error:
                self._json(500, {"error": str(error)})

    return functools.partial(EditorHandler, directory=str(directory))


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()
    ensure_initial_data()
    port = args.port
    store = GraphStore(entity_project=PROJECT)
    from publish_mode_rime import publish
    handler = handler_factory(store, publisher=functools.partial(publish,native_core=os.name=='nt'))
    try:
        server = http.server.ThreadingHTTPServer(("127.0.0.1", port), handler)
    except OSError as error:
        raise SystemExit(f"本地端口 {port} 已被占用；请先关闭之前的编辑器命令窗口。") from error
    url = f"http://127.0.0.1:{port}/"
    print(f"Unicode 三模式编辑器：{url}")
    print("码本与图谱自动保存到项目；小狼毫在点击发布后同步。关闭窗口即可停止服务。")
    if not args.no_browser:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
