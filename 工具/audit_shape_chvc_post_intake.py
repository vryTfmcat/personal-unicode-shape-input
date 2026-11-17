"""Post-intake fixed-cohort recommendations; no shared files or paths are mutated."""
from collections import Counter
from datetime import datetime
import copy
import hashlib
import html
import json
from pathlib import Path
from statistics import median
import sys

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / '原型/键位编辑器'))
import shape_overview as overview
from audit_shape_chvc_structure import reliable_choices, measurements
from audit_shape_historical_buckets import protect
from shape_experiment_features import observe, render

OUTPUT = overview.RUNS / '20261024-chvc-post-intake-v1'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def snapshot():
    result = protect()
    paths = [overview.CHVC_RUN/'chvc结构细分与优先级试验.json',
             overview.CENTRE_RUN/'中心属性交点试验.json',
             overview.THICK_RUN/'粗笔分叉误拒复核.json',
             PROJECT/'原型/键位编辑器/data/pictorial-exclusive-allocation.json',
             PROJECT/'原型/键位编辑器/shape_overview.py',
             PROJECT/'原型/键位编辑器/shape-key-overview.js',
             PROJECT/'原型/键位编辑器/shape-key-overview.html',
             PROJECT/'工具/audit_shape_chvc_structure.py',
             PROJECT/'工具/shape_recovery_geometry.py',
             PROJECT/'工具/shape_experiment_features.py',
             PROJECT/'工具/shape_candidate_layers.py',
             PROJECT/'数据/三模式/shape-stage.json', Path(__file__)]
    paths += list((PROJECT/'实体/字符').glob('*.md'))
    result.update({str(p.relative_to(PROJECT)):digest(p) for p in paths if p.is_file()})
    return result


def choose(current, choices, available):
    """Frozen preferences have priority over any newly supported alternative."""
    if current:
        return list(current), False
    eligible = [p for p in choices if p['code'] in available]
    return ([eligible[0]['code']], True) if eligible else ([], False)


def burden(values):
    values = sorted(values)
    return {'characters':len(values), 'mean':round(sum(values)/len(values),3),
            'median':median(values), 'p90':values[int(.9*(len(values)-1))],
            'maximum':max(values), 'totalCandidateExposure':sum(values)}


def save(path, data):
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


