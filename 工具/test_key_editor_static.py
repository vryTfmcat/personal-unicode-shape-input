#!/usr/bin/env python3
"""Smoke-test the local static editor without opening a browser."""

from __future__ import annotations

import functools
import http.server
import json
import threading
import urllib.request
from pathlib import Path

from build_key_editor_data import build


ROOT = Path(__file__).resolve().parents[1] / "原型" / "键位编辑器"


def main() -> None:
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(ROOT))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        base = f"http://127.0.0.1:{server.server_port}"
        for relative in ("index.html", "styles.css", "app.js", "association.js", "data/initial-data.json"):
            with urllib.request.urlopen(f"{base}/{relative}", timeout=5) as response:
                assert response.status == 200
                assert response.read()
        disk = json.loads((ROOT / "data" / "initial-data.json").read_text(encoding="utf-8"))
        assert disk == build()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
    print("键位编辑器静态服务校验通过。")


if __name__ == "__main__":
    main()
