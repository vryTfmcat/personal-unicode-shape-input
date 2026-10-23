"""User-approved collection buckets, separate from visual classification."""
import bisect,hashlib,json
from pathlib import Path
from shape_strategy_lab import PROJECT

SCRIPT_PATH=PROJECT/'数据/Unicode精选/UCD-17.0.0/Scripts.txt'
ACTIVE='abcdefghijklmnopqrstuvw'
Y_SCRIPTS={'Hangul','Hiragana','Katakana','Tangut','Khitan_Small_Script'}
Y_BLOCK_WORDS=('Hangul','Hiragana','Katakana','Kana ','Small Kana','Tangut','Khitan','Kanbun')
Z_BLOCKS={'CJK Radicals Supplement','Kangxi Radicals','CJK Strokes','Ideographic Description Characters'}


class Scripts:
    def __init__(self,path=SCRIPT_PATH):
        rows=[]
        for line in path.read_text(encoding='utf-8').splitlines():
            content=line.split('#',1)[0].strip()
            if not content:continue
            span,script=map(str.strip,content.split(';'));ends=span.split('..')
            rows.append((int(ends[0],16),int(ends[-1],16),script))
        rows.sort();self.rows=rows;self.starts=[r[0] for r in rows]
    def get(self,cp):
        i=bisect.bisect_right(self.starts,cp)-1
        return self.rows[i][2] if i>=0 and cp<=self.rows[i][1] else 'Unknown'


def collection(char,scripts):
    cp=int(char['codepoint'][2:],16);script=scripts.get(cp);block=char['sourceBlock'];name=char['unicodeName']
    if script in Y_SCRIPTS or any(word in block for word in Y_BLOCK_WORDS) or 'ERA NAME' in name:
        return 'y','排除的契丹／西夏／韩文／日文文字'
    if char['han'] or script=='Han' or block in Z_BLOCKS or 'IDEOGRAPH' in name:
        return 'z','中文／汉字与构形部件'
    return None,None


def full_scope():
    path=PROJECT/'原型/键位编辑器/data/mode-data.json';data=json.loads(path.read_text(encoding='utf-8'));scripts=Scripts()
    rows=[]
    for c in data['characters']:
        key,reason=collection(c,scripts)
        rows.append({'cp':int(c['codepoint'][2:],16),'char':c['char'],'block':c['sourceBlock'],
            'script':scripts.get(int(c['codepoint'][2:],16)),'collection':key,'reason':reason})
    rows.sort(key=lambda r:r['cp'])
    return rows,{'version':'reserved-xyz-v2','active':ACTIVE,'x':'暂留空','y':sorted(Y_SCRIPTS),
        'z':'统一及兼容汉字、Han脚本、汉字部首笔画和表意描述；不将注音、女书算入z',
        'retained':['Bopomofo','Nushu','Tibetan','Myanmar','Yi'],'sourceHash':hashlib.sha256(path.read_bytes()).hexdigest(),
        'scriptsHash':hashlib.sha256(SCRIPT_PATH.read_bytes()).hexdigest()}
