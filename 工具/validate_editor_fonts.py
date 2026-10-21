"""Check the shipped font files against editor identities, not CSS promises."""
from pathlib import Path
from external_paths import font_work_dir
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from fontTools.ttLib import TTFont
from fontTools.pens.boundsPen import BoundsPen

ROOT = Path(__file__).resolve().parents[1]
EDITOR = ROOT/'原型/键位编辑器'


def main():
    manifest = json.loads((EDITOR/'fonts/manifest.json').read_text('utf-8'))
    data = json.loads((EDITOR/'data/mode-data.json').read_text('utf-8'))
    expected = {ord(r['char']) for r in data['characters'] if len(r['char']) == 1}
    samples = {0x25CB,0x071C,0x0A05,0x0A07,0x0A15,0x0B09,0x3400,0x4E00,0x12054,0x1319F,0x13460,0x1D400,0x20000,0x2EBF0,0x31350,0x323B0}
    def check(record):
        path = EDITOR/'fonts'/record['file']
        assert hashlib.sha256(path.read_bytes()).hexdigest() == record['sha256'], path
        font = TTFont(path)
        cmap = font.getBestCmap() or {}
        declared = set(record['codepoints'])
        if 0x0A05 in declared:
            assert record['source'] == 'NotoSansGurmukhi-Regular.ttf', 'Gurmukhi fell back to a pixel font'
            from fontTools.pens.recordingPen import RecordingPen
            glyphs=font.getGlyphSet(); pen=RecordingPen(); glyphs[cmap[0x0A05]].draw(pen)
            assert any(op in ('qCurveTo','curveTo') for op,_ in pen.value), 'Gurmukhi outline has no curves'
        assert all(cp in cmap and cmap[cp] != '.notdef' for cp in declared), path
        drawn = []
        for cp in samples & declared:
            glyphs = font.getGlyphSet()
            pen = BoundsPen(glyphs)
            glyphs[cmap[cp]].draw(pen)
            assert pen.bounds is not None and pen.bounds[2] > pen.bounds[0] and pen.bounds[3] > pen.bounds[1], hex(cp)
            drawn.append(f'U+{cp:04X}')
        font.close()
        return declared, drawn
    seen, drawn = set(), []
    with ThreadPoolExecutor(max_workers=4) as pool:
        for i,(points, samples_drawn) in enumerate(pool.map(check, manifest['faces'])):
            assert not (seen & points), 'Overlapping font declarations'
            seen.update(points); drawn.extend(samples_drawn)
            if i % 100 == 0: print('Checked font files:',i,flush=True)
    missing = {int(cp[2:],16) for cp in manifest['missing']}
    assert expected == seen | missing and not (seen & missing)
    assert len(seen) == manifest['coveredCount']
    assert samples <= seen, 'A representative glyph still lacks coverage'
    result = {'targets':len(expected),'covered':len(seen),'missing':sorted(missing),
              'fontFiles':len(manifest['faces']),'outlineSamples':sorted(drawn),
              'fontBytes':sum(r['bytes'] for r in manifest['faces'])}
    font_work_dir().mkdir(parents=True, exist_ok=True)
    (font_work_dir()/'validation.json').write_text(json.dumps(result,indent=2),'utf-8')
    print(json.dumps(result,ensure_ascii=False),flush=True)


if __name__ == '__main__': main()
