#!/usr/bin/env python3
"""Deploy v7-A1 (35,727 BCDA/ABCD) to Windows Weasel and build Android Trime deployment packages."""
from __future__ import annotations

import ctypes
import hashlib
import json
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
V7_DIR = ROOT / "数据/三模式/规则库/四键实验/键位试验/20261029-二三位联合设计/大规模试分配/键义试验/整体重规划-20261127-v7-A1全键位基线"
V7_JSON = V7_DIR / "全形全键位基线-35727-v7-A1.json"

RIME_SRC = ROOT / "原型/rime"
PUBLISH_DIR = ROOT / "发布"
TRIME_024_ZIP = ROOT / "原型/安卓app/发布/Unicode-Trime-0.2.4.zip"

APPDATA_RIME = Path(os.environ["APPDATA"]) / "Rime"
WEASEL_ROOT = Path(r"C:\Program Files\Rime\weasel-0.17.4")
RIME_DLL = WEASEL_ROOT / "rime.dll"
SHARED_DIR = WEASEL_ROOT / "data"
DEPLOY_CORE = ROOT / "工具/deploy_rime_core.py"

FONT_FACE = (
    '"Microsoft YaHei, Segoe UI Symbol, Noto Sans Symbols2, '
    'Unifont:0:FFFF, Unifont Upper:10000:10FFFF, '
    'Essenfont BMP U17:0:FFFF, Essenfont SMP U17:10000:1FFFF, '
    'Essenfont SIP U17:20000:2FFFF, Essenfont TIP U17:30000:3FFFF"'
)

LUA_PANEL = """local compact, expanded = "unicode_shape_v7_a1", "unicode_shape_v7_a1_expanded"
return function(key, env)
  local engine = env.engine
  local ctx = engine.context
  local keycode = key.keycode
  if engine.schema.schema_id == expanded and ctx:has_menu()
      and not key:ctrl() and not key:alt() and not key:super() and not key:shift()
      and ((keycode >= 0x30 and keycode <= 0x39) or (keycode >= 0xffb0 and keycode <= 0xffb9)) then
    return 1
  end
  local letter = key.keycode == 0x45 or key.keycode == 0x65
  if not letter or not key:ctrl() or not key:shift() or key:alt() or key:super() or key:release() or not ctx:has_menu() then
    return 2
  end
  local input, caret = ctx.input, ctx.caret_pos
  local target = engine.schema.schema_id == compact and expanded or compact
  engine:apply_schema(Schema(target))
  ctx.input, ctx.caret_pos = input, caret
  return 1
end
"""


def desktop_schema(schema_id: str, name: str, dict_name: str, page_size: int = 9, expanded: bool = False, deps: list[str] | None = None, with_panel: bool = True) -> str:
    lines = [
        "schema:",
        f"  schema_id: {schema_id}",
        f"  name: {name}",
        '  version: "7.1"',
        "  icon: icons/unicode_mode_2.ico",
        "  ascii_icon: icons/unicode_mode_ascii.ico",
    ]
    if deps:
        lines.append(f"  dependencies: [{', '.join(deps)}]")
    lines += [
        "switches:",
        "  - name: ascii_mode",
        "    reset: 0",
        "    states: [形码, 西文]",
        "engine:",
        f"  processors: [{'lua_processor@*unicode_v7_panel, ' if with_panel else ''}key_binder, ascii_composer, speller, selector, navigator, express_editor]",
        "  segmentors: [ascii_segmentor, abc_segmentor, fallback_segmentor]",
        "  translators: [table_translator]",
        "speller:",
        "  alphabet: abcdefghijklmnopqrstuvwxyz",
        "  max_code_length: 4",
        "  auto_select: false",
        "translator:",
        f"  dictionary: {dict_name}",
        "  enable_completion: false",
        "  enable_sentence: false",
        "  enable_user_dict: false",
        "  enable_charset_filter: false",
        "  encode_commit_history: false",
        "menu:",
        f"  page_size: {page_size}",
    ]
    if expanded:
        lines.append("  alternative_select_labels:")
        for _ in range(page_size):
            lines.append('    - "\\u200B"')
    lines += [
        "ascii_composer:",
        "  switch_key:",
        "    Shift_L: noop",
        "    Shift_R: commit_text",
        "key_binder:",
        "  import_preset: default",
        "  bindings:",
        "",
        "style:",
        f"  font_face: {FONT_FACE}",
        '  label_format: "%s"',
        "  hover_type: semi_hilite",
        "  horizontal: true",
        "  layout:",
        "    type: horizontal",
        "    min_width: 630",
        "    max_width: 630",
        "    min_height: 100",
        "    candidate_spacing: 12",
        "  paging_on_scroll: true",
    ]
    return "\n".join(lines) + "\n"


