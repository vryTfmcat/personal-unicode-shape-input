#!/usr/bin/env python3
"""Exercise the editor's local graph persistence API."""

from __future__ import annotations

import importlib.util
import json
import tempfile
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[1]
SERVER_PATH = PROJECT / "原型" / "键位编辑器" / "serve.py"
GRAPH_PATH = PROJECT / "数据" / "联想图谱" / "association-graph.json"


def load_server_module():
    spec = importlib.util.spec_from_file_location("key_editor_server", SERVER_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def request(url: str, method: str = "GET", payload=None):
    data = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=data, method=method, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read().decode("utf-8"))


def main() -> None:
    module = load_server_module()
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        graph_path = root / "association-graph.json"
        graph_path.write_bytes(GRAPH_PATH.read_bytes())
        store = module.GraphStore(graph_path, root / "backups")
        server = ThreadingHTTPServer(("127.0.0.1", 0), module.handler_factory(store, PROJECT / "原型" / "键位编辑器"))
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f"http://127.0.0.1:{server.server_address[1]}"
        try:
            status, loaded = request(base + "/api/association-graph")
            assert status == 200
            revision = loaded["revision"]
            graph = loaded["graph"]
            graph["letters"][0]["note"] = "测试保存"
            status, saved = request(base + "/api/association-graph", "PUT", {"baseRevision": revision, "graph": graph})
            assert status == 200 and saved["revision"] != revision
            status, conflict = request(base + "/api/association-graph", "PUT", {"baseRevision": revision, "graph": graph})
            assert status == 409 and conflict["error"] == "revision-conflict"
            invalid = json.loads(json.dumps(graph, ensure_ascii=False))
            invalid["pairs"] = []
            status, response = request(base + "/api/association-graph", "PUT", {"baseRevision": saved["revision"], "graph": invalid})
            assert status == 400
            status, snapshot = request(base + "/api/association-graph/snapshot", "POST", {})
            assert status == 200 and snapshot["snapshot"]
            for _ in range(55):
                store.snapshot(force=True)
            assert len(list((root / "backups").glob("*.json"))) == module.BACKUP_LIMIT
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)
    print("联想图谱本地保存接口校验通过。")


if __name__ == "__main__":
    main()

