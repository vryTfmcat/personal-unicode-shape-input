"""Fixed-cohort structural experiment; never rewrites a published codebook."""
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
from statistics import median

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from audit_shape_historical_buckets import SOURCE, PROJECT, protect, load
from build_shape_keyboard_full import save
from shape_collision_sanity import contradiction
from shape_experiment_features import observe, render, component_mask, filled, bounds, normalized
from shape_keyboard_trial import group_object
from shape_lab_features import components
from shape_recovery_geometry import visible_fork
from shape_stroke_groups import horizontal_stroke_group
from shape_experiment_rules import position
from shape_reviewed_components import cycle_subject
from shape_reviewed_routes import references

OUTPUT = SOURCE.parent / '20261022-chvc-structure-trial-v1'
FEATURES = {'holes': '整字闭孔数', 'parts': '整字分离墨块数',
            'attachments': '已提取外附件类型及方向', 'bars': '连接横笔组数量'}
UNKNOWN = '未稳定提取'
SIZES = (48, 96, 128)
WEIGHTS = (-1, 0, 1)
_TEMPLATES = None


def templates():
    global _TEMPLATES
    if _TEMPLATES is None:
        _TEMPLATES = references(Path('C:/Windows/Fonts/seguisym.ttf'))
    return _TEMPLATES


def count_band(n):
    return str(n) if n < 4 else '4+'


def direction(x, y, box):
    cx, cy = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
    span = max(box[2] - box[0], box[3] - box[1])
    dx, dy = x - cx, y - cy
    a = '左' if dx < -.15 * span else '右' if dx > .15 * span else ''
    b = '上' if dy < -.15 * span else '下' if dy > .15 * span else ''
    return b + a or '中心'


def attachment_objects(f):
    """Only real separated exterior satellites, not every skeletal branch."""
    parts = f['parts']
    if len(parts) < 2:
        return []
    main = max(parts, key=lambda p: p['area'])
    if main['area'] < .70 * sum(p['area'] for p in parts):
        return []
    box = [main[k] for k in ('x0', 'y0', 'x1', 'y1')]
    result = []
    for p in parts:
        if p is main:
            continue
        b = [p[k] for k in ('x0', 'y0', 'x1', 'y1')]
        if not (b[2] <= box[0] or b[0] >= box[2] or b[3] <= box[1] or b[1] >= box[3]):
            continue
        w, h = b[2] - b[0], b[3] - b[1]
        mask = component_mask(f['mask'], p)
        if filled(mask).sum() > mask.sum() * 1.08:
            continue
        kind = ('点' if .5 <= w / h <= 2 and p['area'] / (w*h) >= .50 else
                '笔' if max(w/h, h/w) >= 3 and p['area'] / (w*h) >= .55 else None)
        if kind:
            result.append({'kind': kind, 'direction': direction(p['cx'], p['cy'], box),
                           'bbox': b, 'pixels': p['area'], 'referenceBBox': box})
    return result


def attached_tail(f):
    """Reuse the existing ring/tail ink partition, with roundness and extension gates."""
    if len(f['holes']) != 1:
        return None
    part = cycle_subject(f)
    if part is None:
        return None
    ring, tail, proof = part
    error = float(np.min(np.mean((templates()['familyViews']['o']-normalized(ring['silhouette']))**2,axis=(1,2))))
    box, tb = ring['bbox'], bounds(tail)
    span = max(box[2]-box[0],box[3]-box[1])
    extends = max(box[0]-tb[0],box[1]-tb[1],tb[2]-box[2],tb[3]-box[3])
    if error > .035 or extends < max(3, .12*span) or tail.sum() < max(5,.03*f['body'].sum()):
        return None
    return {'kind':'尾','direction':direction((tb[0]+tb[2])/2,(tb[1]+tb[3])/2,box),
            'bbox':tb,'referenceBBox':box,'pixels':int(tail.sum()),'partitionProof':proof,
            'roundPrototypeError':error}