def mobile_schema(schema_id: str, name: str, dict_name: str, page_size: int = 8) -> str:
    return "\n".join([
        "schema:",
        f"  schema_id: {schema_id}",
        f"  name: {name}",
        '  version: "7.1"',
        "switches:",
        "  - name: ascii_mode",
        "    reset: 0",
        "    states: [形码, 西文]",
        "engine:",
        "  processors: [key_binder, ascii_composer, speller, selector, navigator, express_editor]",
        "  segmentors: [ascii_segmentor, abc_segmentor, fallback_segmentor]",
        "  translators: [table_translator]",
        "speller:",
        "  alphabet: abcdefghijklmnopqrstuvwxyz",
        "  max_code_length: 4",
        "  auto_select: false",
        "translator:",
        f"  dictionary: {dict_name}",
        "  enable_completion: false",
        "  enable_sentence: false",
        "  enable_user_dict: false",
        "  enable_charset_filter: false",
        "  encode_commit_history: false",
        "menu:",
        f"  page_size: {page_size}",
        "ascii_composer:",
        "  switch_key:",
        "    Shift_L: noop",
        "    Shift_R: commit_text",
        "key_binder:",
        "  import_preset: default",
        "  bindings:",
        "",
    ])


def build_dict_lines(rows: dict, order: str) -> list[str]:
    seen = set()
    entries = []
    # Sort deterministically by codepoint so candidate order inside each bucket is clean
    for cp_str in sorted(rows, key=lambda c: int(c[2:], 16)):
        r = rows[cp_str]
        ch = r["char"]
        primary = r[order].lower()
        assert len(primary) == 4 and primary.isalpha(), (cp_str, primary)
        codes = [primary[:2], primary[:3], primary]
        for d3 in r.get("secondaryPaths", []):
            d3_low = d3.lower()
            if order == "ABCD" and len(d3_low) >= 3:
                # Reorder 3-char D3 (BCD) or 4-char D3 (BCDA) symmetrically
                if len(d3_low) == 4:
                    d3_low = d3_low[3] + d3_low[:3]
                else:
                    # 3-char D3 path has no A; prefix/use as-is only in BCDA, or keep suffix search
                    d3_low = d3_low
            codes.append(d3_low)
        for c in codes:
            key = (c, ch)
            if key not in seen:
                seen.add(key)
                entries.append(f"{ch}\t{c}")
    return entries


def write_dict(path: Path, name: str, entries: list[str]) -> None:
    header = [
        "---",
        f"name: {name}",
        'version: "7.1"',
        "sort: original",
        "use_preset_vocabulary: false",
        "columns:",
        "  - text",
        "  - code",
        "...",
    ]
    path.write_text("\n".join(header + entries) + "\n", encoding="utf-8")


def update_default_custom(path: Path, schemas_to_add: list[str]) -> None:
    backup = path.with_name(path.name + ".bak-20261127")
    if path.exists() and not backup.exists():
        shutil.copy2(path, backup)
    lines = path.read_text(encoding="utf-8").splitlines()
    existing = {line.strip().split(":", 1)[1].strip() for line in lines if line.strip().startswith("- schema:")}
    insert_idx = None
    for idx, line in enumerate(lines):
        if line.strip().startswith("schema_list"):
            j = idx + 1
            while j < len(lines) and (lines[j].strip().startswith("- schema:") or not lines[j].strip()):
                if lines[j].strip().startswith("- schema:"):
                    insert_idx = j + 1
                j += 1
            break
    if insert_idx is None:
        lines.append("  schema_list/+:")
        insert_idx = len(lines)
    to_insert = [f"  - schema: {s}" for s in schemas_to_add if s not in existing]
    if to_insert:
        lines[insert_idx:insert_idx] = to_insert
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def stop_weasel() -> None:
    subprocess.run(["taskkill", "/F", "/IM", "WeaselServer.exe"], capture_output=True)
    subprocess.run(["taskkill", "/F", "/IM", "WeaselDeployer.exe"], capture_output=True)


