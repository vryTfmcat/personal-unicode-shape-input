"""Replace pixel-derived editor fallbacks with verified native source outlines.

Incremental: does not rebuild or change existing CJK/approved native faces.
Source downloads and their hashes are recorded in work/editor-fonts/outline-sources.json.
"""
from pathlib import Path
import argparse
import hashlib
import io
import json
import logging
from collections import defaultdict
from fontTools import subset
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont
import build_editor_fonts as build


def main():
    parser=argparse.ArgumentParser(__doc__)
    parser.add_argument('--only-family', help='Update one family without waiting for unrelated large fonts')
    parser.add_argument('--exclude-family', action='append', default=[])
    args=parser.parse_args()
    logging.getLogger('fontTools.subset').setLevel(logging.ERROR)
    path = build.OUT/'manifest.json'
    manifest = json.loads(path.read_text('utf-8'))
    remaining = {cp for r in manifest['faces'] if r['kind']=='fallback-outline' for cp in r['codepoints']}
    targets = {cp for r in manifest['faces'] for cp in r['codepoints']}
    before = len(remaining)
    additions = []
    sources = sorted(build.WORK.glob('Noto*.ttf'))+sorted(build.WORK.glob('Noto*.otf'))
    sources += [build.ROOT/'数据/三模式/规则库/字体/EgyptologyExtended.ttf']
    if args.only_family:
        sources=[source for source in sources if source.stem==args.only_family]
    sources=[source for source in sources if source.stem not in args.exclude_family]
    # Reuse completed subsets from an interrupted batch instead of recompressing.
    known={r['file'] for r in manifest['faces']}
    cache={tuple(r['codepoints']):build.OUT/r['file'] for r in manifest['faces'] if r['kind']=='native-outline'}
    for candidate in build.OUT.glob('ue-*.woff2'):
        if candidate.name in known: continue
        font=TTFont(candidate)
        if font['name'].getDebugName(1)=='UnicodeEditorOutline':
            cache[tuple(sorted(font.getBestCmap() or {}))]=candidate
        font.close()
    for source in sources:
        if not source.exists(): continue
        original = TTFont(source)
        points = remaining & {cp for cp,g in (original.getBestCmap() or {}).items() if g!='.notdef'}
        # Keep this script in one font, including marks previously supplied by
        # Multani; a mixed base/mark pair can break Indic shaping.
        if source.name == 'NotoSansGurmukhi-Regular.ttf':
            points |= {cp for cp in targets if 0x0A00 <= cp <= 0x0A7F and cp in (original.getBestCmap() or {})}
        original.close()
        if not points: continue
        buckets = defaultdict(set)
        for cp in points:
            buckets[0].add(cp)
        for selected in buckets.values():
            cached=cache.get(tuple(sorted(selected)))
            if cached:
                blob=cached.read_bytes(); digest=hashlib.sha256(blob).hexdigest()
                additions.append({'file':cached.name,'source':source.name,'kind':'native-outline',
                                  'sha256':digest,'bytes':len(blob),'codepoints':sorted(selected)})
                remaining.difference_update(selected)
                continue
            font = TTFont(source)
            if 'fvar' in font:
                axes = {a.axisTag:400 if a.axisTag=='wght' else a.defaultValue for a in font['fvar'].axes}
                font = instantiateVariableFont(font,axes,inplace=True)
            options = subset.Options(); options.recalc_timestamp=False
            sub = subset.Subsetter(options=options)
            sub.populate(unicodes=selected); sub.subset(font)
            for rec in font['name'].names:
                if rec.nameID in (1,3,4,6,16):
                    rec.string = 'UnicodeEditorOutline'.encode(rec.getEncoding())
            font.flavor='woff2'; buffer=io.BytesIO(); font.save(buffer); font.close()
            blob=buffer.getvalue(); digest=hashlib.sha256(blob).hexdigest()
            filename=f'ue-{digest[:16]}.woff2'
            (build.OUT/filename).write_bytes(blob)
            additions.append({'file':filename,'source':source.name,'kind':'native-outline',
                              'sha256':digest,'bytes':len(blob),'codepoints':sorted(selected)})
            remaining.difference_update(selected)
        print(source.name,len(points),'promoted',flush=True)
    replaced={cp for r in additions for cp in r['codepoints']}
    for record in manifest['faces']:
        record['codepoints']=sorted(set(record['codepoints'])-replaced)
    manifest['faces']=[r for r in manifest['faces'] if r['codepoints']]+additions
    manifest['outlineUpgrade']={'fallbackBefore':before,'fallbackAfter':len(remaining),'promoted':len(replaced)}
    css='/* Generated disjoint, same-origin font coverage. */\n'
    for r in manifest['faces']:
        css+='@font-face{font-family:"Unicode Editor";src:url("./'+r['file']+'") format("woff2");font-style:normal;font-weight:400;font-display:swap;unicode-range:'+build.ranges(r['codepoints'])+';}\n'
    css+='.glyph,.inspector-glyph,.graph-node-title,.graph-node-symbol,.pair-symbol,.brand-mark{font-family:"Unicode Editor","Segoe UI Symbol",sans-serif;font-synthesis:none;}\n.glyph,.inspector-glyph{line-height:1.35;min-height:1.35em;overflow:visible;}\n'
    temp=build.OUT/'editor-fonts.css.tmp';temp.write_text(css,'utf-8');temp.replace(build.OUT/'editor-fonts.css')
    temp=path.with_suffix('.tmp');temp.write_text(json.dumps(manifest,ensure_ascii=False,indent=2),'utf-8');temp.replace(path)
    source_records=build.WORK/'outline-sources.json'
    if source_records.exists():
        import shutil
        shutil.copy2(source_records,build.OUT/'outline-sources.json')
    print(json.dumps(manifest['outlineUpgrade']),flush=True)


if __name__=='__main__': main()
