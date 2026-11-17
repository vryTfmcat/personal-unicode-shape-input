"""Bind accepted whole-glyph collections; retain every previous route and preference."""
import hashlib
import json
import os
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(PROJECT / '原型/键位编辑器'), str(PROJECT / '工具')]
import shape_overview as so
from shape_structure_scope import check_scope, load_facts

OUT = so.RUNS / '20261024-structure-count-bindings-v3'
DATA = PROJECT / '原型/键位编辑器/data/structure-count-bindings.json'
FEATURES = {'a': ('corners', '整字角点集'), 'b': ('forks', '整字三叉点集'),
            'g': ('crosses', '整字四叉点集'), 'j': ('straightStrokes', '整字直连续笔集'),
            'q': ('curveStrokes', '整字曲连续笔集')}
COUNTS = {1: 'u', 2: 'b', 3: 't', 4: 'y', 5: 'p'}


def whole_curve_scope(row):
    """A legacy hook lookup is not proof of a complete single-curve glyph."""
    stats = row['statistics'] or {}
    parts = row.get('scopeEvidence', {}).get('inkComponents')
    reasons = []
    if parts != 1:
        reasons.append('基准原墨迹并非单一连通部件，或部件证据缺失')
    if stats.get('strokeCount') != 1 or stats.get('curveStrokes') != 1:
        reasons.append('整字不是一条连续曲笔')
    if stats.get('straightStrokes', 0):
        reasons.append('另有直连续笔')
    if any(stats.get(k, 0) for k in ('forks', 'crosses', 'otherJunctions')):
        reasons.append('存在叉交或多出口')
    if stats.get('loops', 0):
        reasons.append('有闭孔，不是完整开口单曲线')
    return not reasons, reasons


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def write(p, value):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def write_review(report, publish=True):
    page = '''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>大组结构新键位分配</title><style>body{font:16px system-ui;margin:24px;background:#f5f6f8;color:#172b3a}main{max-width:1320px;margin:auto}h1{font-size:26px}input,select,button{font:inherit;padding:8px;max-width:100%;box-sizing:border-box}nav{display:flex;gap:8px;flex-wrap:wrap;margin:16px 0}.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:12px}.card{background:white;padding:12px;border:1px solid #ccd5dc;border-radius:8px;overflow-wrap:anywhere}.glyph{width:64px;height:64px;display:block;background-repeat:no-repeat}code{background:#edf2f7;padding:2px;display:inline-block}small{display:block;line-height:1.7}#comparison{line-height:1.8}summary{cursor:pointer}pre{white-space:pre-wrap;overflow-wrap:anywhere}a{color:#126395}button{cursor:pointer}@media(max-width:400px){body{margin:12px}.grid{grid-template-columns:1fr}}</style>
<main><a href="shape-key-overview.html#round=3">四位键位总览</a><h1>大组结构新键位分配</h1><p id="summary"></p>
<p>当前结构计数工作版本已接受并合并到四位键位总览：第三位 a角点／b三叉／g四叉／j直连续笔／q曲连续笔；第四位 u一／b二／t三／y四／p五及以上。整字集合计数；原码和原首选保留，未部署。</p>
<p>ajqu已由本人审阅接受。其他新前缀已检查整字／局部范围及必要结构条件；局部、待核依据和明确矛盾者退出新入口，原码保留。本次接受当前工作版本，不等于逐字人工确认。程序待核项由程序继续排查，无需您逐字审核；需要人工判断的语义边界将另列具体问题。九扰动稳定不等于分类正确。点群不根据细化骨架派生线码；闭轮廓、开口曲线、线组及叉交分别检查。</p>
<nav><select id="group"><option value="">全部55个原大组</option></select><select id="status"><option value="">全部状态</option><option value="assigned">已分配新码</option><option value="pending">程序待核／原入口保留</option><option value="withdrawn">本轮退出新入口</option></select><input id="search" placeholder="字符、U+0054或新四码"><button id="reset">重置</button></nav>
<p id="comparison"></p><p id="count" role="status"></p><div id="grid" class="grid"></div><nav><button id="prev">上一页</button><span id="page"></span><button id="next">下一页</button></nav>
<details><summary>范围、数量与证据边界</summary><p>只有九扰动稳定且线模型适用的观测才生成新码；新字母规则已接受，机器应用不等于逐字人工确认。五以上合并，不推断未观测字符具有零个对象。旧首选不因候选更少被自动覆盖。</p><pre id="scope"></pre></details></main>
<script>const DATA=__DATA__;
const $=id=>document.getElementById(id),esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));let offset=0;
const index=new Map(DATA.records.map(r=>[r.cp,r]));
$('summary').textContent=`已观测 ${DATA.statistics.observed} 字；已分配 ${DATA.statistics.assigned} 字／${DATA.statistics.newCodes} 个新四码／${DATA.statistics.newCharacterCodePairs} 条新增路径；${DATA.statistics.pending} 字暂无本轮新码（含已确认保留原查法者）。`;
$('group').innerHTML+=DATA.groups.map(g=>`<option value="${g.code}">${g.code} · ${g.before} 字</option>`).join('');
$('scope').textContent=JSON.stringify(DATA.prefixScope,null,2);
function render(reset=true){if(reset)offset=0;const g=DATA.groups.find(g=>g.code===$('group').value),s=$('status').value,q=$('search').value.trim();let rows=g?g.recommendations.map(r=>index.get(r.cp)):DATA.records;
const usable=r=>g?r.codes.some(c=>c.startsWith(g.code.slice(0,2))):r.codes.length>0;
if(s==='withdrawn')rows=rows.filter(r=>r.withdrawnCodes.some(c=>!g||c.startsWith(g.code.slice(0,2))));
else if(s)rows=rows.filter(r=>Boolean(usable(r))===(s==='assigned'));
if(q){const m=/^(?:U\\+|0x)?([0-9A-F]{4,6})$/i.exec(q);rows=rows.filter(r=>m?r.cp===parseInt(m[1],16):r.char===q||r.codes.includes(q.toLowerCase()));}
$('comparison').textContent=g?`原 ${g.code} ${g.before} 字全部保留；${g.withBetterRoute} 字取得更小的新入口；${g.pending} 字待核。推荐后最大查找负担 ${g.maxRecommendedBurden}，中位 ${g.medianRecommendedBurden}。`:'';
$('count').textContent=`${rows.length} 个去重字符`;
$('grid').innerHTML=rows.slice(offset,offset+60).map(r=>`<article class="card"><span class="glyph" style="${r.preview?`background-image:url('${r.preview.url}');background-position:-${r.preview.x}px -${r.preview.y}px`:''}"></span><strong>${esc(r.char)} U+${r.cp.toString(16).toUpperCase()}</strong><small>${r.pFamilyBoundaryReview?'p族本批答复：'+esc(r.pFamilyBoundaryReview.note)+'；计数仍待另验':usable(r)?(r.acceptedBoundary?'本字整字形族已人工确认，计数沿用观测':r.codes.includes('ajqu')?'ajqu已审阅；其它入口待审':'机器已分配；语义待审'):r.reviewResolution==='confirmed-circle-subject-retain-existing-routes'?'已确认保留圆主体原查法；不套整字计数':r.acceptedBoundary?'本字新形族已确认；此旧形族不派新计数':'程序待核；原入口保留，无需逐字审核'} · ${r.status==='stable'?'九扰动数值稳定':esc(({unstable:'检测结果不稳定', 'topology-pending':'拓扑检测待核', 'pairing-pending':'接续配对待核', 'filled-face':'实心面模型待核', 'no-line':'未提取可靠线条', error:'检测异常'})[r.status]||r.status)}</small>${r.codes.map(c=>`<button data-code="${c}"><code>${c}</code> · ${DATA.codeCounts[c]} 候选</button>`).join(' ')}${r.withdrawnCodes?.length?'<small>本轮退出：'+r.withdrawnCodes.map(esc).join(' ')+'</small>':''}${r.scopeRejections?.length?'<small>新入口范围收紧：'+r.scopeRejections.map(x=>esc(x.prefix)+' '+x.reasons.map(esc).join('；')).join('／')+'</small>':''}<small>原首选：${esc(r.oldPreferredCodes.join(' ')||'未设置（无需补填）')}</small><details><summary>计数与原码</summary><pre>${esc(JSON.stringify({statistics:r.statistics,oldCodes:r.oldCodes,assignments:r.assignments},null,2))}</pre></details></article>`).join('');
$('page').textContent=rows.length?`${offset+1}–${Math.min(offset+60,rows.length)} / ${rows.length}`:'0 / 0';$('prev').disabled=!offset;$('next').disabled=offset+60>=rows.length;
}
for(const id of ['group','status'])$(id).onchange=()=>render();$('search').oninput=()=>render();$('reset').onclick=()=>{$('group').value='';$('status').value='';$('search').value='';render();};$('prev').onclick=()=>{offset-=60;render(false);};$('next').onclick=()=>{offset+=60;render(false);};$('grid').onclick=e=>{const b=e.target.closest('[data-code]');if(b){$('group').value='';$('status').value='';$('search').value=b.dataset.code;render();}};$('search').value=new URLSearchParams(location.search).get('code')||'';$('status').value=new URLSearchParams(location.search).get('status')||'';render();</script></html>'''
    slim = {k: report[k] for k in ('statistics', 'groups', 'prefixScope')}
    slim['codeCounts'] = {c: len(v) for c, v in report['codeMembers'].items()}
    slim['records'] = [{k: r[k] for k in ('cp', 'char', 'status', 'codes', 'oldCodes', 'oldPreferredCodes', 'preview', 'statistics', 'assignments', 'scopeRejections')} for r in report['records']]
    withdrawn = {r['cp']: r['codes'] for r in report['scopeRevision']['withdrawn']}
    full_index = {r['cp']: r for r in report['records']}
    for r in slim['records']:
        r['acceptedBoundary'] = full_index[r['cp']].get('acceptedBoundary')
        r['reviewResolution'] = full_index[r['cp']].get('reviewResolution')
        r['withdrawnCodes'] = sorted(set(withdrawn.get(r['cp'], [])) | set(full_index[r['cp']].get('withdrawnPWholeCodes', [])))
        r['pFamilyBoundaryReview'] = report.get('pFamilyBoundaryReview', {}).get('decisions', {}).get(str(r['cp']))
    if report.get('kFamilyScopeAcceptance'):
        page=page.replace('原码和原首选保留，未部署。','原首选保留；旧码按已确认清单局部撤回，历史对照保留。未部署小狼毫。')
        page=page.replace('原 ${g.code} ${g.before} 字全部保留；','冻结原组 ${g.code} ${g.before} 字（现行旧路可有已确认撤回，当前人数看四位总览）；')
        version=report['version'].rsplit('-',1)[-1]
        page=page.replace('<p id="summary"></p>','<p id="summary"></p><p>当前为结构计数'+version+'；新计数人数取当前去重并集。下列旧码、原组人数和范围表保留历史基线，不当作现行旧码全部可达的声明。</p>')
    if report.get('countSemanticsVersion')=='whole-continuous-total-v1':
        page=page.replace('j直连续笔／q曲连续笔','j含直入口／q含曲入口')
        page=page.replace('整字集合计数；','j/q第四位统一数同一整字直曲总集合；a/b/g计数原义不变；')
        page=page.replace('新字母规则已接受，机器应用不等于逐字人工确认；','全局直曲总数规则及精确迁移已接受，机器应用不等于逐字人工确认；')
        page=page.replace('旧入口保留','非计数旧入口保留；旧j/q分项数量路按清单撤换')
        page=page.replace('<p id="summary"></p>','<p id="summary"></p><p>whole-continuous-total-v1：791条字码关系撤换，1139条字符串不变；原首选和非计数例外保护。旧v9仅为历史，不混入当前候选。</p>')
    page = page.replace('__DATA__', json.dumps(slim, ensure_ascii=False).replace('</', '<\\/'))
    editor = PROJECT / '原型/键位编辑器'
    if publish:
        (editor / 'structure-count-review.html').write_text(page, encoding='utf-8')
    base = os.path.relpath(editor, OUT).replace('\\', '/') + '/'
    (OUT / '新键位分配审阅.html').write_text(page.replace('<title>', '<base href="' + base + '"><title>', 1), encoding='utf-8')


