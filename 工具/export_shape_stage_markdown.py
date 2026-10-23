"""Export a read-only Obsidian view of the editor's stage snapshot, with escaped glyphs."""
import hashlib,html,json
from pathlib import Path
from external_paths import vault_root

PROJECT=Path(__file__).resolve().parents[1]
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def block(chars):
    # Raw HTML prevents Markdown punctuation from becoming formatting or hiding characters.
    return '<div class="unicode-max-coverage" style="font-size:1.5em;line-height:2;overflow-wrap:anywhere">'+html.escape(chars)+'</div>'

def main():
    stage_path=PROJECT/'数据/三模式/shape-stage.json';stage=read(stage_path);source=PROJECT/stage['source']
    current=Path(read(PROJECT/'数据/三模式/规则库/人工核对/最新人工核对.json')['run'])
    assert current==source,'阶段快照与当前分桶不一致，应先更新编辑器阶段数据'
    rows=read(source/'全部收纳.json')['characters'];bycp={r['cp']:r['char'] for r in rows}
    vp=vault_root()/'70_unicode/个人Unicode音型输入法';folder=vp/'数据/三模式/规则库/人工核对/运行'/source.name/'全部字符预览';folder.mkdir(parents=True,exist_ok=True)
    base='70_unicode/个人Unicode音型输入法/数据/三模式/规则库/人工核对/运行/'+source.name+'/全部字符预览/'
    labels={'x':'组合与附加标记','y':'排除文字收纳','z':'中文与汉字构件','待分类':'待补字形与分类'}
    lists=dict(stage['buckets'],待分类=stage['unclassified']);decoded={};pages=[]
    def front(title):return '---\ntitle: '+title+'\ncssclasses:\n  - unicode-full-table\nstage_id: '+stage['id']+'\nview_only: true\n---\n\n'
    for name,codes in lists.items():
        chars=''.join(bycp[cp] for cp in codes);decoded[name]=chars
        title='桶 '+name if name!='待分类' else name
        order='按图形相似度排列' if name in 'abcdefghijklmnopqrstuvw' else '独立收纳，保留原顺序'
        text=front(title)+'# '+title+((' · '+labels[name]) if name in labels else '')+'\n\n[['+base+'分桶总览|返回分桶总览]] · '+str(len(codes))+' 字 · '+order+'\n\n'+block(chars)+'\n'
        (folder/(name+'.md')).write_text(text,encoding='utf-8');pages.append(name+'.md')
        rendered=html.unescape(text.split('overflow-wrap:anywhere">',1)[1].split('</div>',1)[0]);assert rendered==chars
    aggregate=front('a–w 图形分桶汇总')+'# a–w 图形分桶汇总\n\n[['+base+'分桶总览|返回分桶总览]]\n\n共 28,223 字；仅展示当前主归属。\n\n'
    for a in 'abcdefghijklmnopqrstuvw':aggregate+='## '+a+' · '+str(len(stage['buckets'][a]))+' 字\n\n'+block(decoded[a])+'\n\n'
    (folder/'a-w汇总.md').write_text(aggregate,encoding='utf-8');pages.append('a-w汇总.md')
    overview=front('当前图形分桶总览')+'# 当前图形分桶总览\n\n版本：`'+stage['id']+'`。普通图形桶 28,223 字，965 项归属已确认；其余仍是机器分组。`o` 为普通图形桶，不专属于楔笔族。\n\n'
    overview+='[['+base+'a-w汇总|一页查看全部 a–w 桶]] · [[70_unicode/个人Unicode音型输入法/理论/图形分桶阶段总结-2026-10-16|阶段总结与三个待优化问题]]\n\n'
    overview+='| 桶 | 字符数 |\n| --- | ---: |\n'
    for a in 'abcdefghijklmnopqrstuvw':overview+='| [['+base+a+'|'+a+']] | '+str(len(stage['buckets'][a]))+' |\n'
    overview+='\n## 单独收纳与待分类\n\n'
    for a in ('x','y','z','待分类'):overview+='- [['+base+a+'|'+a+' · '+labels[a]+']]：'+str(len(lists[a]))+' 字。\n'
    overview+='\n## 保存位置与编辑边界\n\n- 权威阶段快照：[工程 shape-stage.json](<'+stage_path.as_uri()+'>)。\n- 完整研究版本：[当前研究目录](<'+source.as_uri()+'>)。\n- 编辑器：[本机键位编辑器](http://127.0.0.1:8765/) → 全形模式 → 阶段分桶。\n- 本目录是从阶段快照生成的 **Markdown 阅读视图**，不是第二份可编辑码本。修改这些页面不会回写编辑器。\n- 字符使用 HTML 转义显示，避免星号、反引号、尖括号被当作 Markdown 格式；桶内顺序与编辑器一致。附加符号可能依赖字体或与相邻字符组合显示。\n- 第二至第四位尚未分配，本次未发布到小狼毫。\n\n源快照 SHA-256：`'+hashlib.sha256(stage_path.read_bytes()).hexdigest()+'`。\n'
    (folder/'分桶总览.md').write_text(overview,encoding='utf-8');pages.append('分桶总览.md')
    assert sum(len(cps) for cps in lists.values())==159345
    for a in 'abcdefghijklmnopqrstuvw':assert decoded[a]==(source/'全部字符预览'/(a+'.md')).read_text(encoding='utf-8')
    report={'stageId':stage['id'],'markdownDirectory':str(folder),'pages':len(pages),'characters':159345,'ordinaryCharacters':28223,'displayOrderMatchesEditor':True,'htmlEscapingRoundtrip':True,'groupingChanged':False}
    (source/'Obsidian导出校验.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    index=vp/'个人Unicode音型输入法.md';s=index.read_text(encoding='utf-8');entry='- [['+base+'分桶总览|Obsidian 当前分桶总览（Markdown）]]\n';heading='## 桶分类核对入口（2026-10-16）\n\n'
    if entry not in s:s=s.replace(heading,heading+entry+'\n',1);index.write_text(s,encoding='utf-8')
    summary=vp/'理论/图形分桶阶段总结-2026-10-16.md';s=summary.read_text(encoding='utf-8');entry='- [['+base+'分桶总览|Obsidian 当前分桶与全部字符（Markdown）]]\n'
    if entry not in s:s=s.replace('## 入口\n\n','## 入口\n\n'+entry,1);summary.write_text(s,encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False))

if __name__=='__main__':main()
