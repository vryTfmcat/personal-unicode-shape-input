"""Isolated native Rime sessions for real candidate and keyboard verification."""
from __future__ import annotations
import ctypes as ct
import itertools
import json
import shutil
import tempfile
from pathlib import Path
from deploy_rime_core import RimeTraits, utf8
from verify_weasel_codes import Candidate, Iterator
from mode_codebooks import base_data, effective_data, candidate_index, query_candidates
from mode_icons import schema_id

WEASEL = Path("C:/Program Files/Rime/weasel-0.17.4")
MODE_OPTIONS = {"block": "unicode_block", "shape": "unicode_shape", "personal": "unicode_personal"}

class Composition(ct.Structure):
    _fields_ = [("length",ct.c_int),("cursor",ct.c_int),("start",ct.c_int),("end",ct.c_int),("preedit",ct.c_char_p)]
class Menu(ct.Structure):
    _fields_ = [("page_size",ct.c_int),("page_no",ct.c_int),("last",ct.c_int),("highlighted",ct.c_int),("count",ct.c_int),("candidates",ct.POINTER(Candidate)),("select_keys",ct.c_char_p)]
class Context(ct.Structure):
    _fields_ = [("data_size",ct.c_int),("composition",Composition),("menu",Menu),("preview",ct.c_char_p),("labels",ct.POINTER(ct.c_char_p))]
class Commit(ct.Structure):
    _fields_ = [("data_size",ct.c_int),("text",ct.c_char_p)]