def start_weasel() -> None:
    server = WEASEL_ROOT / "WeaselServer.exe"
    if server.exists():
        subprocess.Popen([str(server)], creationflags=0x00000008 | 0x00000200)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_rime_queries() -> dict[str, list[str]]:
    """Query compiled Rime tables directly via rime.dll without altering deployed user state permanently."""
    class RimeTraits(ctypes.Structure):
        _fields_ = [
            ("data_size", ctypes.c_int),
            ("shared_data_dir", ctypes.c_char_p),
            ("user_data_dir", ctypes.c_char_p),
            ("distribution_name", ctypes.c_char_p),
            ("distribution_code_name", ctypes.c_char_p),
            ("distribution_version", ctypes.c_char_p),
            ("app_name", ctypes.c_char_p),
            ("modules", ctypes.POINTER(ctypes.c_char_p)),
            ("min_log_level", ctypes.c_int),
            ("log_dir", ctypes.c_char_p),
            ("prebuilt_data_dir", ctypes.c_char_p),
            ("staging_dir", ctypes.c_char_p),
        ]

    class RimeCandidate(ctypes.Structure):
        _fields_ = [("text", ctypes.c_char_p), ("comment", ctypes.c_char_p), ("reserved", ctypes.c_void_p)]

    class RimeMenu(ctypes.Structure):
        _fields_ = [
            ("page_size", ctypes.c_int),
            ("page_no", ctypes.c_int),
            ("is_last_page", ctypes.c_int),
            ("highlighted_candidate_index", ctypes.c_int),
            ("num_candidates", ctypes.c_int),
            ("candidates", ctypes.POINTER(RimeCandidate)),
            ("select_keys", ctypes.c_char_p),
        ]

    class RimeComposition(ctypes.Structure):
        _fields_ = [
            ("length", ctypes.c_int),
            ("cursor_pos", ctypes.c_int),
            ("sel_start", ctypes.c_int),
            ("sel_end", ctypes.c_int),
            ("preedit", ctypes.c_char_p),
        ]

    class RimeContext(ctypes.Structure):
        _fields_ = [
            ("data_size", ctypes.c_int),
            ("composition", RimeComposition),
            ("menu", RimeMenu),
            ("commit_text_preview", ctypes.c_char_p),
            ("select_labels", ctypes.POINTER(ctypes.c_char_p)),
        ]

    rime = ctypes.WinDLL(str(RIME_DLL))
    rime.RimeSetup.argtypes = [ctypes.POINTER(RimeTraits)]
    rime.RimeInitialize.argtypes = [ctypes.POINTER(RimeTraits)]
    rime.RimeCreateSession.restype = ctypes.c_size_t
    rime.RimeSelectSchema.argtypes = [ctypes.c_size_t, ctypes.c_char_p]
    rime.RimeSelectSchema.restype = ctypes.c_int
    rime.RimeSimulateKeySequence.argtypes = [ctypes.c_size_t, ctypes.c_char_p]
    rime.RimeSimulateKeySequence.restype = ctypes.c_int
    rime.RimeGetContext.argtypes = [ctypes.c_size_t, ctypes.POINTER(RimeContext)]
    rime.RimeGetContext.restype = ctypes.c_int
    rime.RimeFreeContext.argtypes = [ctypes.POINTER(RimeContext)]
    rime.RimeClearComposition.argtypes = [ctypes.c_size_t]
    rime.RimeDestroySession.argtypes = [ctypes.c_size_t]

    modules = (ctypes.c_char_p * 4)(b"core", b"dict", b"gears", None)
    shared_b = str(SHARED_DIR).encode("utf-8")
    user_b = str(APPDATA_RIME).encode("utf-8")
    traits = RimeTraits()
    traits.data_size = ctypes.sizeof(RimeTraits) - ctypes.sizeof(ctypes.c_int)
    traits.shared_data_dir = shared_b
    traits.user_data_dir = user_b
    traits.distribution_name = "小狼毫".encode("utf-8")
    traits.distribution_code_name = b"Weasel"
    traits.distribution_version = b"0.17.4"
    traits.app_name = b"rime.weasel.v7_verify"
    traits.modules = ctypes.cast(modules, ctypes.POINTER(ctypes.c_char_p))
    traits.min_log_level = 3
    traits.log_dir = b""
    traits.prebuilt_data_dir = shared_b
    traits.staging_dir = str(APPDATA_RIME / "build").encode("utf-8")

    results = {}
    rime.RimeSetup(ctypes.byref(traits))
    rime.RimeInitialize(ctypes.byref(traits))
    try:
        sid = rime.RimeCreateSession()
        tests = [
            ("unicode_shape_v7_a1", "aaya"),
            ("unicode_shape_v7_a1", "kcr"),
            ("unicode_shape_v7_a1", "pfm"),
            ("unicode_shape_v7_a1", "civ"),
            ("unicode_shape_v7_a1", "xih"),
            ("unicode_shape_v7_a1", "ldbt"),
            ("unicode_shape_v7_a1", "ldb"),
            ("unicode_shape_v7_a1_abcd", "aaay"),
            ("unicode_shape_v7_a1_abcd", "tp"),
            ("unicode_shape_v7_a1_abcd", "xa"),
        ]
        for schema_id, keys in tests:
            assert rime.RimeSelectSchema(sid, schema_id.encode("utf-8"))
            rime.RimeClearComposition(sid)
            rime.RimeSimulateKeySequence(sid, keys.encode("utf-8"))
            ctx = RimeContext()
            ctx.data_size = ctypes.sizeof(RimeContext) - ctypes.sizeof(ctypes.c_int)
            ok = rime.RimeGetContext(sid, ctypes.byref(ctx))
            cands = []
            if ok and ctx.menu.num_candidates:
                for i in range(ctx.menu.num_candidates):
                    cands.append(ctx.menu.candidates[i].text.decode("utf-8"))
            rime.RimeFreeContext(ctypes.byref(ctx))
            results[f"{schema_id}:{keys}"] = cands
        rime.RimeDestroySession(sid)
    finally:
        rime.RimeFinalize()
    return results