def build():
    if OUTPUT.exists():
        raise FileExistsError('独立结果已存在；不得覆盖')
    protected = snapshot()
    view = overview.Overview()
    groups = view.collision_groups(4,True)
    counts = Counter({r['code']:r['count'] for r in groups})
    selected = set(view.allocation_members('chvc'))
    base, thick = overview.chvc_records(), overview.thick_records()
    assert selected == set(base)-overview.exclusive_intake().keys()
    assert len(selected)==1554 and len(overview.exclusive_intake())==4362
    records=[]; fonts={}; fresh=0
    for cp in sorted(selected):
        row=view.chunk(view.rows[cp]['detailUrl'])[cp]
        current=view.brief(cp,True)
        observations=[]
        for old,variant in zip(base[cp]['checks'],thick[cp]['variants'],strict=True):
            assert (old['size'],old['weight'])==(variant['size'],variant['weight'])
            observations.append(dict(old,visibleForks=variant['proofs']))
        choices=reliable_choices(row,observations,counts)
        preferred,added=choose(current['preferredCodes'],choices,current['codes'])
        if added:
            # Independently reproduce original locked font and all nine variants.
            fresh_observations=[]
            for old in observations:
                f=observe(*render(row['char'],row['font']['path'],row['font'].get('index',0),
                                  size=old['size'],weight=old['weight'],fonts=fonts))
                measured=measurements(f)
                assert measured['bodyBBox']==old['bodyBBox'],(cp,'主体变动')
                fresh_observations.append(measured)
            verified=reliable_choices(row,fresh_observations,counts)
            assert preferred[0] in [p['code'] for p in verified],(cp,'推荐缺少新鲜九扰动支持')
            chosen=next(p for p in verified if p['code']==preferred[0])
            observations=fresh_observations
            fresh+=1
            if fresh%10==0:print(f'新增建议字形复验 {fresh}',flush=True)
        else:
            chosen=None
        before_code=current['preferredCodes'][0] if current['preferredCodes'] else 'chvc'
        after_code=preferred[0] if preferred else 'chvc'
        assert cp in view.allocation_members(after_code)
        assert counts[after_code]<=counts[before_code] or not added
        positive=thick[cp]['afterPositiveVariants']
        records.append({'cp':cp,'char':row['char'],'font':row['font'],'preview':row['preview'],
            'beforePreferred':current['preferredCodes'],'afterPreferred':preferred,
            'beforeCode':before_code,'afterCode':after_code,
            'beforeBurden':counts[before_code],'afterBurden':counts[after_code],
            'newRecommendation':added,'legacyCodes':current['codes'],
            'afterPositiveVariants':positive,'oldReviewed':row['oldReviewed'],
            'triage':'保留既有推荐' if current['preferredCodes'] else
                     '新增既有结构入口推荐' if added else
                     '有稳定局部分叉，尚无本轮可靠结构推荐' if positive==9 else
                     '检测未支持；保留待核' if positive==0 else '检测不稳定；保留待核',
            'freshEvidence':chosen,'freshChecks':observations if added else None,
            'machineVerifiedNotHumanConfirmed':True})
    unchanged=snapshot()
    assert protected==unchanged,'读取过程中共享输入变化；本轮应重新定位基线'
    assert view.collision_groups(4,True)==groups
    assert all(r['afterPreferred']==r['beforePreferred'] for r in records if r['beforePreferred'])
    changed=[r for r in records if r['newRecommendation']]
    before=burden([r['beforeBurden'] for r in records]);after=burden([r['afterBurden'] for r in records])
    report={'version':'chvc-post-intake-20261024-v1','runTime':datetime.now().astimezone().isoformat(),
            'scope':'当前排他工作视图；固定同一1554字；比较首选查找负担，非原始重码人数下降',
            'sourceIndexSHA256':overview.INDEX_SHA,'intake':dict(Counter(r['firstKey'] for r in overview.exclusive_intake().values())),
            'topGroups':groups[:30],'cohort':len(records),'before':before,'after':after,
            'existingPreferred':sum(bool(r['beforePreferred']) for r in records),
            'newRecommendations':len(changed),'afterPreferred':sum(bool(r['afterPreferred']) for r in records),
            'fallbackBefore':sum(not r['beforePreferred'] for r in records),
            'fallbackAfter':sum(not r['afterPreferred'] for r in records),
            'triage':dict(Counter(r['triage'] for r in records)),
            'newRecommendationDistribution':dict(Counter(r['afterCode'] for r in changed)),
            'rawChvcBefore':counts['chvc'],'rawChvcAfter':counts['chvc'],
            'newBindings':False,'addedPaths':0,'removedPaths':0,'runtimeIntegrated':False,
            'runtimeDeployed':False,'humanIndividuallyConfirmed':False,
            'validation':{'freshGlyphs':fresh,'freshVariants':fresh*9,'cohortIdentityPreserved':True,
                'allCurrentPreferencesPreserved':True,'noTbReentry':not(selected&overview.exclusive_intake().keys()),
                'allRecommendedPathsAlreadyExist':True,'protectedInputsUnchanged':True},
            'protectedHashes':protected,'records':records,
            'limitations':['局部交点九扰动通过不等于整字主族经人工确认。',
                '未获正证据不等于误收，本轮没有任何撤回或删除。',
                '对象选择复用原有body路径和objectId，未发明新对象或键义。',
                '未细分集合内的同形变体，合理同码仍保留。',
                '首选负担为该码全局实际候选数，不是只统计本组人数；不推定候选排名。',
                '旧报告数字属于快照；当前支持数若混合中心与粗笔证据，不能视为同口径交点统计。']}
    OUTPUT.mkdir()
    save(OUTPUT/'诊断与结构推荐.json',report)
    save(OUTPUT/'新增推荐覆盖层.json',{'active':False,'scope':'recommendation-only; no query filtering',
        'sourceIndexSHA256':overview.INDEX_SHA,'intakeSHA256':digest(PROJECT/'原型/键位编辑器/data/pictorial-exclusive-allocation.json'),
        'records':[{'cp':r['cp'],'preferredCodes':r['afterPreferred'],'evidence':r['freshEvidence']} for r in changed]})
    rows=[]
    for r in records:
        glyph=html.escape(r['char'])
        rows.append(f'<tr><td>U+{r["cp"]:04X}</td><td style="font-family:{html.escape(r["font"]["family"])};font-size:28px">{glyph}</td><td>{r["beforeCode"]}</td><td>{r["beforeBurden"]}</td><td>{r["afterCode"]}</td><td>{r["afterBurden"]}</td><td>{r["triage"]}</td></tr>')
    content=f'''<!doctype html><meta charset="utf-8"><title>chvc 扣除t/b后结构推荐独立实验</title>
<style>body{{font:16px system-ui;margin:24px}}table{{border-collapse:collapse}}th,td{{padding:6px 12px;border:1px solid #ccc}}th{{position:sticky;top:0;background:#eee}}</style>
<h1>chvc：固定1554字的结构推荐</h1><p>新增推荐 {len(changed)} 字；保留全部既有路径和推荐。原始重码仍为1554，不代表人工逐字确认或已经接入。</p>
<p>平均查找负担 {before['mean']} → {after['mean']}；中位数 {before['median']} → {after['median']}；P90 {before['p90']} → {after['p90']}。</p>
<p>逐码说明：c＝辐射骨架·纵长；h＝分叉；原码v＝纵长、c＝中尺寸。推荐m＝真实分叉交点，第四位w上／s下／a左／d右／j左上／k右上／n左下／m右下；k＝分离部件组，第四位b两个／t三个／h左右排列／i上下排列；z＝共享侧干连接横笔组，b两横／t三横；t＝外部点块，y＝外部线状构件，第四位为相同位置方向。键义沿用原试验定义，具体对象见JSON evidence。</p>
<table><thead><tr><th>码位</th><th>字形（原字体）</th><th>原首选或回退</th><th>候选</th><th>实验建议</th><th>候选</th><th>状态</th></tr></thead><tbody>{''.join(rows)}</tbody></table>'''
    (OUTPUT/'逐字比较.html').write_text(content,encoding='utf-8')
    summary=f'''# chvc 扣除t／b后诊断与结构推荐

- 运行时间：{report['runTime']}。
- 当前最大组chvc：1554字；其次chec1421、chvg/chvi各1364。t3630、b732排他名单未变。
- 固定1554字：既有推荐{report['existingPreferred']}字保持；新增{len(changed)}字结构推荐；回退{report['fallbackBefore']}→{report['fallbackAfter']}。
- 全局实际首选候选负担：平均{before['mean']}→{after['mean']}；中位数{before['median']}→{after['median']}；P90 {before['p90']}→{after['p90']}；最大值1554→1554。原始chvc仍1554字。
- 新鲜复验{fresh}字×9扰动，推荐必须已有路径、相同对象并满足原结构校验。全部既有推荐、身份、路径及排他名单不变。

具体问题：尺寸/比例描述造成大组，已有粗笔正证据尚未用于结构推荐重算。此次只补推荐，不删除检测未支持字、不按区块或名称分桶，不隐去候选。存在局部分叉并不保证整字主族正确；检测错误与对象选择问题继续按逐字证据核查。合理同码与同形变体保留。候选展示只提供独立逐字比较，不能宣称已经降重或人工确认。

## 总控接续

本目录“新增推荐覆盖层.json”为active=false的独立建议，只含新增项；原详情与路径仍为权威来源。总控如接入，需协调shape_overview.py及总览前端，保留562个当前已有推荐、全部候选及t/b排他，按当前名单复算；本轮未修改公共文件。若任何输入哈希改变，应重新诊断而非直接套用此静态人数。

未完成：其余回退字符的可靠对象提取与取形边界审议；本轮未新增键义、未调整中心阈值、未部署小狼毫或推送Git。机器通过不等于人工逐字确认。
'''
    (OUTPUT/'总控接续.md').write_text(summary,encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in ('records','protectedHashes','limitations')},ensure_ascii=False),flush=True)
    return report


if __name__=='__main__':build()