def measurements(f):
    # Explicit whole-ink topology avoids observe()'s automatic subject selection.
    holes = [h for h in components(~np.pad(f['mask'], 1), 4) if not h['edge'] and h['area'] >= 5]
    attachments = attachment_objects(f)
    tail=attached_tail(f)
    if tail:attachments.append(tail)
    for a in attachments:
        b=f['bbox'];scale=max(b[2]-b[0],b[3]-b[1]);ab=a['bbox']
        a['positionKey']=position((ab[0]+ab[2]-b[0]-b[2])/(2*scale),
                                   (ab[1]+ab[3]-b[1]-b[3])/(2*scale),0,0)
    bars = horizontal_stroke_group(f)
    b=f['bbox']; scale=max(b[2]-b[0],b[3]-b[1])
    visible = [dict(index=i, positionKey=position((j['x0']+j['x1']-b[0]-b[2])/(2*scale),
                                                 (j['y0']+j['y1']-b[1]-b[3])/(2*scale),0,0), **proof) for i, j in enumerate(f['junctionObjects'])
               if (proof := visible_fork(f, j, (3, 4)))]
    tokens = {'holes': count_band(len(holes)), 'parts': count_band(len(f['parts'])),
              'attachments': '、'.join(sorted({o['kind'] + o['direction'] for o in attachments})) or UNKNOWN,
              'bars': str(bars['object']['memberCount']) if bars else UNKNOWN}
    return {'values': tokens, 'exactHoleCount': len(holes), 'exactPartCount': len(f['parts']),
            'attachments': attachments, 'bars': bars['proof'] if bars else None,
            'group': group_object(f) if len(f['parts']) > 1 else None,
            'visibleForks': visible, 'bodyBBox': f['bbox'], 'bodyIsWholeInk': bool(np.array_equal(f['mask'], f['body'])),
            'negative': contradiction(f, 'h')}


def stable_value(observations, feature):
    values = [o['values'][feature] for o in observations]
    return values[0] if len(set(values)) == 1 else UNKNOWN


def bbox_close(a, b, tolerance=5):
    return a is not None and b is not None and max(abs(x-y) for x, y in zip(a, b)) <= tolerance


def reliable_choices(row, observations, code_counts):
    """Rank only extant, object-matched structural paths, never size/PCA paths."""
    objects = {o['id']: o for o in row['objects']}
    routes = {(r['bucket'] + r['familyKey'], r['target']): r for r in row['familyRoutes']}
    choices = []
    for path in row['paths']:
        code = path['code']
        if code == 'chvc' or code_counts[code] >= code_counts['chvc']:
            continue
        accepted = []
        for e in path['evidence']:
            route = routes[(code[:2], e['familyTarget'])]
            if code[:2] != 'ch' or route['target'] != 'body':
                continue
            o = objects[e['objectId']]
            if e['rule'] == 'component.connected_horizontal_group' and code[-1] in 'bt':
                n = o.get('memberCount')
                good = all(v['bars'] and v['bars']['memberCount'] == n
                           and bbox_close(o['bbox'], [min(b[0] for b in v['bars']['memberBBoxes']),
                                                     min(b[1] for b in v['bars']['memberBBoxes']),
                                                     max(b[2] for b in v['bars']['memberBBoxes']),
                                                     max(b[3] for b in v['bars']['memberBBoxes'])]) for v in observations)
                reason = '九扰动一致的连接横笔组数量'
            elif e['rule'] == 'skeleton.branch' and code[-1] in 'wsadjknm':
                b = o['bbox']
                cx, cy = (b[0]+b[2]-1)/2, (b[1]+b[3]-1)/2
                good = all(any(abs(p['centre'][0]-cx) <= 5 and abs(p['centre'][1]-cy) <= 5
                                   and p['armCount'] in (3,4) for p in v['visibleForks']) for v in observations)
                # The direction code must survive, not merely the presence of a fork.
                good = good and all(any(abs(p['centre'][0]-cx) <= 5 and abs(p['centre'][1]-cy) <= 5
                                       and p['positionKey'] == code[-1]
                                       for p in v['visibleForks']) for v in observations)
                reason = '九扰动一致的真实交点位置；不区分T/Y支臂式样'
            elif e['rule'] == 'topology.separated' and code[-1] in 'bthi':
                good = all(v['group'] and v['group']['memberCount'] == o.get('memberCount')
                           and bbox_close(v['group']['bbox'],o['bbox'])
                           and (code[-1] not in 'hi' or v['group'].get('arrangement') == code[-1]) for v in observations)
                good = good and all(v['visibleForks'] for v in observations)
                reason = '九扰动一致的完整分离构件组，且分叉入口有正证据'
            elif code[2] in 'ty' and code[-1] in 'wsadjknm':
                kind = '点' if code[2] == 't' else '笔'
                good = all(any(a['kind'] == kind and a['positionKey']==code[-1] and bbox_close(a['bbox'], o['bbox']) for a in v['attachments'])
                           and v['visibleForks'] for v in observations)
                reason = '九扰动一致的原墨迹外附件；分叉入口有正证据'
            else:
                continue
            if good:
                accepted.append({'objectId': o['id'], 'rule': e['rule'], 'reason': reason})
        if accepted:
            choices.append({'code': code, 'allCandidatesV14': code_counts[code], 'evidence': accepted,
                            'wasPreferred': path.get('preferred', False)})
    # Keep an established specific preference when valid; otherwise minimize actual lookup burden.
    choices.sort(key=lambda p: (not p['wasPreferred'], p['allCandidatesV14'], p['code']))
    return choices


