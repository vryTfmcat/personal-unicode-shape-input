"""Geometry-backed route amendments for reviewed comparisons, without name lookup."""
import numpy as np
from functools import lru_cache

from shape_experiment_features import normalized, render, observe, component_mask, bounds
from shape_keyboard_trial import line_group, fill_state, trial_facts, obj, RULES, ROOT, load
from shape_family_boundaries import reference_views, refine, retained_legacy_characters, fits, lookup_boundary_decisions
from shape_reviewed_components import closed_spine_arc, cycle_subject
from shape_recovery_geometry import two_stroke_angle, converging_stroke_bands, visible_fork, angle_has_visible_gap
from shape_connected_frames import connected_frames, border_spines
from shape_collision_sanity import certify


def bucket_for(groups, coarse, ratio):
    proportion = 'tall' if ratio < .8 else 'wide' if ratio > 1.25 else 'balanced'
    return next(g['bucket'] for g in groups if g['coarse'] == coarse and g['proportion'] == proportion)


@lru_cache(maxsize=1)
def frame_lookup_decisions():
    decision = load(ROOT / '人工审议.json')['keyboardConsultation20261020']['frameLookupAcceptance20261021']
    assert decision['decision'] == 'accepted'
    return decision


@lru_cache(maxsize=4)
def references(font):
    return {'familyViews': reference_views(font), 'angular4': normalized(render('4', font)[0]),
            'hookViews': np.array([normalized(np.rot90(observe(*render(ch,font,size=size,weight=weight))['body'],turns))
                                  for ch in 'Jʃɟ' for size in (48,96,128) for weight in (-1,0,1)
                                  for turns in range(4)]),
            'radialViews': np.array([normalized(observe(*render(ch,font,size=size,weight=weight))['body'])
                                    for ch in '☆★✳✴✵✷' for size in (48,96,128) for weight in (-1,0,1)]),
            'angleViews': np.array([normalized(np.rot90(render(ch, font, size=size, weight=weight)[0], turns))
                                   for ch in 'L∟⌞∧∨Vv' for size in (48, 96, 128)
                                   for weight in (-1, 0, 1) for turns in range(4)]),
            'angular4Views': [normalized(render('4', font, size=size, weight=weight)[0])
                              for size in (48, 96, 128) for weight in (-1, 0, 1)]}


def straight_body(f):
    if len(f['parts']) != 1 or f['holes'] or max(f['ratio'], 1 / f['ratio']) < 4 or f['anisotropy'] < 9:
        return False
    yy, xx = np.nonzero(f['body'])
    points = np.column_stack((xx, yy)).astype(float)
    points -= points.mean(axis=0)
    _, axes = np.linalg.eigh(np.cov(points.T))
    along, across = points @ axes[:, -1], points @ axes[:, 0]
    span = np.ptp(along)
    bins = np.linspace(along.min(), along.max() + .001, 9)
    centres, widths = [], []
    for lo, hi in zip(bins[:-1], bins[1:]):
        section = across[(along >= lo) & (along < hi)]
        if not len(section):
            return False
        centres.append(float(section.mean()))
        widths.append(float(np.quantile(section, .95) - np.quantile(section, .05) + 1))
    # A curved centreline or flared/hooked ends cannot become a whole straight line.
    return (max(abs(c) for c in centres) <= max(1.2, span * .02)
            and max(widths) <= min(widths) * 1.8)


def dominant_double_loop(f):
    if len(f['holes']) != 2 or len(f['parts']) > 2 or f['endpoints'] > 2:
        return False
    if int(f['body'].sum()) != int(f['mask'].sum()):
        return False
    holes = f['holes']
    areas = [h['area'] for h in holes]
    if min(areas) / max(areas) < .3 or sum(areas) / f['silhouette'].sum() < .10:
        return False
    x0, y0, x1, y1 = f['bbox']
    dx, dy = abs(holes[0]['cx'] - holes[1]['cx']), abs(holes[0]['cy'] - holes[1]['cy'])
    horizontal = dx >= dy
    if max(f['ratio'], 1 / f['ratio']) > 1.5 and horizontal != (f['ratio'] > 1):
        return False
    axis, low, high = ('x', x0, x1) if horizontal else ('y', y0, y1)
    cross_span = (y1 - y0) if horizontal else (x1 - x0)
    if min(dx, dy) > max(2, cross_span * .2):
        return False
    covered = max(h[axis + '1'] for h in holes) - min(h[axis + '0'] for h in holes)
    # Two pixels of raster tolerance keep thickened rings and short B-like tails.
    return covered + 2 >= (high - low) * .60


