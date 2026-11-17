"""Necessary whole-glyph conditions, never character-identity exceptions."""


def check_scope(prefix, row, facts):
    """Reject contradictions; surviving candidates still require semantic review."""
    key = prefix[1]
    stats = row['statistics'] or {}
    parts = row.get('scopeEvidence', {}).get('inkComponents')
    routes = [r for r in facts['routes'] if r['prefix'] == prefix and r['target'] == 'body'
              and not r['supplementOnly'] and not r.get('localOnly')]
    reasons = []
    if not routes:
        reasons.append('旧前缀仅为局部／补充对象，不能传播为整字计数入口')
    elif all(r['verified'] is False for r in routes):
        reasons.append('旧整字形族依据仍待核，不能因新计数稳定而升级')
    elif prefix != facts.get('primaryPrefix') and not any(r['verified'] is True for r in routes):
        reasons.append('旧替代形族不是整字主形族，也没有独立整体验证')
    if key in 'hxr' and not any(r['verified'] is True for r in routes):
        reasons.append('分叉／交叉／放射缺少独立整字可见墨迹验证，骨架连接点不能直接升级为新入口')
    junctions = sum(stats.get(k, 0) for k in ('forks', 'crosses', 'otherJunctions'))
    holes = stats.get('loops', 0)
    ink = row.get('scopeEvidence', {})
    if (key in 'hxr' and not holes and ink.get('bboxInkFraction', 0) > .35
            and ink.get('minorOverMajor', 0) >= .35 and not any(r['verified'] is True for r in routes)):
        reasons.append('紧凑高密度无孔墨面缺少独立可见笔线验证，不能把细化骨架当交叉或放射')
    if key in 'achuxt' and parts != 1:
        reasons.append('该单体形族混入分离墨部件；整字对象不完整')
    if key in 'cu':
        if holes or junctions:
            reasons.append('开口单曲线混入闭孔或叉交')
        if not stats.get('curveStrokes', 0) and not (key == 'u' and stats.get('corners', 0) >= 2):
            reasons.append('没有曲线主体，也不具备方U形的双折结构')
    elif key == 'a':
        if stats.get('curveStrokes', 0):
            reasons.append('整字角折入口混入曲连续笔；曲折复合形另待核')
        if not stats.get('corners', 0):
            reasons.append('整字没有稳定折角')
        if holes or junctions:
            reasons.append('单角折入口混入闭环或分叉交叉主体')
    elif key == 'l':
        if any(stats.get(k, 0) for k in ('curveStrokes', 'corners', 'forks', 'crosses', 'otherJunctions', 'loops')):
            reasons.append('线条／线组入口混入曲笔、折角、叉交或闭环')
        if not parts or stats.get('straightStrokes', 0) != parts:
            reasons.append('直线数未覆盖全部墨部件，可能存在点块或附加部件')
    elif key == 'h':
        if not junctions:
            reasons.append('整字没有稳定分叉或交叉点')
    elif key == 'x':
        if not stats.get('crosses', 0):
            reasons.append('整字没有稳定四臂交叉点')
    elif key in 'ost':
        if not holes:
            reasons.append('空心闭轮廓入口没有闭孔证据，线模型不能证明实体外形')
        if parts != 1 or junctions or holes != 1:
            reasons.append('闭轮廓新计数入口暂限单一轮廓；附加构件或复合闭孔另待核')
        if key == 'o' and (stats.get('straightStrokes', 0) or stats.get('corners', 0) or stats.get('curveStrokes') != 1):
            reasons.append('整字不是完整单圆曲线，混有直笔或折角')
        if key == 's' and (stats.get('corners') != 4 or stats.get('curveStrokes', 0)):
            reasons.append('四边形完整四角证据不足；圆角或复合轮廓保留旧码待核')
        if key == 't' and stats.get('corners', 0) < 3:
            reasons.append('三角轮廓没有至少三个稳定折角证据')
    elif key == 'b':
        if holes < 2:
            reasons.append('闭孔证据不足以支持双环；孔数不等同环数，保留旧查法待辨')
    elif key == 'p':
        if not holes:
            reasons.append('回环入口缺少整字闭孔证据')
    elif key == 'w':
        if parts != 1:
            reasons.append('多部件波形尚未逐成员证明同类，不能视作单一整字波形')
        if holes or junctions:
            reasons.append('波形入口混入闭孔或叉交')
        if not stats.get('curveStrokes', 0):
            reasons.append('整字没有稳定曲连续笔')
    elif key == 'r':
        star_outline = holes > 0 and stats.get('corners', 0) >= 5
        multi_junction = junctions >= 2 or stats.get('otherJunctions', 0) > 0
        if not (star_outline or multi_junction):
            reasons.append('没有星形闭轮廓或多向分支证据，单个三／四叉不能直接当放射主体')
    elif key == 'd':
        reasons.append('点／点群尚无可见线对象证明，暂不根据细化骨架派生直曲笔码')
    elif key != 'm':
        reasons.append('该形族尚无整字结构计数适用边界，保留原码待核')
    return not reasons, reasons


def load_facts(overview, cps):
    """Read each pinned detail chunk once; keep only auditable route metadata."""
    facts = {}
    chunks = {overview.rows[cp]['detailUrl'] for cp in cps}
    for name in sorted(chunks):
        chunk = overview.chunk(name)
        for cp, r in chunk.items():
            if cp not in cps:
                continue
            facts[cp] = dict(primaryPrefix=(r['bucket'] or '') + (r['familyKey'] or ''),
                             routes=[dict(prefix=x['bucket'] + x['familyKey'], target=x['target'],
                                          supplementOnly=x.get('supplementOnly', False),
                                          localOnly=bool(x.get('localBranchProof')) or x.get('lookupEvidence', {}).get('dominantSubject') is False,
                                          verified=x.get('lookupEvidence', {}).get('verified'))
                                     for x in r['familyRoutes']])
    assert set(facts) == set(cps)
    return facts