def build():
    if DATA.is_file() and so.read(DATA).get('version') not in (None,'structure-count-bindings-v1','structure-count-bindings-v2','structure-count-bindings-v3'):
        raise RuntimeError('当前已有受保护确认版本；禁止用v3生成器覆盖，请按当前版本使用对应确认源生成器')
    sources = [so.RUNS / '20261024-other-large-collisions-v1/其他大组分析.json',
               so.RUNS / '20261024-stroke-continuation-trial-v1/分类数据.json']
    other, chvc = map(so.read, sources)
    protected = [so.RUN / '发布核对索引.json', PROJECT / '数据/三模式/全形核对版.json',
                 PROJECT / '原型/键位编辑器/data/pictorial-exclusive-allocation.json',
                 PROJECT / '原型/键位编辑器/data/shape-review-profile.json']
    hashes = {str(p.relative_to(PROJECT)): sha(p) for p in sources + protected}
    rows = {r['cp']: dict(r, source='other') for r in other['records']}
    for r in chvc['records']:
        if r['cp'] in rows:
            assert rows[r['cp']]['statistics'] == r['statistics']
        else:
            rows[r['cp']] = dict(r, source='chvc')
    assert len(rows) == 11061 and not rows.keys() & so.exclusive_intake().keys()
    overview = so.get_overview()
    facts = load_facts(overview, {cp for cp, r in rows.items() if r['status'] == 'stable'})
    scopes = {g['code']: set(g['cps']) for g in other['groups']}
    scopes['chvc'] = {r['cp'] for r in chvc['records']}
    for code, cps in scopes.items():
        assert set(overview.allocation_members(code)) == cps, ('stale scope', code)
    members = defaultdict(set)
    records = []
    for cp, r in sorted(rows.items()):
        old = overview.brief(cp, True)
        old_codes = [c for c in old['codes'] if len(c) < 3 or c[2] not in FEATURES]
        prefixes = sorted({c[:2] for c in old_codes if len(c) >= 3})
        stats = r['statistics']
        eligible = r['status'] == 'stable'
        assignments = []
        scope_rejections = []
        if eligible:
            assert stats and stats['uncertainStrokes'] == 0 and stats['otherJunctions'] == 0
            for prefix in prefixes:
                assert cp in overview.allocation_members(prefix)
                if prefix[1] == 'j':
                    passed, reasons = whole_curve_scope(r)
                else:
                    passed, reasons = check_scope(prefix, r, facts[cp])
                if not passed:
                    scope_rejections.append(dict(prefix=prefix, reasons=reasons))
                    continue
                for key, (field, meaning) in FEATURES.items():
                    n = stats[field]
                    if not n:
                        continue
                    code = prefix + key + COUNTS[min(n, 5)]
                    assignments.append(dict(code=code, feature=field, meaning=meaning, count=n,
                                            objectId='whole-glyph-collection:' + field,
                                            scope='整字原墨迹；非原形族的局部对象', variants=9))
                    members[code].add(cp)
        records.append(dict(cp=cp, char=chr(cp), status=r['status'], eligible=eligible,
                            source=r['source'], oldCodes=old_codes, oldPreferredCodes=old['preferredCodes'],
                            codes=sorted(a['code'] for a in assignments), assignments=assignments,
                            statistics=stats, preview=old.get('preview'),
                            scopeRejections=scope_rejections,
                            wholeRouteFacts=facts.get(cp),
                            proof=r.get('proof', r.get('continuation'))))
    index = {r['cp']: r for r in records}
    groups = []
    for code, cps in scopes.items():
        recommended = []
        for cp in sorted(cps):
            options = [c for c in index[cp]['codes'] if c[:2] == code[:2]]
            best = min(options, key=lambda c: (len(members[c]), c)) if options else None
            recommended.append(dict(cp=cp, code=best if best and len(members[best]) < len(cps) else code,
                                    burden=min(len(members[best]), len(cps)) if best else len(cps)))
        groups.append(dict(code=code, before=len(cps), oldCandidatesRetained=len(cps),
                           stable=sum(index[cp]['eligible'] for cp in cps),
                           pending=sum(not any(c[:2] == code[:2] for c in index[cp]['codes']) for cp in cps),
                           withBetterRoute=sum(r['code'] != code for r in recommended),
                           maxRecommendedBurden=max(r['burden'] for r in recommended),
                           medianRecommendedBurden=sorted(r['burden'] for r in recommended)[len(cps)//2],
                           recommendations=recommended))
    prefix_scope = []
    for prefix in sorted({c[:2] for c in members}):
        full = set(overview.allocation_members(prefix))
        prefix_scope.append(dict(prefix=prefix, currentMembers=len(full), observed=len(full & rows.keys()),
                                 outsideObservedScope=len(full - rows.keys())))
    assert hashes == {str(p.relative_to(PROJECT)): sha(p) for p in sources + protected}
    prior_path = so.RUNS / '20261024-structure-count-bindings-v2/大组结构键位分配.json'
    prior = so.read(prior_path)
    old_sets = {r['cp']: set(r['codes']) for r in prior['records']}
    withdrawn = [dict(cp=r['cp'], char=r['char'], codes=sorted(old_sets[r['cp']] - set(r['codes'])),
                      reasons=[x for x in r['scopeRejections'] if x['prefix'] in
                               {c[:2] for c in old_sets[r['cp']] - set(r['codes'])}])
                 for r in records if old_sets[r['cp']] - set(r['codes'])]
    assert set(members['ajqu']) == set(prior['codeMembers']['ajqu']), '已接受ajqu集合必须保留'
    report = dict(version='structure-count-bindings-v3', active=True, runtimeDeployed=False,
                  createdAt=datetime.now(timezone.utc).isoformat(), sourceIndexSHA256=so.INDEX_SHA,
                  authorization='好的，采用这个方案重新对大重码组进行键位分配',
                  definitions=dict(third={k: dict(meaning=v[1], feature=v[0], status='accepted-independent-trial',
                                                  condition='整字集合；九扰动稳定且线模型适用，零值及待核不生成码') for k, v in FEATURES.items()},
                                   fourth={k: dict(meaning=('五个及以上' if n == 5 else ['','一个','两个','三个','四个'][n]),
                                                   status='accepted-independent-trial') for n, k in COUNTS.items()}),
                  statistics=dict(observed=len(records), assigned=sum(bool(r['codes']) for r in records),
                                  pending=sum(not r['codes'] for r in records),
                                  observationPending=sum(not r['eligible'] for r in records),
                                  wholeScopePending=sum(r['eligible'] and not r['codes'] for r in records),
                                  newCharacterCodePairs=sum(len(r['codes']) for r in records),
                                  newCodes=len(members), removedPaths=0, changedPreferences=0, tBReentry=0,
                                  withdrawnNewPaths=sum(len(r['codes']) for r in withdrawn)),
                  scopeRevision=dict(previousReportSHA256=sha(prior_path),
                                     reason='推广整字范围与形族必要条件；ajqu已接受集合保留',
                                     wholeCharacterHumanConfirmed=False, withdrawn=withdrawn),
                  codeMembers={c: sorted(v) for c, v in sorted(members.items())},
                  groups=groups, prefixScope=prefix_scope, protectedHashes=hashes, records=records)
    write(OUT / '大组结构键位分配.json', report)
    write(DATA, {k: report[k] for k in ('version', 'active', 'runtimeDeployed', 'sourceIndexSHA256', 'definitions', 'statistics', 'codeMembers')} |
          {'records': [{k: r[k] for k in ('cp', 'codes', 'assignments')} for r in records if r['codes']]})
    lines = ['# 大组结构键位分配', '', '已接受独立工作视图绑定；未部署。原码、原首选、t／b排他均保留。',
             '五类整字对象：a角点／b三叉／g四叉／j直连续笔／q曲连续笔；第四位u一／b二／t三／y四／p五及以上。',
             '范围为55个原大组的去重并集；未观测的前缀成员不推断为零。贯通与闭孔不新增键义。', '',
             json.dumps(report['statistics'], ensure_ascii=False), '',
             '| 原码 | 原候选（保留） | 有更小新入口 | 待核 | 推荐后最大查找负担 | 推荐后中位负担 |',
             '| --- | ---: | ---: | ---: | ---: | ---: |']
    lines += [f"| {g['code']} | {g['before']} | {g['withBetterRoute']} | {g['pending']} | {g['maxRecommendedBurden']} | {g['medianRecommendedBurden']} |" for g in groups]
    lines += ['', '新码人数按所有已分配组的并集去重计算，而非只统计某个原码的子集。',
              '旧码人数不变，推荐查找负担允许因待核字而保持原最大值。最大稳定联合类不当作四码上限。',
              '完整逐字依据、待核状态、全局候选并集与前缀未观测范围见同目录JSON。']
    (OUT / '大组结构键位分配.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    write_review(report)
    print(json.dumps(report['statistics'], ensure_ascii=False))


if __name__ == '__main__':
    build()