def main():
    data = json.loads(V7_JSON.read_text(encoding="utf-8"))
    rows = data["rows"]
    assert len(rows) == 35727

    bcda_entries = build_dict_lines(rows, "BCDA")
    abcd_entries = build_dict_lines(rows, "ABCD")
    print(f"Generated dict entries: BCDA={len(bcda_entries)}, ABCD={len(abcd_entries)}", flush=True)

    # 1. Write tracked schemas + Lua into worktree/原型/rime/
    (RIME_SRC / "lua").mkdir(parents=True, exist_ok=True)
    (RIME_SRC / "lua/unicode_v7_panel.lua").write_text(LUA_PANEL, encoding="utf-8")
    (RIME_SRC / "unicode_shape_v7_a1.schema.yaml").write_text(
        desktop_schema("unicode_shape_v7_a1", "全形 v7-A1（BCDA）", "unicode_shape_v7_a1", page_size=9, deps=["unicode_shape_v7_a1_expanded"]),
        encoding="utf-8",
    )
    (RIME_SRC / "unicode_shape_v7_a1_expanded.schema.yaml").write_text(
        desktop_schema("unicode_shape_v7_a1_expanded", "全形 v7-A1（展开）", "unicode_shape_v7_a1", page_size=100, expanded=True),
        encoding="utf-8",
    )
    (RIME_SRC / "unicode_shape_v7_a1_abcd.schema.yaml").write_text(
        desktop_schema("unicode_shape_v7_a1_abcd", "全形 v7-A1（ABCD）", "unicode_shape_v7_a1_abcd", page_size=9, with_panel=False),
        encoding="utf-8",
    )

    # 2. Deploy to Windows Weasel (%APPDATA%\Rime)
    (APPDATA_RIME / "lua").mkdir(parents=True, exist_ok=True)
    dict_bcda_path = APPDATA_RIME / "unicode_shape_v7_a1.dict.yaml"
    dict_abcd_path = APPDATA_RIME / "unicode_shape_v7_a1_abcd.dict.yaml"
    write_dict(dict_bcda_path, "unicode_shape_v7_a1", bcda_entries)
    write_dict(dict_abcd_path, "unicode_shape_v7_a1_abcd", abcd_entries)
    for fname in (
        "unicode_shape_v7_a1.schema.yaml",
        "unicode_shape_v7_a1_expanded.schema.yaml",
        "unicode_shape_v7_a1_abcd.schema.yaml",
        "lua/unicode_v7_panel.lua",
    ):
        shutil.copy2(RIME_SRC / fname, APPDATA_RIME / fname)

    update_default_custom(
        APPDATA_RIME / "default.custom.yaml",
        ["unicode_shape_v7_a1", "unicode_shape_v7_a1_expanded", "unicode_shape_v7_a1_abcd"],
    )

    stop_weasel()
    subprocess.run(
        [
            sys.executable,
            str(DEPLOY_CORE),
            "--rime-dll", str(RIME_DLL),
            "--shared-data-dir", str(SHARED_DIR),
            "--user-data-dir", str(APPDATA_RIME),
        ],
        check=True,
    )
    for stem in ("unicode_shape_v7_a1", "unicode_shape_v7_a1_expanded", "unicode_shape_v7_a1_abcd"):
        assert (APPDATA_RIME / "build" / f"{stem}.schema.yaml").exists()
    for stem in ("unicode_shape_v7_a1", "unicode_shape_v7_a1_abcd"):
        assert (APPDATA_RIME / "build" / f"{stem}.table.bin").exists()
        assert (APPDATA_RIME / "build" / f"{stem}.prism.bin").exists()

    query_results = verify_rime_queries()
    start_weasel()
    print("Weasel Rime verification queries:", flush=True)
    for k, v in query_results.items():
        print(f"  {k:32s} -> {' '.join(v)}", flush=True)
    assert "o" in query_results["unicode_shape_v7_a1:aaya"]
    assert "%" in query_results["unicode_shape_v7_a1:kcr"]
    assert "⭛" in query_results["unicode_shape_v7_a1:pfm"]
    assert "ࢡ" in query_results["unicode_shape_v7_a1:civ"]
    assert "⌲" in query_results["unicode_shape_v7_a1:xih"]
    assert "▶" in query_results["unicode_shape_v7_a1:ldb"]
    assert "o" in query_results["unicode_shape_v7_a1_abcd:aaay"]
    assert query_results["unicode_shape_v7_a1_abcd:tp"]
    assert query_results["unicode_shape_v7_a1_abcd:xa"]

    # 3. Build Android Trime packages (incremental + full with 43 fonts)
    PUBLISH_DIR.mkdir(parents=True, exist_ok=True)
    mob_bcda = mobile_schema("unicode_shape_v7_a1", "全形 v7-A1（BCDA）", "unicode_shape_v7_a1", page_size=8).encode("utf-8")
    mob_abcd = mobile_schema("unicode_shape_v7_a1_abcd", "全形 v7-A1（ABCD）", "unicode_shape_v7_a1_abcd", page_size=8).encode("utf-8")
    dict_bcda_bytes = dict_bcda_path.read_bytes()
    dict_abcd_bytes = dict_abcd_path.read_bytes()

    enable_example = (
        "patch:\n"
        "  schema_list/+:\n"
        "    - schema: unicode_shape_v7_a1\n"
        "    - schema: unicode_shape_v7_a1_abcd\n"
    ).encode("utf-8")
    trime_readme = (
        "Unicode 全形 v7-A1（35,727 全域四键首版基线）手机同文部署说明\n"
        "========================================================\n\n"
        "1. 若手机此前已部署过 0.2.4（含 43 份补缺字体），只需把【增量包】解压覆盖到同文外部目录（如 Documents/Unicode-Rime）；\n"
        "   若手机尚未配置 43 份补缺字体与主题，请使用【完整包】。\n"
        "2. 打开手机同文 -> 设置 -> 从外部存储同步 -> 部署。\n"
        "3. 在方案列表即可切换「全形 v7-A1（BCDA）」或「全形 v7-A1（ABCD）」直接输入：\n"
        "   - 几何层 29,092 字（A–S/U–W/Y 23 键）\n"
        "   - T 拟像与图标 4,366 字（BCDA 下第 4 键或 ABCD 下首键 T）\n"
        "   - X 附标 2,269 字（BCDA 下第 4 键或 ABCD 下首键 X）\n"
        "4. 若已有自定义 default.custom.yaml，请将 unicode_shape_v7_a1.enable.yaml.example 中的两行追加到 schema_list/+:。\n"
    ).encode("utf-8")

    inc_zip = PUBLISH_DIR / "Unicode-Trime-v7-A1-增量包.zip"
    with zipfile.ZipFile(inc_zip, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("unicode_shape_v7_a1.dict.yaml", dict_bcda_bytes)
        zf.writestr("unicode_shape_v7_a1_abcd.dict.yaml", dict_abcd_bytes)
        zf.writestr("unicode_shape_v7_a1.schema.yaml", mob_bcda)
        zf.writestr("unicode_shape_v7_a1_abcd.schema.yaml", mob_abcd)
        zf.writestr("unicode_shape_v7_a1.enable.yaml.example", enable_example)
        zf.writestr("README-手机部署说明.txt", trime_readme)

    full_default = (
        "patch:\n"
        "  schema_list/+:\n"
        "    - schema: personal_unicode_android\n"
        "    - schema: unicode_shape_v7_a1\n"
        "    - schema: unicode_shape_v7_a1_abcd\n"
    ).encode("utf-8")

    full_zip = PUBLISH_DIR / "Unicode-Trime-v7-A1-完整包.zip"
    with zipfile.ZipFile(TRIME_024_ZIP, "r") as zin, zipfile.ZipFile(full_zip, "w", compression=zipfile.ZIP_DEFLATED) as zout:
        skip = {
            "default.custom.yaml",
            "unicode_shape_v7_a1.dict.yaml",
            "unicode_shape_v7_a1_abcd.dict.yaml",
            "unicode_shape_v7_a1.schema.yaml",
            "unicode_shape_v7_a1_abcd.schema.yaml",
            "unicode_shape_v7_a1.enable.yaml.example",
            "README-手机部署说明.txt",
        }
        for item in zin.infolist():
            if item.filename not in skip:
                zout.writestr(item, zin.read(item.filename))
        zout.writestr("default.custom.yaml", full_default)
        zout.writestr("unicode_shape_v7_a1.dict.yaml", dict_bcda_bytes)
        zout.writestr("unicode_shape_v7_a1_abcd.dict.yaml", dict_abcd_bytes)
        zout.writestr("unicode_shape_v7_a1.schema.yaml", mob_bcda)
        zout.writestr("unicode_shape_v7_a1_abcd.schema.yaml", mob_abcd)
        zout.writestr("unicode_shape_v7_a1.enable.yaml.example", enable_example)
        zout.writestr("README-手机部署说明.txt", trime_readme)

    for zp in (inc_zip, full_zip):
        with zipfile.ZipFile(zp, "r") as zchk:
            bad = zchk.testzip()
            assert bad is None, (zp, bad)
        digest = sha256_file(zp)
        zp.with_suffix(".zip.sha256").write_text(f"{digest}  {zp.name}\n", encoding="utf-8")
        print(f"Verified ZIP {zp.name}: {zp.stat().st_size:,} bytes, sha256={digest}", flush=True)


if __name__ == "__main__":
    main()
