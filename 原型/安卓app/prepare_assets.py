"""Only copy the touch app, public character snapshot, KLE geometry and font assets."""
from pathlib import Path
import shutil,subprocess,sys
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
EDITOR=ROOT/'原型/键位编辑器'
subprocess.run([sys.executable,str(ROOT/'工具/build_touch_data.py')],check=True)
subprocess.run([sys.executable,str(ROOT/'工具/build_trime_bundle.py')],check=True)
DEST=HERE/'generated-assets'
for name in ['touch/preview.html','touch/.gitignore']:
    (DEST/name).unlink(missing_ok=True)
for name in ['touch','fonts']:
    src=EDITOR/name
    for p in src.rglob('*'):
        if p.is_file() and p.suffix.lower() != '.png' and (name=='fonts' or p.name not in ['preview.html','README.md','.gitignore']):
            target=DEST/name/p.relative_to(src);target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,target)
for name in ['virtual-keyboard-core.js','virtual-keyboard-layouts.js']:
    DEST.mkdir(exist_ok=True);shutil.copy2(EDITOR/name,DEST/name)
print('Android offline assets ready')
