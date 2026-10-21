"""Build a compact, read-only snapshot; never write the source codebooks."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
EDITOR=ROOT/'原型/键位编辑器'
def main():
    load=lambda p:json.loads(p.read_text(encoding='utf-8'))
    base=load(EDITOR/'data/mode-data.json')
    book=load(ROOT/'数据/三模式/codebooks.json')
    stage=load(EDITOR/'data/shape-stage.json')
    bucket={cp:(key,rank) for key,cps in stage['buckets'].items() for rank,cp in enumerate(cps)}
    chars=[]
    for c in base['characters']:
        bc=book.get('blockOverrides',{}).get(c['id'],c.get('blockCode')) or {}
        code=bc.get('code','')
        if c['id'] not in book.get('blockOverrides',{}) and code:
            code=book.get('prefixOverrides',{}).get(code[:2],code[:2])+code[2:]
        b,r=bucket.get(ord(c['char']),(None,0))
        chars.append([c['id'],c['char'],c['unicodeName'],c['blockId'],code,b,r])
    personal={k:{'favorite':bool(v.get('favorite')), 'chineseName':v.get('chineseName',''), 'tags':v.get('tags',[])} for k,v in book.get('metadata',{}).items() if v.get('favorite') or v.get('chineseName') or v.get('tags')}
    result={'format':'unicode-touch-catalog-v1','unicodeVersion':base['unicodeVersion'],'stageId':stage['id'], 'personal':personal,'aliases':book.get('personal',{}),
        'blocks':[[b['id'],b['name'],b['plane']] for b in base['blocks']], 'characters':chars}
    target=EDITOR/'touch/catalog.json';target.parent.mkdir(exist_ok=True)
    target.write_text(json.dumps(result,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
    print(f'{len(chars)} characters; {len(result["blocks"])} blocks; {target.stat().st_size} bytes')
if __name__=='__main__':main()
