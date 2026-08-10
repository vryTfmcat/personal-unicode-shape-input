#!/usr/bin/env python3
"""Serve the local Unicode key editor and open it in the default browser."""

from __future__ import annotations

import functools
import http.server
import threading
import webbrowser
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def main() -> None:
    # Keep a fixed origin so browser localStorage remains available every time.
    port = 8765
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(ROOT))
    try:
        server = http.server.ThreadingHTTPServer(("127.0.0.1", port), handler)
    except OSError as error:
        raise SystemExit("本地端口 8765 已被占用；请先关闭之前的编辑器命令窗口。") from error
    url = f"http://127.0.0.1:{port}/"
    print(f"Unicode 音型键位编辑器：{url}")
    print("关闭这个窗口即可停止本地服务。")
    threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
