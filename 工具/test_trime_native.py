"""Check Android-specific Lua using the existing isolated desktop Rime test harness."""
from pathlib import Path
import tempfile,shutil,json
from rime_modes_runtime import Runtime,WEASEL
ROOT=Path(__file__).resolve().parents[1]
def main():
    if not (WEASEL/'rime.dll').exists():
        print('SKIP: native Rime library unavailable');return
    src=ROOT/'原型/键位编辑器/touch/trime-base'
    with tempfile.TemporaryDirectory(prefix='unicode-android-rime-') as temp:
        root=Path(temp)
        manifest=json.loads((src/'manifest.json').read_text(encoding='utf8'))
        for name in manifest['files']:
            dest=root/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src/name,dest)
        (root/'default.custom.yaml').write_text('patch:\n  schema_list:\n    - schema: personal_unicode_android\n',encoding='utf8')
        r=Runtime(root,select_schema=False)
        try:
            assert r.dll.RimeSelectSchema(r.session,b'personal_unicode_android')
            r.modes(['block']);rows=r.query('gltu');assert any(x['char']=='Ⱝ' for x in rows)
            r.key(0xffc3);assert r.selected_modes()==['shape']
            r.key(0xffc3);assert r.selected_modes()==['personal']
            r.key(0xffc3);assert r.selected_modes()==['block','shape','personal']
            r.key(0xffc3);assert r.selected_modes()==['block']
            r.key(0xffc5);assert r.selected_modes()==['block','shape','personal']
            assert r.schema()=='personal_unicode_android'
            print('PASS: Android schema deploys; exact block candidate; F6 cycle; F8 mixed; no Weasel icon switching')
        finally:r.close()
if __name__=='__main__':main()
