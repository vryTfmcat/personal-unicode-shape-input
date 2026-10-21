"""Prepare <= 60 native font families for Trime from existing local font assets."""
from pathlib import Path
import json,hashlib,logging,shutil
from fontTools.ttLib import TTFont
from fontTools import subset
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.pens.recordingPen import DecomposingRecordingPen
from fontTools.pens.transformPen import TransformPen
ROOT=Path(__file__).resolve().parents[1]
WEB=ROOT/'原型/键位编辑器/fonts'
OUT=ROOT/'原型/键位编辑器/touch/trime-base/fonts'
ASSETS=Path.home()/'Documents/Codex/codex资料/字体/Obsidian Unicode'
logging.getLogger('fontTools').setLevel(logging.ERROR)
def main():
    manifest=json.loads((WEB/'manifest.json').read_text(encoding='utf8'))
    catalog=json.loads((ROOT/'原型/键位编辑器/touch/catalog.json').read_text(encoding='utf8'))
    needed={ord(c[1]) for c in catalog['characters']}
    salt=b'trime-native-fonts-v2-outline-only'
    signature=hashlib.sha256(json.dumps(manifest,sort_keys=True,separators=(',',':')).encode('utf8')+salt).hexdigest()
    legacy_signature=hashlib.sha256((WEB/'manifest.json').read_bytes()+salt).hexdigest()
    report=OUT/'coverage.json'
    if report.exists():
        previous=json.loads(report.read_text(encoding='utf8'))
        if previous.get('inputSha256') in (signature,legacy_signature) and all((OUT/n).exists() for n in previous['fonts']):
            if previous['inputSha256']!=signature:
                previous['inputSha256']=signature
                report.write_text(json.dumps(previous,ensure_ascii=False,indent=2),encoding='utf8')
            print('Native fonts cached:',len(previous['fonts']),'families;',previous['covered'],'characters',flush=True);return previous
    OUT.mkdir(parents=True,exist_ok=True)
    fonts=[];covered=set()
    # Preserve source shaping/layout tables for major script specialists, avoiding glyph-only merging.
    native=sorted((f for f in manifest['faces'] if f['kind']=='native-outline'),key=lambda f:len(f['codepoints']),reverse=True)
    selected=native[:32]
    for source in ['NotoMusic-Regular.ttf','NotoSansGlagolitic-Regular.ttf','NotoSansCuneiform-Regular.ttf','NotoSansEgyptianHieroglyphs-Regular.ttf']:
        f=next((f for f in native if f['source']==source),None)
        if f and f not in selected:selected.append(f)
    gentium=ASSETS/'Gentium-Regular.ttf'
    if gentium.exists():
        f=TTFont(gentium);f.flavor=None;name='unicode-latin.ttf';f.save(OUT/name);fonts.append(name);covered.update(cp for cp,g in f.getBestCmap().items() if g!='.notdef');f.close()
    for i,face in enumerate(selected):
        f=TTFont(WEB/face['file']);f.flavor=None;ext='otf' if 'CFF ' in f else 'ttf';name=f'unicode-native-{i:02d}.{ext}'
        f.save(OUT/name);fonts.append(name);covered.update(cp for cp,g in f.getBestCmap().items() if g!='.notdef');f.close()
    print('Script specialists:',len(fonts),'families',flush=True)
    for i,source in enumerate(['Essenfont-BMP-U17.ttf','Essenfont-SMP-U17.ttf','Essenfont-SIP-U17.ttf','Essenfont-TIP-U17.ttf','unifont-17.0.04.otf','unifont_upper-17.0.04.otf']):
        f=TTFont(ASSETS/source)
        # Android may choose embedded blank bitmap strikes over valid glyf outlines.
        for table in ['CBDT','CBLC','EBDT','EBLC','sbix']:
            if table in f:del f[table]
        cmap=f.getBestCmap();cps=(needed-covered)&{cp for cp,g in cmap.items() if g!='.notdef'}
        if not cps:f.close();continue
        options=subset.Options();options.recalc_timestamp=False;options.retain_gids=False
        tool=subset.Subsetter(options=options);tool.populate(unicodes=cps);tool.subset(f)
        f.flavor=None;ext='otf' if 'CFF ' in f else 'ttf';name=f'unicode-fallback-{i:02d}.{ext}';f.save(OUT/name);fonts.append(name)
        covered.update(cp for cp,g in f.getBestCmap().items() if g!='.notdef');f.close();print(source,len(cps),'characters',flush=True)
    # Plangothic shards share an OFL source. Repack only missing CJK outlines into bounded TTFs.
    glyphs={};metrics={};mapping={};chunk=0
    def flush():
        nonlocal glyphs,metrics,mapping,chunk
        if not mapping:return
        name=f'unicode-cjk-{chunk:02d}.ttf';fb=FontBuilder(1000,isTTF=True)
        pen=TTGlyphPen(None);empty=pen.glyph();all_glyphs={'.notdef':empty,**glyphs}
        fb.setupGlyphOrder(list(all_glyphs));fb.setupCharacterMap(mapping);fb.setupGlyf(all_glyphs)
        fb.setupHorizontalMetrics({'.notdef':(1000,0),**metrics});fb.setupHorizontalHeader(ascent=1000,descent=-200)
        fb.setupNameTable({'familyName':f'Unicode CJK Fallback {chunk}','styleName':'Regular','uniqueFontIdentifier':f'UnicodeCJK-{chunk}-1','fullName':f'Unicode CJK Fallback {chunk}','psName':f'UnicodeCJKFallback{chunk}'})
        fb.setupOS2(sTypoAscender=1000,sTypoDescender=-200,usWinAscent=1200,usWinDescent=400);fb.setupPost();fb.setupMaxp();fb.save(OUT/name)
        fonts.append(name);print(name,len(mapping),'characters',flush=True);chunk+=1;glyphs={};metrics={};mapping={}
    for face in manifest['faces']:
        cps=set(face['codepoints'])&(needed-covered)
        if face['kind']!='plangothic' or not cps:continue
        f=TTFont(WEB/face['file']);gs=f.getGlyphSet();scale=1000/f['head'].unitsPerEm;cmap=f.getBestCmap()
        for cp in sorted(cps):
            gn=cmap[cp];rec=DecomposingRecordingPen(gs);gs[gn].draw(rec);pen=TTGlyphPen(None);rec.replay(TransformPen(pen,(scale,0,0,scale,0,0)))
            target=f'u{cp:X}';glyphs[target]=pen.glyph();advance,lsb=f['hmtx'][gn];metrics[target]=(round(advance*scale),round(lsb*scale));mapping[cp]=target;covered.add(cp)
            if len(mapping)>=20000:flush()
        f.close()
    flush()
    missing=sorted(needed-covered)
    assert not missing,missing[:30]
    assert len(fonts)<60,len(fonts)
    # Verify the actual serialized cmap in every shipped file, not just source coverage.
    actual=set()
    for name in fonts:
        f=TTFont(OUT/name,lazy=True)
        assert not any(t in f for t in ['CBDT','CBLC','EBDT','EBLC','sbix']),name
        actual.update(cp for cp,g in f.getBestCmap().items() if g!='.notdef');f.close()
    assert needed<=actual
    licenses=OUT/'licenses';licenses.mkdir(exist_ok=True)
    for p in (WEB/'licenses').glob('*'):
        if p.is_file():shutil.copy2(p,licenses/p.name)
    ofl=ROOT.parent/'cache/font-sources/editor-fonts/plangothic/LICENSE'
    if ofl.exists():shutil.copy2(ofl,licenses/'Plangothic-OFL.txt')
    result={'format':'unicode-trime-fonts-v1','inputSha256':signature,'fonts':fonts,'target':len(needed),'covered':len(needed&actual),'missing':missing,'bytes':sum((OUT/n).stat().st_size for n in fonts),'note':'Native script shaping retained where selected; CJK fallback outlines repacked from existing Plangothic shards. Mapping coverage is not device rendering verification.'}
    report.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8');print('PASS',len(fonts),'fonts,',result['bytes'],'bytes;',result['covered'],'characters covered',flush=True);return result
if __name__=='__main__':main()
