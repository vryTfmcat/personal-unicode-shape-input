"""An in-memory projection of existing candidates, never a second codebook."""
import re
import threading
from collections import defaultdict

BUILD_LOCK = threading.Lock()


def rotate(code):
    return code[1:] + code[0]


def index(overview, allocation, length):
    cache = getattr(overview, '_bucket_order_indexes', None)
    if cache is None:
        with BUILD_LOCK:
            if not hasattr(overview, '_bucket_order_indexes'):
                overview._bucket_order_indexes = {}
        cache = overview._bucket_order_indexes
    key = (allocation, length)
    with BUILD_LOCK:
        if key in cache:
            return cache[key]
        # Registered paths only: a three-letter prefix of a four-code is not
        # itself a short code. brief() already composes current accepted overlays.
        registered = defaultdict(set)
        for cp in overview.rows:
            for code in overview.brief(cp, allocation)['codes']:
                if len(code) == length:
                    registered[code].add(cp)
        prefixes = defaultdict(dict)
        routes = defaultdict(list)
        for code in sorted(registered):
            entries = (overview.allocation_members(code) if allocation
                       else overview.layers.entries.get(code, {}))
            # Four-code exact membership is the existing authoritative query.
            # A short path includes only actually registered short-code holders,
            # never four-code descendants sharing its canonical prefix.
            members = entries if length == 4 else {
                cp: entries.get(cp, 3) for cp in registered[code]}
            rotated = rotate(code)
            routes[rotated] = [(code, cp, tier) for cp, tier in members.items()]
            for size in range(length + 1):
                target = prefixes[rotated[:size]]
                for cp, tier in members.items():
                    target[cp] = min(target.get(cp, 4), tier)
        result = dict(prefixes=dict(prefixes), routes=dict(routes))
        cache[key] = result
        return result


def query(overview, params):
    get = lambda k, default='': params.get(k, [default])[0]
    allowed = {'allocation','order','routeLength','prefix','text','offset'}
    if set(params)-allowed:
        raise ValueError('后置编码查询不能混用键位、集合或专项队列筛选')
    allocation = get('allocation') == '1'
    if not allocation:
        raise ValueError('后置查询仅用于当前工作视图；历史v14保持原顺序')
    scope = get('routeLength', '4')
    if scope not in ('3', '4'):
        raise ValueError('后置查询须指定四码或原三码，不能混合解释')
    length = int(scope)
    prefix = get('prefix').lower()
    if prefix and not re.fullmatch('[a-z]{1,'+scope+'}', prefix):
        raise ValueError('后置编码长度超出当前查询范围')
    data = index(overview, allocation, length)
    members = data['prefixes'].get(prefix, {})
    text = get('text').strip()
    wanted = None
    if text:
        match = re.fullmatch(r'(?:U\+|0x)([0-9a-f]{1,6})', text, re.I)
        wanted = {int(match[1], 16)} if match else {ord(ch) for ch in text}
    # Exact four-code queries preserve the existing tier/order, including page
    # boundaries; only a new cross-bucket union needs a new deterministic order.
    cps = sorted((cp for cp in members if wanted is None or cp in wanted),
                 key=lambda cp: (members[cp], cp if len(prefix)<length else 0))
    offset = max(0, int(get('offset', '0')))
    matches = defaultdict(list)
    page = set(cps[offset:offset+60])
    for rotated, entries in data['routes'].items():
        if rotated.startswith(prefix):
            for canonical, cp, tier in entries:
                if cp in page:
                    matches[cp].append(dict(canonical=canonical, code=rotated))
    names = ('primary', 'component', 'supplement', 'pending')
    rows = [dict(overview.brief(cp, True), layer=names[members[cp]],
                 lookupPaths=matches[cp], geometry='沿用当前原码候选；仅换查询顺序')
            for cp in cps[offset:offset+60]]
    canonical = prefix[-1]+prefix[:-1] if len(prefix) == length else None
    return dict(id=overview.id, allocation=True, total=len(cps), offset=offset,
                rows=rows, groups={n:sum(members[cp]==i for cp in cps)
                                   for i,n in enumerate(names)}, audit=None,
                lookupOrder='back', routeLength=length, canonical=canonical,
                crossBucket=len(prefix)<length,
                shortPolicy='仅注册三码；不把四码前缀当作三码')
