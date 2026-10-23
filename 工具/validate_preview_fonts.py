"""Verify every preview codepoint against selected source and embedded subset fonts."""
import json,re,hashlib,unicodedata
from fontTools.ttLib import TTFont
from PIL import ImageFont
from repair_preview_fonts import OUT,RUN

def main():
    d=json.loads((OUT/'字体覆盖检查.json').read_text(encoding='utf-8'))
    records=json.loads((RUN/'全部收纳.json').read_text(encoding='utf-8'))['characters']
    remaining={r['cp'] for r in records if r.get('primary') in list('abcdefghijklmnopqrstuvwx')}
    blanks=[];subset_missing=[];errors=[];total=0
    for r in d['fonts']:
        f=TTFont(r['file'],fontNumber=r['index']);selected=remaining&set(f.getBestCmap() or {});remaining-=selected;f.close()
        if r['embedded']:
            f=TTFont(OUT/(r['alias']+'.woff2'));subset_missing+=sorted(selected-set(f.getBestCmap() or {}));f.close()
        font=ImageFont.truetype(r['file'],48,index=r['index'])
        for cp in sorted(selected):
            try:
                if font.getmask(chr(cp)).getbbox() is None:
                    blanks.append({'cp':cp,'category':unicodedata.category(chr(cp)),'name':unicodedata.name(chr(cp),'Unicode17'),'font':r['file']})
            except Exception as e:errors.append({'cp':cp,'font':r['file'],'error':str(e)})
            total+=1
    before=(OUT/'修改前核对页.html').read_text(encoding='utf-8');after=(RUN/'单层分桶核对.html').read_text(encoding='utf-8')
    def payload(s):return re.search(r'const data=(.*?);\s*(?:const|function)',s,re.S).group(1)
    result={'rendered':total,'unmapped':sorted(remaining),'embeddedSubsetMissing':subset_missing,'renderErrors':errors,'emptyInkCount':len(blanks),'emptyInk':blanks,'reviewDataUnchanged':payload(before)==payload(after),'mdFiles':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (RUN/'全部字符预览').glob('*.md')}}
    (OUT/'渲染验证.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print({k:v for k,v in result.items() if k not in ('mdFiles','emptyInk')});print('empty ink',blanks)
    assert not remaining and not subset_missing and not errors and result['reviewDataUnchanged']

if __name__=='__main__':main()
