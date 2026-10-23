"""23 balanced visual buckets plus x reserve, y excluded scripts, z Chinese collection."""
import argparse,gzip,hashlib,json,re
from pathlib import Path
from datetime import datetime
from collections import Counter
from PIL import Image,ImageFont,ImageDraw
from balanced_shape_buckets import initialise,incremental,publish_report
from shape_strategy_lab import LAB,save
from inspect_shape_lab import load_run
from shape_bucket_scope import full_scope,ACTIVE

ROOT=LAB/'保留桶布局'


def suggestions(run,records):
    families={'埃及圣书体':['Egyptian Hieroglyphs','Egyptian Hieroglyphs Extended-A'],
        '楔形文字':['Cuneiform','Cuneiform Numbers and Punctuation','Early Dynastic Cuneiform'],
        '手语书写':['Sutton SignWriting'],'安纳托利亚象形文字':['Anatolian Hieroglyphs'],
        '线形文字A与B':['Linear A','Linear B Syllabary','Linear B Ideograms']}
    report=[];label=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',19);small=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',12)
    image=Image.new('RGB',(1160,650),'#f3f6fa');draw=ImageDraw.Draw(image)
    draw.text((24,12),'待你判断的复杂字形块 · 本轮全部保留',font=label,fill='#223b52')
    for i,(name,blocks) in enumerate(families.items()):
        members=[r for r in records if r['block'] in blocks];observed=[r for r in members if r['feature']['observed']]
        indices=[round(j*(len(observed)-1)/7) for j in range(8)] if observed else []
        samples=[observed[j] for j in indices];y=52+i*116
        draw.rounded_rectangle((18,y,1142,y+108),radius=9,fill='white');draw.text((28,y+15),name,font=label,fill='#223b52')
        draw.text((28,y+45),f'{len(members)} characters',font=small,fill='#61768a')
        for j,r in enumerate(samples):
            f=r['feature'];font=ImageFont.truetype(f['fontPath'],45,index=f.get('fontIndex',0));box=font.getbbox(r['char']);cx=265+j*118
            draw.text((cx-(box[2]-box[0])/2-box[0],y+43-(box[3]-box[1])/2-box[1]),r['char'],font=font,fill='#172d42')
            draw.text((cx-36,y+79),f'U+{r["cp"]:04X}',font=small,fill='#61768a')
        report.append({'name':name,'blocks':blocks,'characters':len(members),'observed':len(observed),
            'action':'保留，等待用户判断','samples':[{'char':r['char'],'cp':r['cp']} for r in samples]})
    image.save(run/'复杂文字块待判断.png');save(run/'复杂文字块待判断.json',report)
    return report


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--rebuild',action='store_true');args=parser.parse_args()
    _,source=load_run();scope,policy=full_scope()
    with gzip.open(source['featureCache'],'rt',encoding='utf-8') as stream:cached={r['cp']:r for r in map(json.loads,stream)}
    ordinary=[dict(r,feature=cached[r['cp']]['feature']) for r in scope if r['collection'] is None]
    # Use a scope-specific cache signature so PCA inputs cannot reuse a different corpus.
    source=dict(source,featureCache=source['featureCache']+'#'+hashlib.sha256(','.join(str(r['cp']) for r in ordinary).encode()).hexdigest())
    for f in source['featureManifest']['fonts']:
        if hashlib.sha256(Path(f['path']).read_bytes()).hexdigest()!=f['sha256']:raise ValueError('参考字体变更')
    ROOT.mkdir(parents=True,exist_ok=True);latest=ROOT/'最新分桶.json';previous=None
    if latest.exists():previous=Path(json.loads(latest.read_text(encoding='utf-8'))['run'])
    if previous and not args.rebuild:
        old=json.loads((previous/'范围规则.json').read_text(encoding='utf-8'))
        if any(old[k]!=policy[k] for k in ('version','active','x','y','z','retained','scriptsHash')):raise ValueError('范围规则变化，需显式重建')
        rows,model,capacity=incremental(ordinary,source,previous)
    else:rows,model,capacity=initialise(ordinary,source,ACTIVE)
    run=ROOT/'运行'/datetime.now().strftime('%Y%m%d-%H%M%S');run.mkdir(parents=True)
    save(run/'冻结分组.json',{'version':'reserved-xyz-v1','capacity':capacity,'characters':rows})
    save(run/'模型.json',model);save(run/'范围规则.json',policy)
    summary=publish_report(run,rows,model,capacity,source,ordinary)
    collections=[{'cp':r['cp'],'char':r['char'],'primary':r['collection'],'aliases':[],
        'status':'collection-only','font':cached.get(r['cp'],{}).get('feature',{}).get('font'),
        'collectionReason':r['reason'],'script':r['script'],'block':r['block']} for r in scope if r['collection']]
    allrows=sorted(rows+collections,key=lambda r:r['cp']);counts=Counter(r['primary'] for r in allrows if r['primary']);counts['x']=0
    save(run/'全部收纳.json',{'policy':policy,'characters':allrows})
    y_scripts=Counter(r['script'] for r in collections if r['primary']=='y')
    summary.update(scopeRecords=len(allrows),assigned=sum(counts.values()),ordinaryScope=len(ordinary),
        ordinaryAssigned=len(rows)-summary['pending'],letters='abcdefghijklmnopqrstuvwxyz',counts=dict(counts),
        reserved={'x':0,'y':counts['y'],'z':counts['z']},yScripts=dict(y_scripts),policy=policy)
    save(run/'摘要.json',summary)
    page_path=run/'单层分桶核对.html';page=page_path.read_text(encoding='utf-8')
    payload=json.dumps({'summary':summary,'rows':allrows},ensure_ascii=True,separators=(',',':')).replace('<','\\u003c')
    page=re.sub(r'const data=.*?;const \$=',lambda m:'const data='+payload+';const $=',page,count=1,flags=re.S)
    page=page.replace("data.summary.counts[k]+' 字</b><br><img src=\"代表字形/'+k+'.png\" alt=\"'+k+'桶字形\"></article>'",
        "data.summary.counts[k]+' 字</b><br>'+(data.summary.representatives[k]?'<img src=\"代表字形/'+k+'.png\" alt=\"'+k+'桶字形\">':(k==='x'?'暂时保留为空':k==='y'?'契丹小字、西夏文、韩文、日文；收纳，不参与普通形状聚类':'中文与汉字构形部件；收纳，不参与普通形状聚类'))+'</article>'")
    page=page.replace('只冻结第一位分桶，第三／四位尚未重新生成。','a～w为23个普通形状桶，x留空，y收纳排除文字，z收纳中文。第三／四位尚未重新生成。')
    page=page.replace('；每桶','；普通形状桶每桶')
    page_path.write_text(page,encoding='utf-8')
    text=(run/'单层分桶报告.md').read_text(encoding='utf-8').replace('单层26桶：第一轮机器分组','23个普通形状桶＋x/y/z特殊桶').replace('仅分一次26桶','普通字形仅分一次23桶').replace('→26簇迭代','→23簇迭代')
    text+='\n## 特殊桶\n\n'+f'- z 中文／汉字构形：{counts["z"]}字。\n- y 契丹、西夏、韩文、日文：{counts["y"]}字。\n- x 暂时留空。\n\n特殊收纳桶不适用±20%容量要求，且不生成正式四码。注音、女书、藏文、缅文、彝文仍参与普通聚类；普通符号和中日韩通用标点按字形保留。\n'
    text+='\n本次是用户明确调整范围后的新布局，旧26桶版本保留。此后普通更新冻结a～w主归属和别名，不自动洗牌。\n'
    (run/'单层分桶报告.md').write_text(text,encoding='utf-8')
    suggestions(run,ordinary)
    for name in ('reserved_shape_buckets.py','shape_bucket_scope.py','balanced_shape_buckets.py'):
        p=Path(__file__).parent/name;(run/name).write_bytes(p.read_bytes())
    save(latest,{'run':str(run),'completed':True,'groupingFrozen':True,'reservedXYZ':True})
    print(json.dumps({'run':str(run),'ordinary':len(ordinary),'assigned':summary['ordinaryAssigned'],
        'pending':summary['pending'],'reserved':summary['reserved'],'capacity':capacity},ensure_ascii=False))


if __name__=='__main__':main()