def amend(row, f, groups, anchors, templates):
    routes = [dict(r) for r in row['familyRoutes']]
    if row['char'] in retained_legacy_characters():
        for route in routes:
            route['reviewedRetain'] = '人工审议comparisonAcceptance20261021明确保留原入口'
    primary = row['familyKey']
    primary_bucket = row['bucket']
    changes = []
    decision = lookup_boundary_decisions()
    frame_decision = frame_lookup_decisions()
    reviewed_round = decision['roundPlusOtherEntries']['char'] == row['char']
    if reviewed_round:
        for route in routes:
            if route['familyKey'] == 'o' and route['target'] == 'body':
                route['reviewedRetain'] = '人工审议lookupBoundaryAcceptance20261021明确保留圆形路径'

    def remove(family):
        nonlocal routes
        if any(r['familyKey'] == family and r['target'] == 'body' for r in routes):
            changes.append('移除不成立的' + family + '主体候选入口')
        routes = [r for r in routes if not (r['familyKey'] == family and r['target'] == 'body')]

    def add(family, coarse, identity, basis, promote=False):
        nonlocal primary, primary_bucket
        bucket = bucket_for(groups, coarse, f['ratio'])
        if not any(r['familyKey'] == family and r['target'] == 'body' for r in routes):
            routes.append({'bucket': bucket, 'familyKey': family, 'familyId': identity,
                           'target': 'body', 'newGeometryBasis': basis})
            changes.append(basis)
        if promote:
            primary, primary_bucket = family, bucket

    if line_group(f):
        # Tapered wedges may support a group entry but retain their compound body.
        uniform = all(p['area'] / ((p['x1'] - p['x0']) * (p['y1'] - p['y0'])) >= .88 for p in f['parts'])
        if not row.get('oldReviewed') and row['familyKey'] != 'm':
            routes = [r for r in routes if r['target'] != 'body']
        add('l', '线与转折', 'family.line', '平行线组补充入口；旧确认／复合入口保留',
            promote=primary != 'm' or uniform)

    if len(f['parts']) == 1 and .8 <= f['ratio'] <= 1.25:
        contour = normalized(f['silhouette'])
        distances = {k: min(float(((contour - a) ** 2).mean()) for a in anchors[k]['contours']) for k in ('o', 's')}
        if distances['o'] <= .04 and distances['s'] - distances['o'] >= .08:
            if primary in ('d', 'o', 's'):
                remove('s')
                add('o', '闭环', 'family.round-outline', '圆轮廓明确胜过方轮廓；点群入口保留', promote=primary != 'd')
        elif distances['s'] <= .025 and distances['o'] - distances['s'] >= .08 and primary == 'd':
            add('s', '角形闭合', 'family.quadrilateral', '小方轮廓与点块双入口')

    if straight_body(f):
        remove('s')
        add('l', '线与转折', 'family.line', '单长直线排除四边形入口', promote=primary == 's')

    u_error = float(np.min(np.mean((templates['familyViews']['u'] - normalized(f['body'])) ** 2, axis=(1, 2))))
    if decision['squareU'] and u_error <= .025 and fits(f, 'u', templates['familyViews'])[0]:
        add('u', '开放曲线', 'family.u-shape', '已确认方角及旋转U形；强原型匹配补充入口')

    ink_distance = min(float(((normalized(f['body']) - view) ** 2).mean())
                       for view in templates.get('angular4Views', [templates['angular4']]))
    if len(f['parts']) == 1 and len(f['holes']) <= 1 and ink_distance <= .025:
        remove('s')
        fork = any(j['armCount'] in (3, 4) for j in f['junctionObjects'])
        add('h' if fork else 'a', '辐射骨架' if fork else '线与转折',
            'family.fork' if fork else 'family.angle', '已核对角折／相交字形原型，排除四边形入口', promote=True)

    semantic = row.get('semantic', {})
    double_primary = semantic.get('primaryFamilyId') == 'family.double-loop'
    double_alternate = any(r.get('familyId') == 'family.double-loop' for r in semantic.get('routes', []))
    if dominant_double_loop(f) and (double_primary or double_alternate):
        add('b', '闭环', 'family.double-loop', '沿用双环语义判定；作为补充入口保留原主体', promote=double_primary)
        if not double_primary:
            next(r for r in routes if r['familyKey'] == 'b' and r['target'] == 'body')['supplementOnly'] = True
    routes, primary, primary_bucket, exclusions = refine(
        routes, primary, primary_bucket, f, templates['familyViews'], groups)
    changes.extend('主体形族边界排除：' + e['familyKey'] + '；' + e['reason'] for e in exclusions)
    certified = []
    kept = []
    for route in routes:
        proof = (certify(row, f, route['familyKey']) if route['target'] == 'body'
                 and route['familyKey'] in ('h', 'x', 'r', 'j') and not route.get('reviewedRetain') else None)
        if proof is None:
            kept.append(route)
        else:
            certified.append(proof)
            changes.append('主体形族边界排除：' + route['familyKey'] + '；九种字号粗细均证实对象结构与入口矛盾')
    row['collisionSanityExclusions'] = certified
    routes = kept
    if primary and not any(r['target'] == 'body' and r['familyKey'] == primary for r in routes):
        primary = None
    if not primary and len(f['parts']) == 1 and not f['holes']:
        error = float(np.min(np.mean((templates['angleViews'] - normalized(f['body'])) ** 2, axis=(1, 2))))
        angle = two_stroke_angle(f) or converging_stroke_bands(f)
        template_angle = (error <= .025 and 2 <= f['endpoints'] <= 3
                          and not any(j['armCount'] >= 3 for j in f['junctionObjects']))
        if (template_angle or angle is not None) and angle_has_visible_gap(f):
            add('a', '线与转折', 'family.angle', '实际双笔角折：旋转角形强匹配或双线段证据补回角折入口', promote=True)
            next(r for r in routes if r['familyKey'] == 'a' and r['target'] == 'body')['recoveryGeometry'] = (
                angle or {'test': 'angle-ink-prototype', 'prototypeError': error})

    # A connected tail must not distort the ring's bounding box or size attribute.
    ring_part = cycle_subject(f) if any(r['familyKey'] == 'o' for r in row['familyRoutes']) else None
    if ring_part is not None and not any(r['familyKey'] == 'o' for r in routes):
        rf, tail, proof = ring_part
        error = float(np.min(np.mean((templates['familyViews']['o'] - normalized(rf['silhouette'])) ** 2, axis=(1, 2))))
        if error <= .025:
            observations = [fact for fact in trial_facts(rf, 'o', anchors) if fact['third'] not in 'mr']
            calibrate(observations, rf, 'o', anchors)
            tf = observe(tail, f['extent'])
            tail_object = obj('attached-tail', 'part', tf['bbox'], rf['bbox'], tf['extent'],
                              area=int(tail.sum()), orientation=tf['angle'])
            observations.append({'third': 'y', 'function': RULES['y'][0], 'object': tail_object,
                                 'reason': '从同一连通墨迹剥离的实际尾笔；相对圆环主体定位', 'status': 'proposal'})
            bucket = bucket_for(groups, '闭环', rf['ratio'])
            routes.append({'bucket': bucket, 'familyKey': 'o', 'familyId': 'family.round-outline',
                           'target': 'cycle-subject', 'reviewedObjectFacts': observations,
                           'componentPartitionProof': proof})
            if not primary and proof['ringPixels'] >= .85 * proof['parentPixels']:
                primary, primary_bucket = 'o', bucket
            changes.append('实际圆环与附笔分离；圆环独立计算轮廓和尺寸，尾笔另作外附线对象')

    if not primary and len(f['parts']) > 1:
        for number, part in enumerate(f['parts']):
            if part['area'] < .25 * f['mask'].sum():
                continue
            mask = component_mask(f['mask'], part)
            box = [part[k] for k in ('x0', 'y0', 'x1', 'y1')]
            whole_box = bounds(f['mask'])
            extent = f['extent'] * max(box[2]-box[0], box[3]-box[1]) / max(
                whole_box[2]-whole_box[0], whole_box[3]-whole_box[1])
            pf = observe(mask, extent)
            if straight_body(pf):
                routes.append({'bucket': bucket_for(groups, '线与转折', pf['ratio']), 'familyKey': 'l',
                               'familyId': 'family.line', 'target': 'visible-component-' + str(number),
                               'reviewedObjectFacts': trial_facts(pf, 'l', anchors),
                               'componentEvidence': {'bbox': box, 'pixels': int(mask.sum()),
                                                     'source': 'actual-connected-component', 'test': 'straight_body'}})
                changes.append('分离构件通过直线检验补回l入口；不把细长矩形当方形')
                continue
            for key, coarse, identity in [('o', '闭环', 'family.round-outline'), ('s', '角形闭合', 'family.quadrilateral'),
                                          ('t', '角形闭合', 'family.triangle'), ('u', '开放曲线', 'family.u-shape'),
                                          ('c', '开放曲线', 'family.open-arc')]:
                if key in 'ost' and not .4 <= pf['ratio'] <= 2.5:
                    continue
                if not fits(pf, key, templates['familyViews'])[0]:
                    continue
                view = normalized(pf['silhouette'] if key in 'ost' else pf['body'])
                error = float(np.min(np.mean((templates['familyViews'][key] - view) ** 2, axis=(1, 2))))
                curve_error = float(np.min(np.mean((templates['familyViews']['c'] - view) ** 2, axis=(1, 2)))) if key == 'u' else 0
                clear_u = key == 'u' and error <= .045 and error + .015 < curve_error
                if error > .025 and not clear_u:
                    continue
                observations = trial_facts(pf, key, anchors)
                if key in 'os':
                    calibrate(observations, pf, key, anchors)
                routes.append({'bucket': bucket_for(groups, coarse, pf['ratio']), 'familyKey': key,
                               'familyId': identity, 'target': 'visible-component-' + str(number),
                               'reviewedObjectFacts': observations,
                               'componentEvidence': {'bbox': box, 'pixels': int(mask.sum()),
                                                     'source': 'actual-connected-component', 'prototypeError': error,
                                                     'openCurveMarginVerified': clear_u}})
                changes.append('分离构件强几何匹配补回' + key + '入口；不据此判定整字形族')
    if not primary and not routes and f['holes']:
        for part in connected_frames(f,templates['familyViews']):
            ff, key = part['feature'],part['familyKey']
            body = obj('visible-frame','body',ff['bbox'],f['bbox'],ff['extent'],
                       area=int(ff['body'].sum()),orientation=ff['angle'] if ff['anisotropy']>1.5 else None)
            body.update(fill='hollow',sizeReferenceFill='hollow',positionReference='parent-subject')
            third = 's' if key=='o' and .8<=ff['ratio']<=1.25 else 'w'
            observations = [{'third':third,'function':RULES[third][0] if third in RULES else 'subject.outline',
                             'object':body,'reason':'由实际墨迹分离的封闭边框；尺寸与位置均属于本边框', 'status':'proposal'}]
            routes.append({'bucket':bucket_for(groups,'闭环' if key=='o' else '角形闭合',ff['ratio']),
                           'familyKey':key,'familyId':{'o':'family.round-outline','s':'family.quadrilateral','t':'family.triangle'}[key],
                           'target':part['target'],'supplementOnly':True,'frameEvidence':part['proof'],
                           'reviewedObjectFacts':observations})
            if row['char'] in frame_decision['frameSupplements']['characters'] and key == 's':
                routes[-1]['reviewedRetain'] = 'frameLookupAcceptance20261021：仅确认局部四边框补充'
            changes.append('连接外框按实际墨迹分离，补回边框构件入口；不以孔洞替代整字形族')
        for part in border_spines(f):
            proof = part['proof']
            if any(d['char'] == row['char'] and d['orientation'] == proof['orientation']
                   for d in frame_decision['rejectedBorderSpines']):
                changes.append('本人明确不从该长横线查找；不推广到其他字或其他方向')
                continue
            line = obj('visible-border-spine','part',proof['spineBBox'],f['bbox'],f['extent'],
                       area=proof['spinePixels'],orientation=proof['orientation'])
            routes.append({'bucket':bucket_for(groups,'线与转折',part['feature']['ratio']),
                           'familyKey':'l','familyId':'family.line','target':part['target'],'supplementOnly':True,
                           'spineEvidence':proof,'reviewedObjectFacts':[{'third':'l','function':RULES['l'][0],
                               'object':line,'reason':'主体边缘完整且连续的实际主干带；无补画或延长','status':'proposal'}]})
            changes.append('连接主体的完整边缘主干分离，补回实际单线入口')
    if row['char'] == frame_decision['irregularLoopSupplement']['char']:
        # Human family interpretation applies only to the displayed real loop.
        for part in connected_frames(f, templates['familyViews'], include_unclassified=True):
            if part['familyKey'] is not None:
                continue
            ff = part['feature']
            body = obj('reviewed-irregular-loop', 'body', ff['bbox'], f['bbox'], ff['extent'],
                       area=int(ff['body'].sum()))
            body.update(fill='hollow', positionReference='parent-subject')
            routes.append({'bucket': bucket_for(groups, '闭环', ff['ratio']), 'familyKey': 'p',
                           'familyId': 'family.irregular-loop', 'target': part['target'], 'supplementOnly': True,
                           'reviewedLoopEvidence': part['proof'],
                           'reviewedRetain': 'frameLookupAcceptance20261021：本人确认所示下部环为不规则回环',
                           'reviewedObjectFacts': [{'third': 'w', 'function': 'subject.outline', 'object': body,
                               'reason': '实际闭环分离；形族来自本人对该对象的明确答复', 'status': 'reviewed-lookup'}]})
            changes.append('按本人答复补充下部不规则回环，不改变整字主族')
    if not primary and not routes:
        for semantic_route in semantic.get('routes', []):
            target = semantic_route.get('target', '')
            if semantic_route.get('key') != 'h' or not target.startswith('junction-'):
                continue
            number = int(target.split('-')[-1])
            if number >= len(f['junctionObjects']):
                continue
            junction = f['junctionObjects'][number]
            proof = visible_fork(f, junction)
            if proof is None:
                continue
            o = obj('local-junction-' + str(number), 'junction',
                    [junction[k] for k in ('x0', 'y0', 'x1', 'y1')], f['bbox'], f['extent'])
            routes.append({'bucket': bucket_for(groups, '辐射骨架', 1.), 'familyKey': 'h',
                           'familyId': 'family.fork', 'target': target, 'supplementOnly': True,
                           'localBranchProof': proof,
                           'reviewedObjectFacts': [{'third': 'm', 'function': RULES['m'][0], 'object': o,
                               'reason': '旧检测已记录局部分叉；实际墨迹双环带出口复核后接入编码', 'status': 'proposal'}]})
            changes.append('接回已检测但生成器漏接的局部分叉入口；不把局部替代整字主族')
    cross = next((r for r in routes if r['familyKey'] == 'x' and r['target'] == 'body'), None)
    if (cross and decision['crossPriority'] and len(f['parts']) == 1 and not f['holes']
            and f['endpoints'] == 4 and len(f['junctionObjects']) == 1 and f['junctionObjects'][0]['armCount'] == 4):
        primary, primary_bucket = 'x', cross['bucket']
        changes.append('已确认交叉优先；保留分叉补充入口')
    if reviewed_round:
        for part in closed_spine_arc(f):
            coarse = '线与转折' if part['familyKey'] == 'l' else '开放曲线'
            routes.append({'bucket': bucket_for(groups, coarse, part['ratio']), 'familyKey': part['familyKey'],
                           'familyId': part['familyId'], 'target': part['target'],
                           'reviewedObjectFacts': part['facts'], 'objectPartitionProof': part['proof']})
            changes.append('已确认D多入口需求；实际构件补充：' + part['target'])
    for route in routes:
        if route['target']=='body' and route['familyKey']=='h':
            verified = [n for n,j in enumerate(f['junctionObjects']) if visible_fork(f,j) is not None]
            route['lookupEvidence'] = {'kind':'visible-fork-scale-check','verified':bool(verified),
                                       'verifiedJunctions':verified,
                                       'dominantSubject':len(verified)==1 and len(f['parts'])==1 and not f['holes'] and f['endpoints'] in (3,4),
                                       'scope':'lookup-ranking-only-not-path-removal'}
        if route['target']=='body' and route['familyKey']=='j':
            error = float(np.min(np.mean((templates['hookViews']-normalized(f['body']))**2,axis=(1,2))))
            route['lookupEvidence'] = {'kind':'hook-ink-prototype','verified':error<=.07,
                                       'prototypeError':error,'scope':'lookup-ranking-only-not-path-removal'}
        if route['target']=='body' and route['familyKey']=='r':
            verified = [n for n,j in enumerate(f['junctionObjects']) if visible_fork(f,j,range(5,17)) is not None]
            error = float(np.min(np.mean((templates['radialViews']-normalized(f['body']))**2,axis=(1,2))))
            route['lookupEvidence'] = {'kind':'radial-ink-or-outline','verified':bool(verified) or error<=.065,
                                       'verifiedJunctions':verified,'prototypeError':error,
                                       'dominantSubject':error<=.065 or (len(verified)==1 and len(f['parts'])==1 and not f['holes']),
                                       'scope':'lookup-ranking-only-not-path-removal'}
    return routes, primary, primary_bucket, changes


def calibrate(observations, f, family, anchors):
    state = fill_state(f, family, anchors)
    if family not in ('o', 's') or not state:
        return
    for fact in observations:
        if fact['object']['kind'] == 'body':
            fact['object']['sizeReferenceFill'] = state