class Runtime:
    def __init__(self, root: Path, weasel: Path = WEASEL, deploy=True, select_schema=True):
        self.root = root
        self.dll = ct.WinDLL(str(weasel / "rime.dll"))
        for name, args, result in (
            ("RimeSetup", [ct.POINTER(RimeTraits)], None), ("RimeInitialize", [ct.POINTER(RimeTraits)], None),
            ("RimeStartMaintenance", [ct.c_int], ct.c_int), ("RimeJoinMaintenanceThread", [], None),
            ("RimeFinalize", [], None), ("RimeCreateSession", [], ct.c_size_t),
            ("RimeDestroySession", [ct.c_size_t], ct.c_int), ("RimeSelectSchema", [ct.c_size_t, ct.c_char_p], ct.c_int),
            ("RimeGetCurrentSchema", [ct.c_size_t, ct.c_char_p, ct.c_size_t], ct.c_int),
            ("RimeSetOption", [ct.c_size_t, ct.c_char_p, ct.c_int], None), ("RimeGetOption", [ct.c_size_t, ct.c_char_p], ct.c_int),
            ("RimeClearComposition", [ct.c_size_t], None), ("RimeSetInput", [ct.c_size_t, ct.c_char_p], ct.c_int),
            ("RimeGetContext", [ct.c_size_t,ct.POINTER(Context)], ct.c_int),
            ("RimeFreeContext", [ct.POINTER(Context)], ct.c_int),
            ("RimeGetCommit", [ct.c_size_t,ct.POINTER(Commit)], ct.c_int),
            ("RimeFreeCommit", [ct.POINTER(Commit)], ct.c_int),
            ("RimeProcessKey", [ct.c_size_t, ct.c_int, ct.c_int], ct.c_int),
            ("RimeCandidateListBegin", [ct.c_size_t, ct.POINTER(Iterator)], ct.c_int),
            ("RimeCandidateListNext", [ct.POINTER(Iterator)], ct.c_int), ("RimeCandidateListEnd", [ct.POINTER(Iterator)], None),
        ):
            f = getattr(self.dll, name); f.argtypes = args; f.restype = result
        traits = RimeTraits()
        traits.data_size = ct.sizeof(RimeTraits) - ct.sizeof(ct.c_int)
        self.paths = [utf8(weasel / "data"), utf8(root), utf8(root / "build")]
        traits.shared_data_dir, traits.user_data_dir, traits.staging_dir = self.paths
        traits.app_name = b"rime.unicode_modes_verify"
        traits.min_log_level = 2; traits.log_dir = b""
        self.dll.RimeSetup(ct.byref(traits)); self.dll.RimeInitialize(ct.byref(traits))
        if deploy:
            self.dll.RimeStartMaintenance(1); self.dll.RimeJoinMaintenanceThread()
        self.session = self.dll.RimeCreateSession()
        if not self.session or (select_schema and not self.dll.RimeSelectSchema(self.session, b"personal_unicode_modes")):
            self.close(); raise RuntimeError("隔离 Rime 无法加载三模式方案")
        self.option("ascii_mode", False)

    def option(self, key, value):
        self.dll.RimeSetOption(self.session, key.encode(), int(value))

    def modes(self, modes, chinese=False, extended=False):
        for m, key in MODE_OPTIONS.items(): self.option(key, m in modes)
        self.option("unicode_chinese", chinese); self.option("unicode_extended", extended)

    def query(self, code, clear=True):
        if clear: self.dll.RimeClearComposition(self.session)
        if not self.dll.RimeSetInput(self.session, code.encode()): raise RuntimeError("无法设置测试输入")
        it = Iterator(); result = []
        if self.dll.RimeCandidateListBegin(self.session, ct.byref(it)):
            try:
                while self.dll.RimeCandidateListNext(ct.byref(it)):
                    result.append({"char": it.candidate.text.decode(), "comment": (it.candidate.comment or b"").decode()})
            finally: self.dll.RimeCandidateListEnd(ct.byref(it))
        return result

    def input(self):
        context=Context();context.data_size=ct.sizeof(Context)-ct.sizeof(ct.c_int)
        if not self.dll.RimeGetContext(self.session,ct.byref(context)): return ""
        try: return (context.composition.preedit or b"").decode()
        finally: self.dll.RimeFreeContext(ct.byref(context))
    def key(self, key, modifiers=0): return self.dll.RimeProcessKey(self.session, key, modifiers)
    def caret(self):
        context=Context();context.data_size=ct.sizeof(Context)-ct.sizeof(ct.c_int)
        assert self.dll.RimeGetContext(self.session,ct.byref(context))
        try: return context.composition.cursor
        finally: self.dll.RimeFreeContext(ct.byref(context))
    def menu(self):
        context=Context();context.data_size=ct.sizeof(Context)-ct.sizeof(ct.c_int)
        assert self.dll.RimeGetContext(self.session,ct.byref(context))
        try:
            menu=context.menu
            return menu.page_no, bool(menu.last), [menu.candidates[i].text.decode() for i in range(menu.count)]
        finally: self.dll.RimeFreeContext(ct.byref(context))
    def committed(self):
        value=Commit();value.data_size=ct.sizeof(Commit)-ct.sizeof(ct.c_int)
        if not self.dll.RimeGetCommit(self.session,ct.byref(value)):return ""
        try:return (value.text or b"").decode()
        finally:self.dll.RimeFreeCommit(ct.byref(value))
    def selected_modes(self): return [m for m,k in MODE_OPTIONS.items() if self.dll.RimeGetOption(self.session,k.encode())]
    def schema(self):
        buffer = ct.create_string_buffer(128)
        assert self.dll.RimeGetCurrentSchema(self.session, buffer, len(buffer))
        return buffer.value.decode()
    def close(self):
        if getattr(self, "session", None): self.dll.RimeDestroySession(self.session); self.session = None
        self.dll.RimeFinalize()


def default_custom(root: Path):
    variants = ''.join(f'    - schema: {schema_id(mask)}\n' for mask in (1,2,4,7,3,5,6,0))
    (root / "default.custom.yaml").write_text('patch:\n  "schema_list/+":\n'+variants+'  "switcher/save_options/+":\n    - unicode_block\n    - unicode_shape\n    - unicode_personal\n    - unicode_chinese\n    - unicode_extended\n', encoding="utf-8")


