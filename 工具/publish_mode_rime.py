"""Build, verify, back up and deploy the independent Unicode scheme on Weasel."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import threading
from datetime import datetime
from pathlib import Path
import yaml
from build_mode_rime import build, OUTPUT
from mode_icons import schema_id
from mode_codebooks import PROJECT, BOOK_PATH, atomic_json, validate_codebooks
from rime_modes_runtime import verify

PUBLISH_LOCK = threading.Lock()


def installation() -> tuple[Path, Path]:
    import winreg
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Rime\Weasel") as key:
        user = Path(winreg.QueryValueEx(key,"RimeUserDir")[0])
    with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Rime\Weasel") as key:
        root = Path(winreg.QueryValueEx(key,"WeaselRoot")[0])
    return user.resolve(), root.resolve()


def merged_default(raw: str) -> str:
    config = yaml.safe_load(raw) or {}
    if not isinstance(config, dict): raise ValueError("default.custom.yaml 不是配置对象")
    patch = config.setdefault("patch", {})
    if not isinstance(patch, dict): raise ValueError("default.custom.yaml 的 patch 格式异常")
    schemas = patch.setdefault("schema_list/+", [])
    if not isinstance(schemas, list): raise ValueError("schema_list/+ 应为列表")
    # Register display variants so Weasel restores the last icon at startup.
    for mask in (1, 2, 4, 7, 3, 5, 6, 0):
        name = schema_id(mask)
        if not any(isinstance(x,dict) and x.get("schema")==name for x in schemas):
            schemas.append({"schema":name})
    options=patch.setdefault("switcher/save_options/+", [])
    if not isinstance(options,list): raise ValueError("switcher/save_options/+ 应为列表")
    for key in ("unicode_block","unicode_shape","unicode_personal","unicode_chinese","unicode_extended"):
        if key not in options: options.append(key)
    return yaml.safe_dump(config,allow_unicode=True,sort_keys=False)


def atomic_copy(source: Path, target: Path):
    target.parent.mkdir(parents=True,exist_ok=True)
    fd,name=tempfile.mkstemp(prefix=target.name+".",suffix=".tmp",dir=target.parent);os.close(fd)
    try:shutil.copy2(source,name);os.replace(name,target)
    finally:
        if os.path.exists(name):os.unlink(name)


def deploy(root: Path):
    startup=subprocess.STARTUPINFO();startup.dwFlags|=subprocess.STARTF_USESHOWWINDOW;startup.wShowWindow=0
    result=subprocess.run([str(root/"WeaselDeployer.exe"),"/deploy"],startupinfo=startup,
                          creationflags=subprocess.CREATE_NO_WINDOW,timeout=60,check=False)
    if result.returncode:raise RuntimeError(f"小狼毫重新部署返回 {result.returncode}")


def deploy_core(root: Path, target: Path):
    """Documented Weasel 0.17.4 fallback, with frontend lifecycle restored."""
    import sys
    installed_user,installed_root=installation()
    if root.resolve()!=installed_root or target.resolve()!=installed_user:
        raise ValueError('Native frontend restart is limited to the detected Weasel installation')
    startup=subprocess.STARTUPINFO();startup.dwFlags|=subprocess.STARTF_USESHOWWINDOW;startup.wShowWindow=0
    options=dict(startupinfo=startup,creationflags=subprocess.CREATE_NO_WINDOW)
    status=subprocess.run(['tasklist','/FI','IMAGENAME eq WeaselServer.exe','/FO','CSV','/NH'],capture_output=True,**options)
    running=b'WeaselServer.exe' in status.stdout
    if running:subprocess.run(['taskkill','/IM','WeaselServer.exe','/F'],capture_output=True,check=True,**options)
    try:
        subprocess.run([sys.executable,'-X','utf8',str(PROJECT/'工具/deploy_rime_core.py'),
                        '--rime-dll',str(root/'rime.dll'),'--shared-data-dir',str(root/'data'),
                        '--user-data-dir',str(target)],check=True,timeout=300,**options)
    finally:
        if running:subprocess.Popen([str(root/'WeaselServer.exe')],stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,**options)


def publish(book: dict, target: Path | None = None, weasel: Path | None = None, native_core=False) -> dict:
    if not PUBLISH_LOCK.acquire(blocking=False):raise RuntimeError("已有发布正在进行")
    release_stage = None
    try:
        validate_codebooks(book)
        if target is None or weasel is None:target,weasel=installation()
        release_stage=tempfile.TemporaryDirectory(prefix="unicode-modes-release-")
        release_output=Path(release_stage.name)/"rime"
        build_result=build(book,release_output)
        isolated=verify(release_output,book,weasel)
        old_default=target/"default.custom.yaml"
        updated_default=merged_default(old_default.read_text(encoding="utf-8-sig") if old_default.exists() else "")
        backup=PROJECT/"原型"/"rime"/"备份"/("unicode-modes-"+datetime.now().strftime("%Y%m%d-%H%M%S-%f"))
        backup.mkdir(parents=True)
        with tempfile.TemporaryDirectory(prefix="unicode-modes-publish-") as temp:
            staged=Path(temp);(staged/"default.custom.yaml").write_text(updated_default,encoding="utf-8")
            files={p.relative_to(release_output):p for p in release_output.rglob("*") if p.is_file()}
            files[Path("default.custom.yaml")]=staged/"default.custom.yaml"
            existed=[];new=[]
            for relative in files:
                destination=target/relative
                if destination.exists():
                    saved=backup/relative;saved.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(destination,saved);existed.append(relative.as_posix())
                else:new.append(relative.as_posix())
            manifest={"target":str(target),"schema":"personal_unicode_modes","backedUp":existed,"newFiles":new,
                      "isolatedVerification":isolated,"weaselRedeployed":False,'shapeReviewProfile':build_result.get('shapeReviewProfile')}
            atomic_json(backup/"codebooks-published.json",book);atomic_json(backup/"manifest.json",manifest)
            try:
                for relative,source in files.items():atomic_copy(source,target/relative)
                if native_core:deploy_core(weasel,target)
                else:deploy(weasel)
                actual=verify(release_output,book,weasel,deployed=target)
                hashes={relative.as_posix():hashlib.sha256((target/relative).read_bytes()).hexdigest() for relative in files}
                assert all(hashlib.sha256(source.read_bytes()).hexdigest()==hashes[relative.as_posix()] for relative,source in files.items())
                manifest.update(weaselRedeployed=True,deploymentMethod='rime.dll' if native_core else 'WeaselDeployer',deployedVerification=actual,sha256=hashes,counts=build_result["counts"])
                atomic_json(backup/"manifest.json",manifest)
            except Exception as error:
                for relative in existed:atomic_copy(backup/relative,target/relative)
                # Only exact files created by this transaction, within verified Rime directory.
                for relative in new:
                    destination=(target/relative).resolve()
                    if destination.is_relative_to(target.resolve()) and destination.is_file():destination.unlink()
                try:
                    if native_core:deploy_core(weasel,target)
                    else:deploy(weasel)
                except Exception as rollback_error:manifest["rollbackError"]=str(rollback_error)
                manifest["error"]=str(error);manifest["rolledBack"]=True;atomic_json(backup/"manifest.json",manifest)
                raise RuntimeError(f"发布失败，已恢复旧源文件；备份 {backup}：{error}") from error
        return {"backup":str(backup),"schema":"personal_unicode_modes","verification":actual,"counts":build_result["counts"],'shapeReviewProfile':build_result.get('shapeReviewProfile')}
    finally:
        if release_stage is not None:release_stage.cleanup()
        PUBLISH_LOCK.release()


if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("--apply",action="store_true");parser.add_argument('--native-core',action='store_true');args=parser.parse_args()
    book=json.loads(BOOK_PATH.read_text(encoding="utf-8"))
    if args.apply:print(json.dumps(publish(book,native_core=args.native_core),ensure_ascii=False))
    else:
        build(book);print(json.dumps(verify(OUTPUT,book),ensure_ascii=False))
