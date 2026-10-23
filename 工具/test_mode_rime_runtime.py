"""Exercise enabled personal aliases against the installed native Rime core."""
import copy
import json
import sys
import tempfile
from pathlib import Path
from mode_codebooks import BOOK_PATH, base_data
from build_mode_rime import build
from rime_modes_runtime import verify, WEASEL


def main():
    if sys.platform != "win32" or not (WEASEL/"rime.dll").is_file():
        print("本机无小狼毫核心，跳过原生 Rime 测试；数据与 API 检查仍适用。")
        return
    fixture=copy.deepcopy(json.loads(BOOK_PATH.read_text(encoding="utf-8")))
    circle=next(c for c in base_data()["characters"] if c["char"]=="○")
    fixture["personal"][circle["id"]]=[{"code":"oe","enabled":True},{"code":circle["blockCode"]["code"],"enabled":True}]
    fixture["personal"]["u-004f"]=[{"code":"oe","enabled":True}]
    fixture["personal"]["u-554a"]=[{"code":"aakk","enabled":True}]
    with tempfile.TemporaryDirectory(prefix="unicode-personal-fixture-") as temp:
        build(fixture,Path(temp))
        print(json.dumps(verify(Path(temp),fixture),ensure_ascii=False))


if __name__=="__main__":main()
