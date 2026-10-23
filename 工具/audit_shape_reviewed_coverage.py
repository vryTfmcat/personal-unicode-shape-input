"""Freeze the 145 historical-bucket identities and inspect their locked glyphs."""
import argparse
from collections import Counter
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from build_shape_keyboard_full import save
from shape_experiment_features import render, observe, normalized
from shape_family_boundaries import reference_views
from shape_keyboard_trial import PROJECT, DATA, load, fingerprint


def audit(run, output):
    output.mkdir(parents=True, exist_ok=True)
    index = load(run / '发布核对索引.json')
    candidates = [r for r in load(run / '程序修复与漏收审计.json')['remaining'] if r['oldReviewed']]
    assert len(candidates) == 145
    wanted = {r['cp'] for r in candidates}
    stage = load(DATA / 'shape-stage.json')
    source = PROJECT / stage['source'] / '全部收纳.json'
    history = {r['cp']: r for r in load(source)['characters'] if r['cp'] in wanted}
    assert all(r.get('shapeAssignmentLocked') for r in history.values())
    slim = {r['cp']: r for r in index['records']}
    details = {}
    for url in {slim[cp]['detailUrl'] for cp in wanted}:
        details.update({r['cp']: r for r in load(run / url)['records'] if r['cp'] in wanted})
    views = reference_views(Path('C:/Windows/Fonts/seguisym.ttf'))
    records, masks = [], {}
    for cp, row in sorted(details.items()):
        font = row['font']
        mask, extent = render(row['char'], font['path'], font.get('index', 0))
        f = observe(mask, extent)
        masks[cp] = mask
        errors = {key: round(float(np.min(np.mean((vv - normalized(f['silhouette'] if key in 'ost' else f['body']))**2,
                                                   axis=(1, 2)))), 5) for key, vv in views.items()}
        records.append({'cp': cp, 'char': row['char'], 'history': history[cp],
                        'historicalConfirmationScope': '旧primary分桶锁定，不是本轮形族、路径或迁移确认',
                        'currentBucket': row['bucket'], 'baselineFamily': row['baselineFamilyKey'],
                        'font': font, 'bbox': f['bbox'], 'extent': extent, 'ratio': f['ratio'],
                        'parts': f['parts'], 'holes': f['holes'], 'endpoints': f['endpoints'],
                        'junctions': f['junctionObjects'], 'wholePrototypeErrors': errors,
                        'withdrawalReasons': row['familyBoundaryReview']['excluded'],
                        'pathsAbsent': not row['paths']})
    summary = {'count': len(records), 'allStillWithoutDetailedPaths': all(r['pathsAbsent'] for r in records),
               'source': str(source), 'sourceSHA256': fingerprint(source),
               'priorRun': index['id'], 'cohortFrozen': sorted(wanted),
               'oldFamilies': dict(Counter(r['baselineFamily'] for r in records)),
               'historyStatuses': dict(Counter(r['history']['status'] for r in records)),
               'historyReasons': dict(Counter(r['history'].get('reviewReason') for r in records)),
               'historyScope': 'historical first-bucket acceptance only; no route exemptions',
               'historicalBucketsPreservedInSource': True, 'records': records}
    save(output / '历史确认145字初核.json', summary)
    label = ImageFont.truetype('C:/Windows/Fonts/consola.ttf', 15)
    for page in range((len(records)+35)//36):
        canvas = Image.new('RGB', (1440, 1320), 'white')
        draw = ImageDraw.Draw(canvas)
        for n, r in enumerate(records[page*36:(page+1)*36]):
            x, y = n%6*240, n//6*220
            glyph = Image.fromarray(np.where(masks[r['cp']], 0, 255).astype('uint8')).resize((144,144), Image.Resampling.NEAREST)
            canvas.paste(glyph, (x+42,y+22))
            draw.text((x+5,y+3), f"U+{r['cp']:04X} old:{r['history']['primary']} trial:{r['baselineFamily']}", font=label, fill='black')
            draw.text((x+5,y+169), f"p{len(r['parts'])} hole{len(r['holes'])} end{r['endpoints']} j{len(r['junctions'])}", font=label, fill='black')
            draw.text((x+5,y+190), 'arms:'+','.join(str(j['armCount']) for j in r['junctions']), font=label, fill='black')
        canvas.save(output / f'历史确认145字-原字形-{page+1}.png')
    print({k:v for k,v in summary.items() if k not in ('records','cohortFrozen')})
    return summary


def preflight(run, output):
    from build_shape_keyboard_full import rebuild_row, validate_row
    from shape_keyboard_trial import trial_definitions, outline_anchors
    provenance = load(run / '构建来源.json')
    baseline_path = Path(provenance['baseline'])
    baseline_index = load(baseline_path.parent / '发布核对索引.json')
    definitions = trial_definitions(baseline_index)
    cohort = load(output / '历史确认145字初核.json')
    wanted = set(cohort['cohortFrozen'])
    anchors = outline_anchors(Path('C:/Windows/Fonts/seguisym.ttf'))
    fonts, results = {}, []
    for row in load(baseline_path)['records']:
        if row['cp'] not in wanted:
            continue
        rebuilt, delta = rebuild_row(row,definitions,baseline_index['bucketGroups'],anchors,fonts)
        validate_row(rebuilt,definitions)
        results.append({'cp':row['cp'],'char':row['char'],'recovered':bool(rebuilt['paths']),
                        'family':rebuilt['familyKey'],'routes':rebuilt['familyRoutes'],
                        'codes':[p['code'] for p in rebuilt['paths']], 'amendments':rebuilt['routeAmendments']})
    assert len(results)==145
    summary = {'cohortCount':145,'recovered':sum(r['recovered'] for r in results),
               'remaining':sum(not r['recovered'] for r in results),
               'sourceHistoricalConfirmationsUnchanged':fingerprint(Path(cohort['source']))==cohort['sourceSHA256'],
               'records':results}
    save(output / '145字修复预检.json',summary)
    print({k:v for k,v in summary.items() if k!='records'})
    print([(r['char'],r['codes']) for r in results if r['recovered']])
    return summary


def verify_after(after, output):
    from shape_recovery_geometry import visible_fork, two_stroke_angle, converging_stroke_bands
    cohort = load(output / '历史确认145字初核.json')
    wanted = set(cohort['cohortFrozen'])
    index = load(after / '发布核对索引.json')
    records, checked, categories, selected = [], Counter(), Counter(), {}
    for url in sorted({r['detailUrl'] for r in index['records']}):
        for row in load(after / url)['records']:
            geometry = [r for r in row['familyRoutes'] if r.get('localBranchProof') or r.get('recoveryGeometry')]
            if geometry:
                font = row['font']
                f = observe(*render(row['char'],font['path'],font.get('index',0)))
                for route in geometry:
                    if route.get('localBranchProof'):
                        number = int(route['target'].split('-')[-1])
                        assert visible_fork(f,f['junctionObjects'][number]) == route['localBranchProof']
                        checked['freshVisibleForkProofs'] += 1
                    if route.get('recoveryGeometry'):
                        proof = route['recoveryGeometry']
                        if proof['test'] != 'angle-ink-prototype':
                            assert (two_stroke_angle(f) or converging_stroke_bands(f)) == proof
                        checked['angleRecoveryProofs'] += 1
            if row['cp'] not in wanted:
                continue
            f = row['features']
            category = ('已补回入口' if row['paths'] else
                        '多闭孔／连接外框需进一步提取对象' if len(f['holes'])>1 else
                        '单闭孔／附件轮廓尚无可靠对象' if f['holes'] else
                        '分离部件尚未匹配可靠入口' if len(f['parts'])>1 else
                        '开口或线骨架尚无可靠入口')
            categories[category] += 1
            selected[row['cp']] = row
            records.append({'cp':row['cp'],'char':row['char'],'recovered':bool(row['paths']),
                            'category':category,'primaryFamily':row['familyKey'],
                            'codes':[p['code'] for p in row['paths']],
                            'routes':row['familyRoutes'],'amendments':row['routeAmendments']})
    assert len(records)==145
    assert fingerprint(Path(cohort['source'])) == cohort['sourceSHA256']
    summary = {'passed':True,'cohortCount':145,'recovered':sum(r['recovered'] for r in records),
               'remaining':sum(not r['recovered'] for r in records),'categories':dict(categories),
               'historicalConfirmationsSourceHashUnchanged':True,'historicalScope':cohort['historyScope'],
               'globalFreshGeometryChecks':dict(checked),'run':index['id'],'records':records}
    save(after / '历史确认145字逐字核查.json',summary)
    canvas = Image.new('RGB',(1360,690),'white')
    draw = ImageDraw.Draw(canvas)
    title = ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',19)
    label = ImageFont.truetype('C:/Windows/Fonts/consola.ttf',17)
    for number,char in enumerate('¬ᶺ𝙫Ṷᵏ𝘒𒋡𐍢'):
        row = selected[ord(char)]
        f = observe(*render(char,row['font']['path'],row['font'].get('index',0)))
        pixels = np.full((*f['mask'].shape,3),255,dtype='uint8')
        pixels[f['mask']] = [190,190,190]
        route = row['familyRoutes'][0]
        selected_mask = f['mask'].copy()
        if route.get('componentEvidence'):
            box = route['componentEvidence']['bbox']
            yy,xx = np.indices(f['mask'].shape)
            selected_mask &= (xx>=box[0])&(xx<box[2])&(yy>=box[1])&(yy<box[3])
        if route.get('localBranchProof'):
            box = route['reviewedObjectFacts'][0]['object']['bbox']
            yy,xx = np.indices(f['mask'].shape)
            selected_mask &= (xx>=box[0])&(xx<box[2])&(yy>=box[1])&(yy<box[3])
        pixels[selected_mask] = [25,100,155]
        x,y = number%4*340,number//4*320
        kind = '角折主体' if route['familyKey']=='a' else 'U形构件' if route['familyKey']=='u' else '局部分叉检测位置'
        draw.text((x+12,y+7),f'U+{ord(char):04X}  '+kind,font=title,fill='black')
        canvas.paste(Image.fromarray(pixels).resize((224,224),Image.Resampling.NEAREST),(x+50,y+40))
        codes = [p['code'] for p in row['paths']]
        draw.text((x+12,y+270),' / '.join(codes[:3]),font=label,fill='black')
    draw.text((12,658),'局部分叉只标检测位置，不以窗口大小编码尺寸；其他字符蓝色为选中墨迹。',font=title,fill='black')
    canvas.save(after/'历史确认字修复示例.png')
    print({k:v for k,v in summary.items() if k!='records'})
    return summary


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--run', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--preflight', action='store_true')
    p.add_argument('--after', type=Path)
    args = p.parse_args()
    if args.after:
        verify_after(args.after,args.output)
    else:
        audit(args.run, args.output)
        if args.preflight:
            preflight(args.run,args.output)