def verify_status_assets(root: Path):
    """Check the compiled schema bindings and Windows' real icon loader."""
    import yaml
    from PIL import Image
    from mode_icons import SIZES
    user = ct.WinDLL("user32", use_last_error=True)
    user.LoadImageW.argtypes = [ct.c_void_p,ct.c_wchar_p,ct.c_uint,ct.c_int,ct.c_int,ct.c_uint]
    user.LoadImageW.restype = ct.c_void_p
    user.DestroyIcon.argtypes = [ct.c_void_p]
    for mask in range(8):
        config = yaml.safe_load((root/"build"/f"{schema_id(mask)}.schema.yaml").read_text(encoding="utf-8"))
        assert config["show_notifications"] is False, "图标模式不能显示临时提示框"
        for key, name in (("icon",str(mask)),("ascii_icon","ascii")):
            assert config["schema"][key] == f"icons/unicode_mode_{name}.ico"
            path = root/config["schema"][key]
            with Image.open(path) as im:
                assert im.ico.sizes() == {(s,s) for s in SIZES}, (path,im.ico.sizes())
            for size in (16,20,24,32,48):
                handle = user.LoadImageW(None,str(path),1,size,size,0x10)
                assert handle, ("Windows 无法载入图标",path,size,ct.get_last_error())
                user.DestroyIcon(handle)