def partition(records, keys):
    groups = defaultdict(list)
    for r in records:
        groups[tuple(r['stableFeatures'][k] for k in keys)].append(r)
    sizes = sorted(len(v) for v in groups.values())
    per_character = sorted(len(groups[tuple(r['stableFeatures'][k] for k in keys)]) for r in records)
    return {'features': keys, 'cohort': len(records), 'groupCount': len(groups), 'maxGroup': max(sizes),
            'medianGroup': median(sizes), 'medianCharacterBurden': median(per_character),
            'p90CharacterBurden': per_character[int(.9*(len(per_character)-1))],
            'charactersInGroupsAtMost20': sum(n for n in sizes if n <= 20),
            'largestGroups': [{'signature': dict(zip(keys, signature)), 'count': len(rows),
                               'cps': [r['cp'] for r in rows], 'examples': ''.join(r['char'] for r in rows[:24])}
                              for signature, rows in sorted(groups.items(), key=lambda v: -len(v[1]))[:12]],
            'scope': 'fixed-chvc-cohort-semantic-partition; NOT deployed/global-four-key-candidate-count'}


def sheet(records, filename, title):
    chosen = records[:72]
    canvas = Image.new('RGB', (1120, 45 + max(1,(len(chosen)+7)//8)*104), 'white')
    draw = ImageDraw.Draw(canvas); font = ImageFont.truetype('C:/Windows/Fonts/msyh.ttc', 13)
    draw.text((10,8), title + '；原锁定字形，非人工确认', font=font, fill='black')
    sprites = {}
    for i,r in enumerate(chosen):
        p=r['preview']; path=PROJECT/'原型/键位编辑器'/p['url']
        if path not in sprites:sprites[path]=Image.open(path).convert('RGB')
        x,y=10+(i%8)*138,36+(i//8)*104
        canvas.paste(sprites[path].crop((p['x'],p['y'],p['x']+64,p['y']+64)),(x,y))
        draw.text((x,y+65),f'U+{r["cp"]:04X}',font=font,fill='black')
        draw.text((x,y+82),r['preferredCodes'][0] if r['preferredCodes'] else '待核／保留',font=font,fill='#356c65')
    canvas.save(OUTPUT/filename)


def build():
    if OUTPUT.exists():raise FileExistsError('不覆盖既有试验结果')
    before=protect(); index=load(SOURCE/'发布核对索引.json')
    code_counts=Counter(code for r in index['records'] for code in set(r['codes']))
    selected={r['cp'] for r in index['records'] if 'chvc' in r['codes']}
    assert len(selected)==1562
    rows=[r for p in sorted((SOURCE/'details').glob('*.json')) for r in load(p)['records'] if r['cp'] in selected]
    records=[];fonts={}
    for i,row in enumerate(rows):
        observations=[]; checks=[]
        for size in SIZES:
            for weight in WEIGHTS:
                mask,extent=render(row['char'],row['font']['path'],row['font'].get('index',0),size=size,weight=weight,fonts=fonts)
                f=observe(mask,extent);o=measurements(f); observations.append(o)
                checks.append({'size':size,'weight':weight,**o})
        baseline=observations[4]
        stable={k:stable_value(observations,k) for k in FEATURES}
        negative=baseline['negative'] and all(o['negative'] and o['negative']['kind']==baseline['negative']['kind'] for o in observations)
        choices=reliable_choices(row,observations,code_counts)
        positive=all(bool(o['visibleForks']) for o in observations)
        if negative:status='独立试验撤回chvc：九扰动负证据'
        elif choices:status='已有可靠结构细码优先'
        elif positive:status='分叉正证据稳定，细分仍不足'
        else:status='分叉入口待核，保留原码'
        eligible=[k for k,v in stable.items() if v!=UNKNOWN and
                  (k!='holes' or v!='0') and (k!='parts' or v!='1')]
        old_preferred=[p['code'] for p in row['paths'] if p.get('preferred')]
        preferred=[choices[0]['code']] if choices and not negative else []
        records.append({k:row.get(k) for k in ('cp','char','bucket','familyKey','preview','font','oldReviewed')} |
                       {'status':status,'stableFeatures':stable,'baseline':baseline,'checks':checks,
                        'forkPositiveVariants':sum(bool(o['visibleForks']) for o in observations),
                        'negativeCertificate':baseline['negative'] if negative else None,
                        'choices':choices,'preferredCodes':preferred,'oldPreferredCodes':old_preferred,
                        'demotedCodes':['chvc'] if preferred else [],'withdrawnTrialCodes':['chvc'] if negative else [],
                        'newFeatureDirections':eligible,'legacyChvcRetained':True})
        if (i+1)%100==0:print(f'chvc {i+1}/1562 九扰动及对象复核完成',flush=True)
    assert before==protect()
    comparisons={k:partition(records,[k]) for k in FEATURES}
    comparisons['combined']=partition(records,list(FEATURES))
    supported=[r for r in records if r['forkPositiveVariants']==9]
    supported_comparisons={k:partition(supported,[k]) for k in FEATURES}
    supported_comparisons['combined']=partition(supported,list(FEATURES))
    fallback=[r for r in records if not r['preferredCodes'] and not r['withdrawnTrialCodes']]
    preferred_counts=Counter(r['preferredCodes'][0] for r in records if r['preferredCodes'])
    capacity={'cohort':len(records),'legacyChvcCandidates':1562,
              'preferSpecific':sum(bool(r['preferredCodes']) for r in records),
              'preferredActuallyChanged':sum(bool(r['preferredCodes']) and r['preferredCodes']!=r['oldPreferredCodes'] for r in records),
              'withdrawnWithNegativeCertificate':sum(bool(r['withdrawnTrialCodes']) for r in records),
              'unresolvedFallback':len(fallback),'preferredCodeDistribution':dict(preferred_counts),
              'actualGlobalCandidateCountsV14':{code:code_counts[code] for code in preferred_counts},
              'bestGlobalCandidateMedian':median([r['choices'][0]['allCandidatesV14'] for r in records if r['choices']]) if preferred_counts else None,
              'compatibilityRawMaxUnchanged':True}
    report={'version':'chvc-structure-priority-trial-20261022-v1','date':'2026-10-22',
            'sourceIndexSHA256':before[str((SOURCE/'发布核对索引.json').relative_to(PROJECT))],
            'runtimeDeployed':False,'newBindings':False,'sourceCodebookChanged':False,
            'capacity':capacity,'statusCounts':dict(Counter(r['status'] for r in records)),
            'featureNames':FEATURES,'comparisons':comparisons,'stableForkComparisons':supported_comparisons,
            'fallbackCombination':partition(fallback,list(FEATURES)) if fallback else None,
            'records':records,'protectedHashes':before,'protectedInputsUnchanged':True,
            'policy':{'specific':'已成立的结构对象优先；优先保留已确认的具体入口，再按全量候选负担比较',
                      'chvc':'有可靠结构细码则降为兼容备选；无可靠细码不删除；负证据单独记录试验撤回',
                      'scope':'本轮只对chvc固定1562字调整试验查找优先级，不自动迁移主桶、不改部署',
                      'size':'不改圆、方、点、环的真实大小系列'},
            'limitations':['多特征组合是诊断签名，未绑定字母，不能当作四键降重结果。',
                           '全部1562字纳入每项对比，检测不稳和未提取也计入；另列九扰动分叉正证据子集。',
                           '全量实际候选数来自v14原始普通字符码表，不是新特征的全量扫描结果。',
                           '闭孔统计固定为整字全部墨迹；部件按>=3像素的8邻接墨块计，不是笔画。',
                           '孔以4邻接背景、面积>=5像素计；四个以上先合并，不能据此断言人眼孔数。',
                           '外附件试主体占墨量>=70%的分离点／直笔，以及经实际圆环分离且明显外伸的连体尾笔；未提取不等于没有附件。',
                           '连接横笔组沿用已确认的2/3横笔共侧干检测；未覆盖其它连接笔组。',
                           '分叉正证据只证明存在局部真实交点，不等于整字主族已经人工确认。',
                           '三字号乘一像素收缩/原样/膨胀，仅检验同一锁定字体的检测稳定性。'],
            'sourceHashes':{Path(__file__).name:hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}}
    save(OUTPUT/'chvc结构细分与优先级试验.json',report)
    sheet([r for r in records if r['preferredCodes']], '可靠细码优先.png', 'chvc已有可靠细码优先，最多展示72字')
    sheet(fallback[:72], '剩余大组.png', 'chvc仍需细分或核实入口，最多展示72字')
    save(OUTPUT/'验收.json',{'passed':True,'fixedCohort':1562,'allComparedWithoutHiding':True,
                           'nineChecksPerCharacter':all(len(r['checks'])==9 for r in records),
                           'sourceProtected':True,'newBindings':False,'runtimeDeployed':False})
    print(json.dumps({'capacity':capacity,'status':report['statusCounts'],
                      'comparison':{k:{f:v[f] for f in ('groupCount','maxGroup','medianCharacterBurden','charactersInGroupsAtMost20')} for k,v in comparisons.items()}},ensure_ascii=False),flush=True)
    return report


if __name__=='__main__':build()
