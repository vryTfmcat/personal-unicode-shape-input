"""Independent post-t/b collision audit; existing paths only, no runtime writes."""
import copy
import hashlib
import html
import json
import math
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from statistics import median

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / '原型/键位编辑器'))
import shape_overview as overview
from audit_shape_chvc_structure import reliable_choices, measurements
from audit_shape_historical_buckets import protect
from shape_experiment_features import observe, render

OUTPUT = overview.RUNS / '20261024-collision-current-v1'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def burden(values):
    values = sorted(values)
    return dict(characters=len(values), median=median(values),
                p90=values[math.ceil(.9 * len(values)) - 1], maximum=max(values),
                atMost20=sum(v <= 20 for v in values), atMost50=sum(v <= 50 for v in values))


def merge_observations(old, thick):
    observations = copy.deepcopy(old['checks'])
    assert len(observations) == len(thick['variants']) == 9
    for obs, variant in zip(observations, thick['variants']):
        assert (obs['size'], obs['weight']) == (variant['size'], variant['weight'])
        obs['visibleForks'] = variant['proofs']
    return observations


def build():
    if OUTPUT.exists():
        raise FileExistsError('已有结果，禁止覆盖')
    protected = protect()
    sources = [overview.CHVC_RUN / 'chvc结构细分与优先级试验.json',
               overview.THICK_RUN / '粗笔分叉误拒复核.json',
               overview.CENTRE_RUN / '中心属性交点试验.json',
               PROJECT / '原型/键位编辑器/data/pictorial-exclusive-allocation.json']
    sources += [PROJECT / '原型/键位编辑器' / n for n in
                ('shape_overview.py', 'shape-key-overview.js', 'shape-key-overview.html')]
    sources += [PROJECT / '工具' / n for n in
                ('shape_recovery_geometry.py', 'audit_shape_chvc_structure.py',
                 'shape_experiment_features.py', 'shape_experiment_rules.py')]
    source_hashes = {str(p.relative_to(PROJECT)): digest(p) for p in sources}
    thick_report = overview.thick_repair()
    assert digest(PROJECT / '工具/shape_recovery_geometry.py') == thick_report['geometryCodeSHA256']
    assert overview.chvc_trial()['sourceIndexSHA256'] == overview.INDEX_SHA
    assert thick_report['sourceIndexSHA256'] == overview.INDEX_SHA
    o = overview.Overview()
    intake = set(overview.exclusive_intake())
    collisions = o.collision_groups(4, True)
    cohort = set(o.allocation_members('chvc'))
    assert collisions[0]['code'] == 'chvc'
    assert not cohort & intake
    counts = {g['code']: g['count'] for g in collisions}
    old = overview.chvc_records()
    thick = overview.thick_records()
    centre = overview.centre_records()
    records = []
    fonts = {}
    for cp in sorted(cohort):
        detail = o.detail(cp, True)
        detail = dict(detail, paths=[p for p in detail['paths'] if len(p['code']) == 4])
        brief = o.brief(cp, True)
        paths = {p['code']: p for p in detail['paths']}
        current = [c for c in brief['preferredCodes'] if len(c) == 4 and c in paths]
        # Preserve every pre-existing structural preference, including manual ones.
        frozen = bool(old[cp]['preferredCodes'] or centre.get(cp, {}).get('preferredCodes')
                      or any(p.get('preferred') and p.get('reviewedPreference') for p in paths.values()))
        observations = merge_observations(old[cp], thick[cp])
        choices = reliable_choices(detail, observations, counts)
        candidate = choices[0] if choices and not frozen and not old[cp]['negativeCertificate'] else None
        fresh = []
        if candidate:
            # Cache evidence is a shortlist only. Re-render every proposed addition.
            for check in observations:
                f = observe(*render(detail['char'], detail['font']['path'], detail['font'].get('index', 0),
                                    size=check['size'], weight=check['weight'], fonts=fonts))
                fresh.append(measurements(f))
            verified = reliable_choices(detail, fresh, counts)
            candidate = next((c for c in verified if c['code'] == candidate['code']), None)
        baseline_code = current[0] if current else 'chvc'
        # Never replace a lower-burden existing default by a worse recommendation.
        accepted = candidate if candidate and counts[candidate['code']] < counts[baseline_code] else None
        recommended = accepted['code'] if accepted else baseline_code
        assert recommended in paths and cp in o.allocation_members(recommended)
        records.append(dict(cp=cp, char=chr(cp), preview=old[cp]['preview'],
                            baselineCode=baseline_code, recommendedCode=recommended,
                            baselineBurden=counts[baseline_code], recommendedBurden=counts[recommended],
                            frozenPreference=frozen, newRecommendation=bool(accepted),
                            evidence=accepted['evidence'] if accepted else [], freshVariantChecks=len(fresh),
                            positiveVariants=thick[cp]['afterPositiveVariants'],
                            negativeCertificate=old[cp]['negativeCertificate'],
                            bodyIsWholeInk=old[cp]['baseline']['bodyIsWholeInk'],
                            originalCodes=brief['codes'], originalPreferredCodes=brief['preferredCodes']))
        if len(records) % 300 == 0:
            print(f'当前chvc复核 {len(records)}/{len(cohort)}', flush=True)
    assert protected == protect()
    assert source_hashes == {str(p.relative_to(PROJECT)): digest(p) for p in sources}
    assert cohort == {r['cp'] for r in records}
    additions = [r for r in records if r['newRecommendation']]
    stats = dict(cohort=len(cohort), tBExcluded=len(intake),
                 historicalChvc=len(o.layers.entries['chvc']), currentChvc=counts['chvc'],
                 newRecommendations=len(additions), frozenPreferences=sum(r['frozenPreference'] for r in records),
                 positiveVariantDistribution=dict(Counter(str(r['positiveVariants']) for r in records)),
                 baseline=burden([r['baselineBurden'] for r in records]),
                 experiment=burden([r['recommendedBurden'] for r in records]),
                 changedBefore=burden([r['baselineBurden'] for r in additions]) if additions else None,
                 changedAfter=burden([r['recommendedBurden'] for r in additions]) if additions else None)
    report = dict(version='collision-current-v1', runTime=datetime.now().astimezone().isoformat(),
                  statistics=stats, collisions=collisions, records=records,
                  sourceHashes=source_hashes, protectedHashes=protected,
                  scope='现行t/b排他视图；只新增查法建议，所有候选及路径保持原样；非人工逐字确认',
                  noRuntimeWrites=True, newBindings=False, newPaths=0, removedPaths=0,
                  integration=['总控可审阅后接入独立建议；涉及shape_overview.py/总览前端，尚未实施'],
                  unresolved='0/9与部分检出仅作待核；局部分叉不等于整字主族；同形Unicode身份允许同码')
    OUTPUT.mkdir()
    (OUTPUT / '当前重码诊断与建议.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    make_preview(records, stats)
    print(json.dumps(stats, ensure_ascii=False), flush=True)
    return report


def make_preview(records, stats):
    from PIL import Image, ImageDraw, ImageFont
    additions = [r for r in records if r['newRecommendation']]
    selected = additions[:48]
    image = Image.new('RGB', (1000, 40 + max(1, math.ceil(len(selected) / 8)) * 110), 'white')
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype('C:/Windows/Fonts/msyh.ttc', 13)
    draw.text((8, 8), 'chvc已有对象细码：独立建议／非逐字人工确认；原候选保留', font=font, fill='black')
    sprites = {}
    for i, r in enumerate(selected):
        p = r['preview']; source = PROJECT / '原型/键位编辑器' / p['url']
        if source not in sprites:
            sprites[source] = Image.open(source).convert('RGB')
        x, y = 8 + i % 8 * 124, 36 + i // 8 * 110
        image.paste(sprites[source].crop((p['x'], p['y'], p['x'] + 64, p['y'] + 64)), (x, y))
        draw.text((x, y + 64), f'U+{r["cp"]:04X} {r["recommendedCode"]}', font=font, fill='black')
        draw.text((x, y + 83), f'{r["baselineBurden"]} → {r["recommendedBurden"]}', font=font, fill='#245c50')
    image.save(OUTPUT / '新增建议预览.png')
    rows = []
    for r in sorted(records, key=lambda r: (not r['newRecommendation'], r['cp'])):
        p = r['preview']; uri = (PROJECT / '原型/键位编辑器' / p['url']).as_uri()
        glyph = f'<span class="glyph" style="background-image:url({html.escape(uri)});background-position:-{p["x"]}px -{p["y"]}px"></span>'
        status = '新增建议，九扰动重渲染' if r['newRecommendation'] else '保留既有偏好' if r['frozenPreference'] else '待核，全部保留'
        rows.append(f'<tr><td>{glyph}U+{r["cp"]:04X}</td><td>{r["baselineCode"]} ({r["baselineBurden"]})</td><td>{r["recommendedCode"]} ({r["recommendedBurden"]})</td><td>{status}</td><td>{r["positiveVariants"]}/9</td></tr>')
    page = '<!doctype html><meta charset="utf-8"><title>当前大重码专项实验</title><style>body{font-family:system-ui;margin:24px}td,th{padding:8px;border-bottom:1px solid #ddd;text-align:left}.glyph{display:inline-block;width:64px;height:64px;vertical-align:middle}table{border-collapse:collapse}</style><h1>chvc 已有结构码建议实验</h1><p>独立只读报告；所有1554字保留。原候选量未下降，新增建议尚未接入总览。机器证据不等于人工确认。</p><pre>' + html.escape(json.dumps(stats, ensure_ascii=False, indent=2)) + '</pre><table><thead><tr><th>锁定原字形</th><th>原推荐及候选量</th><th>实验推荐及全量候选量</th><th>状态</th><th>局部分叉支持</th></tr></thead><tbody>' + ''.join(rows) + '</tbody></table>'
    (OUTPUT / '当前重码审阅.html').write_text(page, encoding='utf-8')


if __name__ == '__main__':
    build()