def verify(output: Path, book: dict, weasel: Path = WEASEL, deployed: Path | None = None) -> dict:
    data = effective_data(base_data(), book); index = candidate_index(data)
    by_char = {c["char"]: c for c in data["characters"]}
    codes = [by_char[c]["blockCode"]["code"] for c in ("○", "᳀", "᳁", "᳂")]
    codes += ["oe", "oexx", "lkvv", "aakk", "zzzz"]
    reviewing=bool(data.get('shapeReviewProfile'))
    if reviewing:
        for length in (1,2,3,4):
            choices=[k for k in index['shape'] if len(k)==length]
            codes += sorted(choices,key=lambda k:(len(index['shape'][k]),k))[:2]
    codes += list(index["personal"])[:4]
    with tempfile.TemporaryDirectory(prefix="unicode-modes-native-") as temp:
        root = Path(temp)
        for source in output.rglob("*"):
            if source.is_file():
                target = root / source.relative_to(output); target.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(source, target)
        default_custom(root)
        if deployed:
            (root / "build").mkdir(exist_ok=True)
            for source in (deployed / "build").glob("*"):
                if source.is_file() and (source.name.startswith(("unicode_", "personal_unicode_modes")) or source.name == "default.yaml"):
                    shutil.copy2(source, root / "build" / source.name)
        runtime = Runtime(root, weasel, deploy=deployed is None)
        checked = 0;collection_checks={}
        try:
            verify_status_assets(root)
            if reviewing:
                import yaml
                config=yaml.safe_load((root/'build/personal_unicode_modes.schema.yaml').read_text(encoding='utf-8'))
                assert config['unicode_shape']['review_id']==data['shapeReviewProfile']['experimentId'],'Compiled review version mismatch'
            for n in (1, 2, 3):
                for combo in itertools.combinations(MODE_OPTIONS, n):
                    for chinese, extended in ((False,False),(False,True),(True,False),(True,True)):
                        runtime.modes(combo, chinese, extended)
                        mask = sum({"block":1,"shape":2,"personal":4}[m] for m in combo)
                        assert runtime.schema() == schema_id(mask), ("模式图标方案未同步", combo, runtime.schema())
                        for code in dict.fromkeys(codes):
                            expected = query_candidates(index, code, list(combo), chinese, extended)
                            actual = runtime.query(code)
                            assert [x["char"] for x in actual] == [x["char"] for x in expected], (combo,chinese,extended,code,actual[:10],expected[:10])
                            for actual_row, expected_row in zip(actual, expected):
                                labels={"block":"区块","personal":"收藏","shape":"全形","chinese":"中文","extended":"中文扩展"}
                                assert actual_row["comment"] == "+".join(labels[s] for s in expected_row["sources"])
                            checked += 1
            runtime.modes(["shape"])
            if reviewing:
                for collection in 'xyz':
                    actual=runtime.query(collection)
                    assert [r['char'] for r in actual]==[r['char'] for r in index['shape'][collection]],('Collection candidates truncated/reordered',collection,len(actual),len(index['shape'][collection]))
                    collection_checks[collection]=len(actual)
            page_code='oe'
            if reviewing:
                page_code=next(k for k in sorted(index['shape']) if 10<len(index['shape'][k])<=40)
            round_rows = runtime.query(page_code);shape_count = len(round_rows); assert shape_count > 10
            paged=[];page=0
            while True:
                actual_page,last,chars=runtime.menu();assert actual_page==page
                paged.extend(chars)
                if last:break
                runtime.key(0xff56);page+=1
                assert page <= shape_count
            assert paged==[r["char"] for r in round_rows], "完整翻页候选不一致"
            runtime.key(ord("1"));assert runtime.committed()==paged[-len(chars)], "数字选字失败"
            runtime.modes(["block"]);runtime.query(codes[0]);runtime.key(32)
            assert runtime.committed()=="○", "空格选字失败"
            runtime.modes(["shape"])
            assert not runtime.query("zzzz" if reviewing else "oexx")
            runtime.modes(["block"]); runtime.query(codes[0]); original = runtime.input()
            for expected in (["shape"],["personal"],["block","shape","personal"],["block"]):
                runtime.key(0xffe1,1); runtime.key(0xffe1,1<<30)
                assert runtime.selected_modes() == expected, ("left shift",runtime.selected_modes(),expected)
                assert runtime.schema() == schema_id(sum({"block":1,"shape":2,"personal":4}[m] for m in expected))
                assert runtime.input() == original, ("lost composition", runtime.input())
                assert not runtime.committed(), "切图标不应提交字符"
            runtime.key(0xffe1,1); runtime.key(ord("A"),1); runtime.key(0xffe1,1<<30)
            assert runtime.selected_modes() == ["block"], "大写组合误切模式"
            runtime.key(0xffe1,1); runtime.key(0xffe1,1); runtime.key(0xffe1,1<<30)
            assert runtime.selected_modes() == ["shape"], "长按应只切换一次"
            runtime.dll.RimeClearComposition(runtime.session)
            runtime.key(0xffe2,1); runtime.key(0xffe2,1<<30)
            assert runtime.dll.RimeGetOption(runtime.session,b"ascii_mode"), "右 Shift 未切中英文"
            runtime.modes(["shape","personal"], True, True)
            assert runtime.dll.RimeGetOption(runtime.session,b"ascii_mode"), "切模式不应退出英文"
            runtime.modes([])
            assert runtime.schema() == schema_id(0), "全关图标未同步"
            runtime.modes(["shape","personal"], True, True)
            runtime.committed()  # Drain the earlier right-Shift commit_text result.
            runtime.query("oe")
            runtime.option("ascii_mode",False)
            runtime.key(0xff51)
            caret=runtime.caret(); assert caret == 1, ("测试未移动输入光标",caret)
            runtime.option("unicode_block",True)
            assert runtime.caret()==caret, "切图标丢失光标位置"
            assert not runtime.committed(), "光标中途切换意外上屏"
            runtime.option("unicode_block",False)
        finally: runtime.close()
        runtime = Runtime(root, weasel, deploy=False, select_schema=False)
        try:
            assert runtime.selected_modes() == ["shape","personal"], "重启未恢复模式"
            assert runtime.dll.RimeGetOption(runtime.session,b"unicode_chinese"), "重启未恢复中文开关"
            assert runtime.dll.RimeGetOption(runtime.session,b"unicode_extended"), "重启未恢复扩展开关"
            assert runtime.schema() == schema_id(6), "启动未恢复最后的模式图标"
        finally: runtime.close()
        return {"candidateChecks": checked, "modeCombinations": 7, "shapeRoundCandidates": shape_count,
                "shiftVerified": True, "preferencesVerified": True, "pagingVerified": True,
                "selectionVerified": True, "statusIconsVerified": True, "deployedTables": deployed is not None,
                'fullCollectionChecks':collection_checks,
                'shapeReviewExperimentId':data.get('shapeReviewProfile',{}).get('experimentId')}


if __name__ == "__main__":
    import argparse
    from build_mode_rime import OUTPUT
    from mode_codebooks import BOOK_PATH
    p=argparse.ArgumentParser();p.add_argument("--deployed",type=Path);args=p.parse_args()
    book=json.loads(BOOK_PATH.read_text(encoding="utf-8"))
    print(json.dumps(verify(OUTPUT,book,deployed=args.deployed),ensure_ascii=False))
