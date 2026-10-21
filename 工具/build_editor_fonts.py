"""Build same-origin, disjoint webfont subsets for the editor's actual characters.

Uses existing project fonts and @free-fonts/plangothic 1.0.0 (fonts only,
no package code). Source paths never appear in the public manifest.
"""
from pathlib import Path
from external_paths import font_work_dir
import argparse
import hashlib
import io
import json
import logging
import re
import shutil
from collections import defaultdict
from fontTools.ttLib import TTFont
from fontTools import subset

ROOT = Path(__file__).resolve().parents[1]
EDITOR = ROOT / '原型/键位编辑器'
OUT = EDITOR / 'fonts'
WORK = font_work_dir()
ASSETS = Path('C:/Users/86137/Documents/Codex/codex资料/字体/Obsidian Unicode')


def ranges(points):
    groups = []
    for cp in sorted(points):
        if groups and cp == groups[-1][1] + 1:
            groups[-1][1] = cp
        else:
            groups.append([cp, cp])
    return ','.join(f'U+{a:X}' + (f'-{b:X}' if b != a else '') for a, b in groups)


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--assets', type=Path, default=ASSETS)
    args = parser.parse_args()
    if not (WORK/'plangothic/fonts').is_dir():
        raise SystemExit('缺少遍黑体源分片；请按编辑器 fonts/README.md 准备 @free-fonts/plangothic 1.0.0。')
    logging.getLogger('fontTools.subset').setLevel(logging.ERROR)
    OUT.mkdir(exist_ok=True)
    data = json.loads((EDITOR/'data/mode-data.json').read_text('utf-8'))
    targets = {ord(x['char']) for x in data['characters'] if len(x['char']) == 1}
    remaining = set(targets)
    faces, records = [], []

    def register(path, points, blob, source, kind):
        digest = hashlib.sha256(blob).hexdigest()
        name = f'ue-{digest[:16]}.woff2'
        (OUT/name).write_bytes(blob)
        faces.append('@font-face{font-family:"Unicode Editor";src:url("./'+name+'") format("woff2");font-style:normal;font-weight:400;font-display:swap;unicode-range:'+ranges(points)+';}')
        records.append({'file': name, 'source': source, 'kind': kind,
                        'sha256': digest, 'bytes': len(blob), 'codepoints': sorted(points)})
        remaining.difference_update(points)

    # Native outlines first. Shared family + disjoint unicode-range declarations
    # avoids OS installation dependencies and enormous global fallback stacks.
    native = [WORK/'NotoSansGurmukhi-Regular.ttf']
    native += sorted((ROOT/'数据/三模式/规则库/字体').glob('Noto*.ttf'))
    native += sorted(WORK.glob('Noto*.ttf'))
    native += sorted(WORK.glob('Noto*.otf'))
    native += [ROOT/'数据/三模式/规则库/字体/EgyptologyExtended.ttf']
    native += [args.assets/'Gentium-Regular.ttf']
    for path in native:
        if not path.exists():
            continue
        font = TTFont(path)
        points = remaining & {cp for cp,g in (font.getBestCmap() or {}).items() if g != '.notdef'}
        if not points:
            font.close()
            continue
        font.close()
        buckets = defaultdict(set)
        for cp in points: buckets[0].add(cp)
        for selected in buckets.values():
            font = TTFont(path)
            if 'fvar' in font:
                from fontTools.varLib.instancer import instantiateVariableFont
                axes = {a.axisTag:400 if a.axisTag=='wght' else a.defaultValue for a in font['fvar'].axes}
                font = instantiateVariableFont(font,axes,inplace=True)
            options = subset.Options()
            options.recalc_timestamp = False
            sub = subset.Subsetter(options=options)
            sub.populate(unicodes=selected)
            sub.subset(font)
            # Rename subsets while preserving copyright and license fields.
            for rec in font['name'].names:
                if rec.nameID in (1,3,4,6,16): rec.string='UnicodeEditorSubset'.encode(rec.getEncoding())
            font.flavor = 'woff2'
            buffer = io.BytesIO()
            font.save(buffer)
            register(path, selected, buffer.getvalue(), path.name, 'native-outline')
            font.close()
    print('Native outlines:', len(targets)-len(remaining), flush=True)

    # Copy the already-split OFL CJK fonts without modifying their bytes.
    # Restrict declarations to their actual cmap intersection, not bucket bounds.
    for i,path in enumerate(sorted((WORK/'plangothic/fonts').glob('*.woff2'))):
        start = int(path.stem.rsplit('-',1)[1],16)
        if not any(start <= cp < start+256 for cp in remaining):
            continue
        font = TTFont(path)
        points = remaining & {cp for cp,g in (font.getBestCmap() or {}).items() if g != '.notdef'}
        if points:
            register(path, points, path.read_bytes(), path.name, 'plangothic')
        font.close()
        if i % 100 == 0:
            print('CJK chunks:', i, 'remaining:', len(remaining), flush=True)

    # Final fallback only: existing monochrome outlines, then Unifont. No Windows
    # proprietary fonts are embedded. Preserve license documents with assets.
    fallback = sorted((args.assets/'单色轮廓').glob('*V2.ttf'))
    fallback += [args.assets/'单色轮廓/ObsidianOutline-SIP.ttf', args.assets/'单色轮廓/ObsidianOutline-TIP.ttf',
                 args.assets/'unifont-17.0.04.otf', args.assets/'unifont_upper-17.0.04.otf']
    for path in fallback:
        if not path.exists(): continue
        original = TTFont(path)
        points = remaining & {cp for cp,g in (original.getBestCmap() or {}).items() if g != '.notdef'}
        original.close()
        # 1024-codepoint chunks keep large fallback fonts off the initial page.
        buckets = defaultdict(set)
        for cp in points: buckets[cp//1024].add(cp)
        for bucket, selected in sorted(buckets.items()):
            font = TTFont(path)
            options = subset.Options(); options.recalc_timestamp = False
            sub = subset.Subsetter(options=options); sub.populate(unicodes=selected); sub.subset(font)
            for nid in (1,3,4,6,16): font['name'].setName('UnicodeEditorFallback', nid, 3, 1, 0x409)
            font.flavor = 'woff2'; buffer = io.BytesIO(); font.save(buffer)
            register(path, selected, buffer.getvalue(), path.name, 'fallback-outline')
            font.close()
        print('Fallback:', path.name, 'remaining:', len(remaining), flush=True)

    css = '/* Generated by build_editor_fonts.py; do not edit. */\n'+'\n'.join(faces)+'\n'
    css += '.glyph,.inspector-glyph,.graph-node-title,.graph-node-symbol,.pair-symbol,.brand-mark{font-family:"Unicode Editor","Segoe UI Symbol",sans-serif;font-synthesis:none;}\n'
    css += '.glyph,.inspector-glyph{line-height:1.35;min-height:1.35em;overflow:visible;}\n'
    (OUT/'editor-fonts.css').write_text(css,'utf-8')
    manifest = {'targetCount':len(targets),'coveredCount':len(targets)-len(remaining),
                'missing':[f'U+{cp:04X}' for cp in sorted(remaining)],'faces':records,
                'note':'cmap coverage only; fallback glyphs may be pixel-derived. Original character data is unchanged.'}
    (OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),'utf-8')
    (OUT/'missing-codepoints.json').write_text(json.dumps(sorted(remaining)),'utf-8')
    licenses = OUT/'licenses'; licenses.mkdir(exist_ok=True)
    for path in (ROOT/'数据/三模式/规则库/字体').glob('*LICENSE*'): shutil.copy2(path,licenses/path.name)
    for path in [ROOT/'数据/三模式/规则库/字体/LICENSE-Noto.txt',args.assets/'OFL-Gentium.txt',WORK/'LICENSE-OFL.txt']:
        if path.exists(): shutil.copy2(path,licenses/path.name)
    if (WORK/'source-lock.json').exists(): shutil.copy2(WORK/'source-lock.json',OUT/'source-lock.json')
    unifont = TTFont(args.assets/'unifont-17.0.04.otf')
    copyright_text = unifont['name'].getDebugName(0) or ''
    license_note = unifont['name'].getDebugName(13) or ''
    unifont.close()
    (licenses/'Unifont-copyright.txt').write_text(copyright_text+'\n'+license_note,'utf-8')
    ofl=(ROOT/'数据/三模式/规则库/字体/LICENSE-Noto.txt').read_text('utf-8')
    (licenses/'Unifont-OFL.txt').write_text(copyright_text+'\n\n'+ofl[ofl.index('SIL OPEN FONT LICENSE'):],'utf-8')
    import zipfile
    with zipfile.ZipFile(args.assets/'license-pack.zip') as z:
        for name in ['LICENSE-SOURCES.md','LICENSE.md']:
            (licenses/('Essenfont-'+name)).write_bytes(z.read(name))
    (OUT/'README.md').write_text('# Editor webfonts\n\nGenerated for the Unicode 17 editor data. Same-origin URL sources only; no local() dependencies. Native Noto/Gentium outlines precede Plangothic and existing fallback outlines. See manifest.json for exact coverage and source identities.\n\nPlangothic webfont distribution: @free-fonts/plangothic 1.0.0, upstream https://github.com/Fitzgerald-Porthmouth-Koenigsegg/Plangothic_Project (SIL OFL). CSS declarations are restricted to actual cmap coverage. Bundled fonts are not copied from SYMBL.\n\nRebuild: python 工具/build_editor_fonts.py. FontTools and Brotli plus the documented local font assets are required.\n','utf-8')
    print(json.dumps({k:v for k,v in manifest.items() if k!='faces'},ensure_ascii=False),flush=True)


if __name__ == '__main__':
    main()
