"""Audit preview coverage and build portable native-first CSS without changing characters."""
import base64, hashlib, io, json, re, shutil
from pathlib import Path
from collections import Counter
from fontTools.ttLib import TTFont
from fontTools import subset

ROOT=Path(__file__).resolve().parents[1]
VAULT=ROOT.parents[1]
LAB=ROOT/'数据/三模式/规则库'
RUN=Path(json.loads((LAB/'人工核对/最新人工核对.json').read_text(encoding='utf-8'))['run'])
OUT=RUN/'字体全面检查-20261014'
ASSETS=Path('C:/Users/86137/Documents/Codex/codex资料/字体/Obsidian Unicode')
CSS=VAULT/'.obsidian/snippets/unicode-font-fallback.css'

def names(font):
    result=[]
    for rec in font['name'].names:
        if rec.nameID in (4,6,1):
            try: value=rec.toUnicode()
            except Exception: continue
            if value not in result: result.append(value)
    return result

def main():
    OUT.mkdir(exist_ok=True)
    if not (OUT/'修改前.css').exists(): shutil.copy2(CSS,OUT/'修改前.css')
    records=json.loads((RUN/'全部收纳.json').read_text(encoding='utf-8'))['characters']
    targets={r['cp'] for r in records if r.get('primary') in list('abcdefghijklmnopqrstuvwx')}
    allcp={r['cp'] for r in records}
    windows=Path('C:/Windows/Fonts')
    paths=[windows/n for n in ('segoeui.ttf','seguisym.ttf','seguihis.ttf')]
    paths+=sorted((LAB/'字体').glob('*.ttf'))+[ASSETS/'Gentium-Regular.ttf']
    # Mongolian Baiti has invalid composite references in the native renderer on this machine.
    paths += [windows/n for n in ('Nirmala.ttc','ebrima.ttf','himalaya.ttf','phagspa.ttf','javatext.ttf','mmrtext.ttf','sylfaen.ttf','gadugi.ttf','taile.ttf','ntailu.ttf','msyi.ttf','mvboli.ttf','malgun.ttf','msyh.ttc')]
    # Exclude Segoe UI Emoji: use the monochrome outline fallbacks below.
    native_end=len(paths)
    paths += sorted((ASSETS/'单色轮廓').glob('*V2.ttf'))
    paths += [ASSETS/'单色轮廓/ObsidianOutline-SIP.ttf',ASSETS/'单色轮廓/ObsidianOutline-TIP.ttf',ASSETS/'unifont-17.0.04.otf',ASSETS/'unifont_upper-17.0.04.otf']
    remaining=set(targets); allcovered=set(); native=set(); assigned={}; fonts=[]; faces=[]
    for pos,path in enumerate(paths):
        if not path.exists(): continue
        facecount=1
        if path.suffix.lower()=='.ttc':
            from fontTools.ttLib import TTCollection
            collection=TTCollection(path,lazy=True); facecount=len(collection.fonts); collection.close()
        for index in range(facecount):
            font=TTFont(path,fontNumber=index,lazy=False)
            cmap=font.getBestCmap() or {}
            if 'head' in font and font['head'].flags & 0x4000: font.close(); continue
            cover={cp for cp,glyph in cmap.items() if glyph!='.notdef'}
            allcovered |= cover & allcp
            if pos<native_end: native |= cover & targets
            selected=remaining & cover
            if not selected: font.close(); continue
            alias=f'UnicodePreview{len(fonts):02d}'
            original_names=names(font)
            # Embedded portable subsets for redistributable project fonts. Windows faces use local names.
            embed=not str(path).startswith('C:\\Windows') and not str(path).startswith('C:/Windows')
            if embed:
                key=hashlib.sha256(path.read_bytes()+','.join(map(str,sorted(selected))).encode()).hexdigest()
                cache=OUT/(key+'.woff2')
                if cache.exists(): blob=cache.read_bytes()
                else:
                    options=subset.Options(); options.recalc_timestamp=False
                    sub=subset.Subsetter(options=options); sub.populate(unicodes=selected); sub.subset(font)
                    font.flavor='woff2'; buffer=io.BytesIO(); font.save(buffer)
                    blob=buffer.getvalue(); cache.write_bytes(blob)
                (OUT/(alias+'.woff2')).write_bytes(blob)
                source='url("data:font/woff2;base64,'+base64.b64encode(blob).decode()+'") format("woff2")'
            else:
                source=', '.join('local('+json.dumps(n,ensure_ascii=False)+')' for n in original_names)
            ranges=','.join(f'U+{cp:X}' for cp in sorted(selected))
            faces.append('@font-face{font-family:"'+alias+'";src:'+source+';font-style:normal;font-weight:400;unicode-range:'+ranges+';}')
            info={'alias':alias,'file':str(path),'index':index,'names':original_names,'assignedCount':len(selected),'embedded':embed,'native':pos<native_end,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
            fonts.append(info)
            for cp in selected: assigned[cp]=info
            remaining-=selected; font.close()
            print(path.name,len(selected),'remaining',len(remaining),flush=True)
    old=CSS.read_text(encoding='utf-8')
    # Replace previous generated additions on repeated runs; keep legacy yz coverage below native aliases.
    old=old.split('/* BEGIN PORTABLE PREVIEW FONTS */')[0]
    stack=','.join('"'+f['alias']+'"' for f in fonts)+',"Obsidian Unicode U17",sans-serif'
    selector='.markdown-preview-view.unicode-full-table p,.markdown-source-view.unicode-full-table .cm-line:not(.HyperMD-header),.workspace-leaf-content[data-type="markdown"]:has(.view-header-breadcrumb[aria-label="全部字符预览"]) .markdown-preview-view p,.workspace-leaf-content[data-type="markdown"]:has(.view-header-breadcrumb[aria-label="全部字符预览"]) .markdown-source-view .cm-line:not(.HyperMD-header),.unicode-max-coverage'
    addition='\n/* BEGIN PORTABLE PREVIEW FONTS */\n/* Native script fonts precede outline/bitmap fallbacks. Original font licenses remain in project and source font directories. */\n'+'\n'.join(faces)+'\n'+selector+'{font-family:'+stack+'!important;font-synthesis:none;text-rendering:optimizeLegibility;}\n'
    CSS.write_text(old+addition,encoding='utf-8')
    missing=[{'cp':r['cp'],'char':r['char'],'bucket':r.get('primary')} for r in records if r['cp'] in remaining]
    bitmap=[{'cp':cp,'char':chr(cp),'font':assigned[cp]['file']} for cp in sorted(targets-native) if cp in assigned]
    report={'previewCharacters':len(targets),'covered':len(targets-remaining),'nativeCoverage':len(targets&native),'outlineFallbackCount':len(bitmap),'missing':missing,'outlineFallback':bitmap,'allIdentityCount':len(allcp),'allFontCmapCovered':len(allcovered),'fonts':fonts,'groupingChanged':False,'note':'cmap audit is not proof of application rendering; some universal fallback outlines are intrinsically pixel-derived.'}
    (OUT/'字体覆盖检查.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    body=[]
    for letter in 'abcdefghijklmnopqrstuvwx':
        chars=[r['char'] for r in records if r.get('primary')==letter]
        body.append('<h2>'+letter+'</h2><div class="chars">'+''.join(chars).replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')+'</div>')
    html='<!doctype html><meta charset="utf-8"><title>全部桶字体核对</title><style>'+ '\n'.join(faces)+'body{background:#1e1e1e;color:#ddd;margin:32px} .chars{font-family:'+stack+';font-size:28px;line-height:2;overflow-wrap:anywhere;font-variant-emoji:text;font-variant-ligatures:none}h2{font:24px system-ui}</style>' + ''.join(body)
    (OUT/'全部桶字体核对.html').write_text(html,encoding='utf-8')
    review=RUN/'单层分桶核对.html'
    if not (OUT/'修改前核对页.html').exists(): shutil.copy2(review,OUT/'修改前核对页.html')
    reviewtext=(OUT/'修改前核对页.html').read_text(encoding='utf-8')
    reviewtext=reviewtext.replace('</style>','\n'+'\n'.join(faces)+'\n.char.portable-fonts{font-family:'+stack+'!important;}\n</style>',1)
    reviewtext=reviewtext.replace('class="char" style="font-family:', 'class="char\'+(\'abcdefghijklmnopqrstuvwx\'.includes(r.primary)&&r.primary?\' portable-fonts\':\'\')+\'" style="font-family:')
    review.write_text(reviewtext,encoding='utf-8')
    # Native-render visual evidence, including formerly missing and pixel-derived script examples.
    from PIL import Image, ImageDraw, ImageFont
    samples=[0x12480,0x13460,0x1D800,0x16F05,0x1B05,0x10C80,0x10080,0x12F90,0x0E01,0x11A00]
    samples=[cp if cp in assigned else next((n for n in sorted(assigned) if cp<=n<cp+128),None) for cp in samples]
    samples=[cp for cp in samples if cp is not None]
    image=Image.new('RGB',(900,110*len(samples)+60),'#1e1e1e');draw=ImageDraw.Draw(image)
    label=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',18)
    outlinepaths=[ASSETS/'单色轮廓/ObsidianOutline-BMP-V2.ttf',ASSETS/'单色轮廓/ObsidianOutline-SMP-V2.ttf']
    draw.text((20,15),'U+ code        previous fallback          native font',font=label,fill='white')
    for row,cp in enumerate(samples):
        info=assigned[cp];newfont=ImageFont.truetype(info['file'],48,index=info['index'])
        oldfont=ImageFont.truetype(str(outlinepaths[cp>0xffff]),48)
        y=70+110*row;draw.text((20,y),f'U+{cp:04X}',font=label,fill='white')
        draw.text((200,y),chr(cp),font=oldfont,fill='white',anchor='lt');draw.text((470,y),chr(cp),font=newfont,fill='white',anchor='lt')
        draw.text((470,y+60),Path(info['file']).stem,font=label,fill='#aaaaaa')
    image.save(OUT/'字体修正对照.png')
    print(json.dumps({k:v for k,v in report.items() if k not in ('fonts','outlineFallback','missing')},ensure_ascii=False))

if __name__=='__main__': main()
