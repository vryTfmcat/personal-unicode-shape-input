"""Read-only review of one pinned independent run, never a publication source."""
import functools
import hashlib
import json
import re
import threading
from collections import Counter
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

PROJECT = Path(__file__).resolve().parents[2]
RUNS = PROJECT / '数据/三模式/规则库/四键实验/键位试验'
RUN = RUNS / '20261021-connected-stroke-group-full-v1'
AUDIT_RUN = RUNS / '20261021-certified-collision-repairs-v2'
INDEX_SHA = 'a0a81a9782cf636a61f0fd694c89eebde7ebd5e7ab0422f4ffae7c3ec7fa76ca'
ASSETS = {'Q': 'Q主体与尾笔分离.png', 'D': 'D三种对象查法.png', 'EF': 'E-F横笔组新码.png'}
HISTORICAL_RUN = RUNS / '20261022-historical-buckets-pilot-v1'
CLEANUP_RUN = RUNS / '20261022-historical-buckets-cleanup-draft-v1'
U_EXPANSION_RUN = RUNS / '20261022-u-line-group-expansion-v1'
CHVC_RUN = RUNS / '20261022-chvc-structure-trial-v1'
CENTRE_RUN = RUNS / '20261022-centre-position-trial-v1'
THICK_RUN = RUNS / '20261022-thick-fork-repair-v1'
HISTORICAL_ASSETS = {'historical-u': '线群候选.png', 'historical-v': '块面候选.png',
                     'historical-existing': '现有形族补回候选.png'}
LETTERS = 'abcdefghijklmnopqrstuvwxyz'
LAYERS = ('primary', 'component', 'supplement', 'pending')
LOCK = threading.Lock()


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


@functools.lru_cache(maxsize=1)
def historical_pilot():
    report = read(HISTORICAL_RUN / '历史桶整理与新用途试验.json')
    if report['sourceIndexSHA256'] != INDEX_SHA or report['runtimeDeployed'] is not False:
        raise ValueError('历史桶试验与当前独立版不一致')
    return report


def historical_summary():
    report = historical_pilot()
    return {k: v for k, v in report.items() if k not in ('records', 'protectedHashes', 'controls')}


def historical_record(cp):
    return next((r for r in historical_pilot()['records'] if r['cp'] == cp), None)


@functools.lru_cache(maxsize=1)
def cleanup_draft():
    report = read(CLEANUP_RUN / '旧桶清空与新键位草案.json')
    if report['sourceIndexSHA256'] != INDEX_SHA or report['runtimeDeployed'] is not False:
        raise ValueError('清空草案来源不一致，停止读取')
    return report


def cleanup_summary():
    return {k:v for k,v in cleanup_draft().items() if k not in ('records','protectedHashes')}


@functools.lru_cache(maxsize=1)
def u_expansion():
    report=read(U_EXPANSION_RUN / 'u线群全量近似候选.json')
    if report['sourceIndexSHA256']!=INDEX_SHA or report['bucketsChanged'] is not False:
        raise ValueError('u近似候选来源不一致')
    return report


def u_expansion_summary():
    report=u_expansion()
    return {k:v for k,v in report.items() if k not in ('records','boundaries','protectedHashes')}


@functools.lru_cache(maxsize=1)
def u_expansion_records():
    return {r['cp']:r for r in u_expansion()['records']}


def u_expansion_members(kind):
    rows=u_expansion()['records']
    groups={'stable':'同一定义稳定新候选','unstable':'同形线群但检测不稳定',
            'broad':'多段层列扩展候选','current':'原u已保留42字'}
    if kind in groups:return [r['cp'] for r in rows if r['category']==groups[kind]]
    if kind=='six':return [r['cp'] for r in rows if not r['alreadyInU'] and r['category']==groups['stable'] and 0x4DC0<=r['cp']<=0x4DFF]
    if kind=='three':return [r['cp'] for r in rows if r['category']==groups['stable'] and 0x2630<=r['cp']<=0x2637]
    if kind=='two':return [r['cp'] for r in rows if 0x268C<=r['cp']<=0x268F]
    if kind=='new':return [r['cp'] for r in rows if not r['alreadyInU']]
    raise ValueError('未知u近似候选组')


@functools.lru_cache(maxsize=1)
def chvc_trial():
    report=read(CHVC_RUN/'chvc结构细分与优先级试验.json')
    if report['sourceIndexSHA256']!=INDEX_SHA or report['runtimeDeployed'] is not False or report['newBindings'] is not False:
        raise ValueError('chvc结构试验来源或独立范围不一致')
    return report


@functools.lru_cache(maxsize=1)
def chvc_records():
    return {r['cp']:r for r in chvc_trial()['records']}


def chvc_summary():
    return {k:v for k,v in chvc_trial().items() if k not in ('records','protectedHashes')} | {
        'stableCentralGap':len(chvc_members('centre')),
        'noForkSupport':len(chvc_members('never')),'partialForkSupport':len(chvc_members('partial'))}


def chvc_members(kind):
    rows=chvc_trial()['records']
    if kind=='all':return [r['cp'] for r in rows]
    if kind=='preferred':return [r['cp'] for r in rows if r['preferredCodes']]
    if kind=='pending':return [r['cp'] for r in rows if r['forkPositiveVariants']<9 and not r['withdrawnTrialCodes']]
    if kind=='positive':return [r['cp'] for r in rows if r['forkPositiveVariants']==9]
    if kind=='never':return [r['cp'] for r in rows if r['forkPositiveVariants']==0]
    if kind=='partial':return [r['cp'] for r in rows if 0<r['forkPositiveVariants']<9]
    if kind=='fallback':return [r['cp'] for r in rows if not r['preferredCodes'] and not r['withdrawnTrialCodes']]
    if kind=='centre':return [r['cp'] for r in rows if not r['preferredCodes'] and
                             all(len(o['visibleForks'])==1 and o['visibleForks'][0]['positionKey'] is None for o in r['checks'])]
    if kind in ('holes','parts','attachments','bars'):
        return [r['cp'] for r in rows if kind in r['newFeatureDirections']]
    if kind=='largest':return chvc_trial()['comparisons']['combined']['largestGroups'][0]['cps']
    if kind=='residual':return chvc_trial()['fallbackCombination']['largestGroups'][0]['cps']
    if kind=='currentResidual':
        original=chvc_trial()['fallbackCombination']['largestGroups'][0]['cps']
        return [cp for cp in original if not (has_centre_trial() and centre_records().get(cp,{}).get('preferredCodes'))]
    if kind=='negative':return [r['cp'] for r in rows if r['withdrawnTrialCodes']]
    raise ValueError('未知chvc试验队列')


@functools.lru_cache(maxsize=1)
def centre_trial():
    report=read(CENTRE_RUN/'中心属性交点试验.json')
    if report['sourceIndexSHA256']!=INDEX_SHA or report['runtimeDeployed'] is not False:
        raise ValueError('中心试验来源或部署状态不一致')
    return report


@functools.lru_cache(maxsize=1)
def centre_records():
    return {r['cp']:r for r in centre_trial()['records']}


def centre_summary():
    new_chvc=sum(bool(r['preferredCodes']) and r['chvcCohort'] for r in centre_trial()['records'])
    return {k:v for k,v in centre_trial().items() if k not in ('records','protectedHashes')} | {
        'newChvcPreferred':new_chvc,'currentChvcSpecificPreferred':418+new_chvc,
        'remainingChvcWithoutSpecificPreference':1144-new_chvc,'currentLargestResidual':len(chvc_members('currentResidual'))}


def centre_members(kind):
    rows=centre_trial()['records']
    if kind=='all':return [r['cp'] for r in rows]
    if kind=='stable':return [r['cp'] for r in rows if r['stable']]
    if kind=='unstable':return [r['cp'] for r in rows if not r['stable']]
    if kind=='preferred':return [r['cp'] for r in rows if r['preferredCodes']]
    if kind=='gap':return [r['cp'] for r in rows if r['inPrevious101']]
    if kind=='frozen':return [r['cp'] for r in rows if r['frozenPreference']]
    raise ValueError('未知中心试验队列')


@functools.lru_cache(maxsize=1)
def centre_additions():
    result={}
    for cp,row in centre_records().items():
        for p in row['paths']:
            for n in range(1,5):
                members=result.setdefault(p['code'][:n],{})
                members[cp]=min(members.get(cp,4),row['pathTiers'][p['code']])
    return result


def has_centre_trial():
    return (CENTRE_RUN/'中心属性交点试验.json').is_file()


def has_thick_repair():
    return (THICK_RUN/'粗笔分叉误拒复核.json').is_file()


@functools.lru_cache(maxsize=1)
def thick_repair():
    report=read(THICK_RUN/'粗笔分叉误拒复核.json')
    if report['sourceIndexSHA256']!=INDEX_SHA or report['runtimeDeployed'] is not False:
        raise ValueError('粗笔复核来源或部署状态不一致')
    return report


@functools.lru_cache(maxsize=1)
def thick_records():
    return {r['cp']:r for r in thick_repair()['records']}


def thick_members(kind):
    rows=thick_repair()['records']
    if kind=='all':return [r['cp'] for r in rows]
    if kind=='improved':return [r['cp'] for r in rows if r['improved']]
    if kind=='newStable':return [r['cp'] for r in rows if r['newlyStable']]
    if kind=='stable':return [r['cp'] for r in rows if r['afterPositiveVariants']==9]
    if kind=='pending':return [r['cp'] for r in rows if r['afterPositiveVariants']<9]
    raise ValueError('未知粗笔复核队列')


@functools.lru_cache(maxsize=1)
def cleanup_records():
    return {r['cp']:r for r in cleanup_draft()['records']}


@functools.lru_cache(maxsize=1)
def cleanup_additions():
    from shape_candidate_layers import route_layer
    additions = {}
    def add(prefix,cp,tier):
        members=additions.setdefault(prefix,{})
        members[cp]=min(members.get(cp,4),tier)
    for cp,row in cleanup_records().items():
        draft_row={'familyKey':row['draftFamily']}
        routes={(r['bucket']+r['familyKey'],r['target']):r for r in row['familyRoutes']}
        if row['draftBucket']:
            add(row['draftBucket'],cp,0)
        for route in row['familyRoutes']:
            add(route['bucket']+route['familyKey'],cp,route_layer(draft_row,route))
        for path in row['paths']:
            code=path['code']
            tier=min(route_layer(draft_row,routes[(code[:2],e['familyTarget'])],e['objectId']) for e in path['evidence'])
            for n in range(1,len(code)+1):add(code[:n],cp,tier)
    return additions


class Overview:
    def __init__(self):
        from shape_candidate_layers import CandidateLayers
        raw = (RUN / '发布核对索引.json').read_bytes()
        if hashlib.sha256(raw).hexdigest() != INDEX_SHA:
            raise ValueError('独立版索引校验失败；停止读取，不回退到旧版')
        index = json.loads(raw)
        del raw
        if index.get('active') is not False:
            raise ValueError('该入口只允许独立试验版')
        self.id = index['id']
        self.definitions = index['definitions']
        self.rows = {r['cp']: {k: r.get(k) for k in (
            'cp', 'char', 'bucket', 'oldBucket', 'oldReviewed', 'familyKey',
            'codes', 'preferredCodes', 'preview', 'detailUrl')} for r in index['records']}
        # Route proofs are reread by chunk; do not retain a second full copy while indexing.
        del index['records']
        self.unclassified = index['unclassified']
        self.collections = index['collections']
        def details():
            for path in sorted((RUN / 'details').glob('*.json')):
                chunk = read(path)
                if chunk['experimentId'] != self.id:
                    raise ValueError('详情与索引版本不一致')
                yield from chunk['records']
        # Reuse the exact layer policy, but retain only prefix memberships globally.
        # Per-character suggestion hints are reconstructed from its detail on demand.
        self.layers = CandidateLayers([])
        for row in details():
            local = CandidateLayers([row])
            for prefix, members in local.entries.items():
                for cp, tier in members.items():
                    self.layers.add(prefix, cp, tier)
        self.audit = read(AUDIT_RUN / '大重码入口与属性复核.json')
        audit = read(RUN / '程序修复与漏收审计.json')
        historical = read(RUN / '历史确认145字逐字核查.json')
        previous = read(AUDIT_RUN / '程序修复与漏收审计.json')
        self.queues = {
            'first': [cp for cp, r in self.rows.items() if not r['codes']],
            'prior': [r['cp'] for r in audit['remaining']],
            'withdrawn': [r['cp'] for r in previous['newlyWithheld']],
            'historical': [r['cp'] for r in historical['records'] if not r['recovered']],
            'affected': [ord(ch) for ch in self.audit['newlyFirstKeyOnlyWithHistoricalFlag']],
            'unclassified': self.unclassified,
        }
        self.queue_reasons = {r['cp']: r.get('triageCategory', '') for r in audit['remaining']}
        self.queue_reasons.update({r['cp']: r['category'] for r in historical['records'] if not r['recovered']})
        self.capacity = read(RUN / '容量与差异报告.json')
        self.keys = []
        buckets = {b['bucket']: b for b in index['bucketGroups']}
        for position in range(1, 5):
            for key in LETTERS:
                definition = ({k: dict(v, meaning=v['coarse'] + {'balanced': '·均衡', 'tall': '·纵长', 'wide': '·横宽', None: ''}[v['proportion']]) for k, v in buckets.items()} if position == 1 else
                              self.definitions[{2: 'families', 3: 'third', 4: 'fourth'}[position]])
                item = dict(definition.get(key, {}))
                cps = self.key_members(position, key)
                if position == 1 and key in self.collections:
                    item = {'meaning': key + ' 保留集合', 'status': 'reserved-collection'}
                    cps = self.collections[key]
                if position == 1 and not item and cps:
                    item = {'meaning': '历史第一位保留（未新定键义）', 'status': 'historical-retained'}
                preferred = [ord(ch) for ch in '○●□■☆★∥=∴∵EFQDTB𐎊•▪◾']
                anchors = [ord(ch) for text in item.get('anchors', []) for ch in text]
                example_cps = list(dict.fromkeys(cp for cp in anchors + preferred if cp in cps))[:8]
                for cp in cps:
                    if len(example_cps) >= 8:
                        break
                    if cp not in example_cps:
                        example_cps.append(cp)
                self.keys.append(dict(item, key=key, position=position, count=len(cps),
                                      assigned=bool(item), examples=[self.brief(cp) for cp in example_cps]))
        deployed = read(PROJECT / '数据/三模式/全形核对版.json')
        self.bootstrap = {'id': self.id, 'sha256': INDEX_SHA, 'run': RUN.name, 'deployed': deployed,
                          'keys': self.keys, 'capacity': self.capacity,
                          'queueCounts': {k: len(v) for k, v in self.queues.items()},
                          'auditVersion': self.audit['after'], 'definitions': self.definitions,
                          'collisions': self.collision_groups(4)}

    def brief(self, cp, allocation=False):
        row = self.rows.get(cp)
        if not row:
            return {'cp': cp, 'char': chr(cp), 'codes': [], 'preferredCodes': [],
                    'reason': '全局未分类；尚无全形编码' if cp in self.unclassified else '保留集合，非普通形族路径'}
        result=dict(row, reason=self.queue_reasons.get(cp, ''))
        if allocation and cp in cleanup_records():
            draft=cleanup_records()[cp]
            result.update(bucket=draft['draftBucket'],familyKey=draft['draftFamily'],
                          codes=sorted(set(row['codes'])|set(draft['newCodes'])),
                          legacyFirstAlias=draft['legacyFirstAlias'],cleanupBasis=draft['allocationBasis'],
                          primaryPending=draft['primaryPending'],draftOnly=True)
            if draft['draftBucket']=='u':
                result['preferredCodes']=['ulki']+[c for c in row['preferredCodes'] if c!='ulki']
        if allocation and (CHVC_RUN/'chvc结构细分与优先级试验.json').is_file():
            trial=chvc_records().get(cp)
            if trial and trial['preferredCodes']:
                result.update(preferredCodes=trial['preferredCodes'],chvcPreferenceApplied=True)
        if allocation and has_centre_trial() and cp in centre_records():
            trial=centre_records()[cp]
            result['codes']=sorted(set(result['codes'])|{p['code'] for p in trial['paths']})
            if trial['preferredCodes']:
                result.update(preferredCodes=trial['preferredCodes'],centrePreferenceApplied=True)
        return result

    def allocation_members(self,prefix):
        members=dict(self.layers.entries.get(prefix,{}))
        if len(prefix)==1 and prefix in 'tujvbg':
            for cp,row in cleanup_records().items():
                if row['legacyFirstAlias']==prefix and not any(c.startswith(prefix) for c in row['oldCodes']):
                    members.pop(cp,None)
        for cp,tier in cleanup_additions().get(prefix,{}).items():
            members[cp]=min(members.get(cp,4),tier)
        if has_centre_trial():
            for cp,tier in centre_additions().get(prefix,{}).items():
                members[cp]=min(members.get(cp,4),tier)
        return members

    def key_members(self, position, key, allocation=False):
        if allocation:
            if position==1:
                return list(self.allocation_members(key))
            original=set(self.key_members(position,key))
            for cp,row in cleanup_records().items():
                if position==2 and any(r['familyKey']==key for r in row['familyRoutes']):original.add(cp)
                elif position>2 and any(len(c)>=position and c[position-1]==key for c in row['newCodes']):original.add(cp)
            if has_centre_trial():
                original|={cp for cp,r in centre_records().items() if any(p['code'][position-1]==key for p in r['paths'])}
            return sorted(original)
        if position == 1:
            return list(self.layers.entries.get(key, {}))
        if position == 2:
            return sorted({cp for prefix, entries in self.layers.entries.items()
                           if len(prefix) == 2 and prefix[1] == key for cp in entries})
        return [cp for cp, r in self.rows.items() if any(len(code) >= position and code[position - 1] == key for code in r['codes'])]

    def collision_groups(self, length, allocation=False):
        if allocation:
            prefixes={p for p in self.layers.entries if len(p)==length}|{p for p in cleanup_additions() if len(p)==length}
            if has_centre_trial():prefixes|={p for p in centre_additions() if len(p)==length}
            return sorted([{'code':p,'count':len(self.allocation_members(p))} for p in prefixes
                           if self.allocation_members(p)],key=lambda x:(-x['count'],x['code']))
        return sorted([{'code': p, 'count': len(v)} for p, v in self.layers.entries.items()
                       if len(p) == length], key=lambda x: (-x['count'], x['code']))

    @functools.lru_cache(maxsize=8)
    def chunk(self, name):
        if not re.fullmatch(r'details/\d{3}\.json', name):
            raise ValueError('无效详情分片')
        d = read(RUN / name)
        if d['experimentId'] != self.id:
            raise ValueError('详情版本不一致')
        return {r['cp']: r for r in d['records']}

    def detail(self, cp, allocation=False):
        row = self.rows.get(cp)
        if not row:
            if cp not in self.unclassified and not any(cp in v for v in self.collections.values()):
                raise ValueError('该码位不在本次核对范围')
            return self.brief(cp)
        detail = self.chunk(row['detailUrl'])[cp]
        if allocation and cp in cleanup_records():
            import copy
            detail=copy.deepcopy(detail)
            draft=cleanup_records()[cp]
            paths={p['code']:p for p in detail['paths']}
            for path in draft['paths']:
                if path['code'] not in paths:paths[path['code']]=copy.deepcopy(path)
                else:
                    for evidence in path['evidence']:
                        if evidence not in paths[path['code']]['evidence']:paths[path['code']]['evidence'].append(evidence)
            if draft['draftBucket']=='u' and 'ulki' in paths:
                paths['ulki']['preferred']=True
                paths['ulki']['preferenceScope']='independent-first-key-draft-only'
            detail.update(bucket=draft['draftBucket'],familyKey=draft['draftFamily'],paths=list(paths.values()),
                          cleanupDraft={k:v for k,v in draft.items() if k not in ('paths','objects','familyRoutes')})
            detail['objects']+=draft['objects'];detail['familyRoutes']+=draft['familyRoutes']
        if allocation and has_centre_trial() and cp in centre_records():
            import copy
            trial=centre_records()[cp];detail=copy.deepcopy(detail)
            existing={p['code'] for p in detail['paths']}
            detail['paths']+=[copy.deepcopy(p) for p in trial['paths'] if p['code'] not in existing]
            if trial['preferredCodes']:
                for p in detail['paths']:
                    p['originalPreferred']=p.get('preferred',False)
                    p['preferred']=p['code'] in trial['preferredCodes']
                detail['centrePreferenceApplied']=True
        if allocation and (CHVC_RUN/'chvc结构细分与优先级试验.json').is_file():
            trial=chvc_records().get(cp)
            if trial and trial['preferredCodes']:
                import copy
                detail=copy.deepcopy(detail)
                for path in detail['paths']:
                    path['originalPreferred']=path.get('preferred',False)
                    path['preferred']=path['code'] in trial['preferredCodes']
                detail['chvcPreferenceApplied']=True
        from shape_candidate_layers import CandidateLayers
        local = CandidateLayers([detail])
        local.entries = {p['code']:self.allocation_members(p['code']) for p in detail['paths']} if allocation else self.layers.entries
        extra = historical_record(cp) if (HISTORICAL_RUN / '历史桶整理与新用途试验.json').is_file() else None
        return dict(detail, suggestions=local.suggestions(cp), historicalPilot=extra,
                    thickForkRepair=thick_records().get(cp) if has_thick_repair() else None,
                    centreTrial=centre_records().get(cp) if has_centre_trial() else None,
                    chvcTrial=chvc_records().get(cp) if (CHVC_RUN/'chvc结构细分与优先级试验.json').is_file() else None,
                    uExpansion=u_expansion_records().get(cp) if (U_EXPANSION_RUN/'u线群全量近似候选.json').is_file() else None,
                    codeCounts={p['code']:len(local.entries[p['code']]) for p in detail['paths']})

    @functools.lru_cache(maxsize=1)
    def allocation_keys(self):
        result=[]
        meanings={'u':'线群／层列·草案','v':'台阶实心块面·草案'}
        for original in self.keys:
            k=dict(original);p,key=k['position'],k['key']
            cps=self.key_members(p,key,True)
            if p==1 and key in 'bgjt':
                k.update(meaning='空键（旧桶已清空）',assigned=False,status='draft-released')
            elif p==1 and key in meanings:
                k.update(meaning=meanings[key],assigned=True,status='independent-draft',condition='仅在独立草案试用；原码表与部署不变')
            elif p==4 and key=='o' and has_centre_trial():
                k.update(centre_trial()['definition'],assigned=True,positive='Y',negative='T')
            if p==1 and key in self.collections:cps=self.collections[key]
            k.update(count=len(cps),examples=[self.brief(cp,True) for cp in cps[:8]])
            result.append(k)
        return result

    def query(self, params):
        get = lambda k, default='': params.get(k, [default])[0]
        prefix, queue, text = get('prefix').lower(), get('queue'), get('text').strip()
        allocation=get('allocation')=='1'
        groups = {}
        trial_records = {}
        if get('thickRepair'):
            cps=thick_members(get('thickRepair'))
        elif get('centre'):
            cps=centre_members(get('centre'))
        elif get('chvcTrial'):
            cps=chvc_members(get('chvcTrial'))
        elif get('uExpansion'):
            cps=u_expansion_members(get('uExpansion'))
        elif get('cleanup'):
            records=cleanup_records();kind=get('cleanup')
            if kind not in ('all','pending','recovered','reviewed','allocated'):
                raise ValueError('未知清空草案队列')
            cps=[cp for cp,r in records.items() if kind=='all' or
                 (kind=='pending' and r['primaryPending']) or (kind=='recovered' and r['newCodes']) or
                 (kind=='reviewed' and r['historicalFirstKeyConfirmed']) or
                 (kind=='allocated' and r['draftBucket'] is not None)]
        elif get('trial'):
            report = historical_pilot()
            trial_records = {r['cp']: r for r in report['records']}
            trial = get('trial')
            if trial == 'history':
                cps = [r['cp'] for r in report['records'] if not get('oldKey') or r['oldBucket'] == get('oldKey')]
            elif trial in ('u', 'v'):
                cps = report['trials'][trial]['cps']
            elif trial == 'existing':
                cps = [r['cp'] for r in report['records'] if r['existingFamilyProbe'] and r['existingFamilyProbe']['stable']]
            elif trial == 'category' and get('category') in report['categories']:
                cps = [r['cp'] for r in report['records'] if r['category'] == get('category')]
            elif trial == 'reviewed':
                cps = [r['cp'] for r in report['records'] if r['historicallyReviewed']]
            else:
                raise ValueError('未知历史桶试验队列')
        elif prefix:
            if not re.fullmatch('[a-z]{1,4}', prefix):
                raise ValueError('编码必须为一至四个字母')
            if prefix in self.collections:
                cps = self.collections[prefix]
            else:
                if allocation:
                    members=self.allocation_members(prefix)
                    groups={name:[cp for cp,tier in members.items() if tier==i] for i,name in enumerate(LAYERS)}
                    cps=[cp for name in LAYERS for cp in groups[name]]
                else:
                    result = self.layers.query(prefix)
                    cps, groups = result['candidates'], result['groups']
        elif queue:
            if queue not in self.queues:
                raise ValueError('未知核对队列')
            cps = self.queues[queue]
            if allocation and queue in ('first','prior','withdrawn','historical'):
                cps=[cp for cp in cps if not self.brief(cp,True)['codes']]
        elif get('position'):
            position, key = int(get('position')), get('key')
            if position not in range(1, 5) or key not in LETTERS or len(key) != 1:
                raise ValueError('无效键位')
            cps = self.collections.get(key, []) if position == 1 and key in self.collections else self.key_members(position, key, allocation)
        else:
            cps = list(self.rows)
            if text:
                cps += self.unclassified + [cp for values in self.collections.values() for cp in values]
        if text:
            match = re.fullmatch(r'(?:U\+|0x)([0-9a-f]{1,6})', text, re.I)
            wanted = {int(match[1], 16)} if match else {ord(ch) for ch in text}
            cps = [cp for cp in cps if cp in wanted]
        offset = max(0, int(get('offset', '0')))
        tier = {cp: name for name, values in groups.items() for cp in values}
        audit = next((g for g in self.audit['groups'] if g['code'] == prefix), None)
        support = set(audit.get('geometrySupportedCPs', [])) if audit else set()
        uncertain = set(audit.get('uncertainRetainedCPs', [])) if audit else set()
        rows = [dict(self.brief(cp,allocation), layer=tier.get(cp),
                     thickRepairStatus=(str(thick_records()[cp]['beforePositiveVariants'])+'/9 → '+str(thick_records()[cp]['afterPositiveVariants'])+'/9') if get('thickRepair') else None,
                     centreStatus=('稳定新增中心码' if centre_records()[cp]['stable'] else '检测未稳定，未加新码') if get('centre') else None,
                     centreCodes=[p['code'] for p in centre_records()[cp]['paths']] if get('centre') else None,
                     chvcPriority=({k:chvc_records()[cp][k] for k in ('status','preferredCodes','stableFeatures','oldPreferredCodes')}
                                   if get('chvcTrial') else None),
                     uExpansionCategory=u_expansion_records().get(cp,{}).get('category') if get('uExpansion') else None,
                     historicalCategory=trial_records.get(cp, {}).get('category'),
                     geometry=('几何证据支持（非人工确认）' if cp in support else
                               '证据待核，保留入口' if cp in uncertain else '本轮未单独复核'))
                for cp in cps[offset:offset + 60]]
        return {'id': self.id, 'allocation':allocation, 'total': len(cps), 'offset': offset, 'rows': rows,
                'groups': {k: len(v) for k, v in groups.items()},
                'audit': ({k: audit[k] for k in ('code', 'geometrySupported', 'uncertainRetained')} if audit else None)}


@functools.lru_cache(maxsize=1)
def get_overview():
    return Overview()


def handle(handler):
    """Return True only for our allowlisted GET routes."""
    url = urlsplit(handler.path)
    if not url.path.startswith('/api/shape-overview/'):
        return False
    params = parse_qs(url.query)
    try:
        with LOCK:
            overview = get_overview()
        endpoint = url.path.removeprefix('/api/shape-overview/')
        if endpoint == 'bootstrap':
            extra = historical_summary() if (HISTORICAL_RUN / '历史桶整理与新用途试验.json').is_file() else None
            draft=cleanup_summary() if (CLEANUP_RUN / '旧桶清空与新键位草案.json').is_file() else None
            payload = dict(overview.bootstrap, historicalPilot=extra,cleanupDraft=draft,
                           chvcTrial=chvc_summary() if (CHVC_RUN/'chvc结构细分与优先级试验.json').is_file() else None,
                           centreTrial=centre_summary() if has_centre_trial() else None,
                           thickForkRepair={k:v for k,v in thick_repair().items() if k not in ('records','protectedHashes')} if has_thick_repair() else None,
                           uExpansion=u_expansion_summary() if (U_EXPANSION_RUN/'u线群全量近似候选.json').is_file() else None,
                           allocationKeys=overview.allocation_keys() if draft else None)
            if draft:
                recovered={cp for cp,r in cleanup_records().items() if r['newCodes']}
                payload['allocationQueueCounts']={k:len(set(v)-recovered) if k in ('first','prior','withdrawn','historical') else len(v)
                                                   for k,v in overview.queues.items()}
        elif endpoint == 'query':
            payload = overview.query(params)
        elif endpoint == 'detail':
            payload = overview.detail(int(params.get('cp', ['-1'])[0]),params.get('allocation',[''])[0]=='1')
        elif endpoint == 'collisions':
            length = int(params.get('length', ['4'])[0])
            if length not in range(1, 5):
                raise ValueError('长度必须为一至四')
            payload = {'groups': overview.collision_groups(length,params.get('allocation',[''])[0]=='1')}
        elif endpoint == 'historical-pilot':
            report = historical_pilot()
            payload = dict(historical_summary(), controls=report['controls'])
        elif endpoint == 'asset' and params.get('id', [''])[0] in HISTORICAL_ASSETS:
            data = (HISTORICAL_RUN / HISTORICAL_ASSETS[params['id'][0]]).read_bytes()
            handler.send_response(200)
            handler.send_header('Content-Type', 'image/png')
            handler.send_header('Content-Length', str(len(data)))
            handler.send_header('Cache-Control', 'no-cache')
            handler.end_headers()
            handler.wfile.write(data)
            return True
        elif endpoint == 'asset' and params.get('id', [''])[0] in ASSETS:
            data = (RUN / ASSETS[params['id'][0]]).read_bytes()
            handler.send_response(200)
            handler.send_header('Content-Type', 'image/png')
            handler.send_header('Content-Length', str(len(data)))
            handler.send_header('Cache-Control', 'no-cache')
            handler.end_headers()
            handler.wfile.write(data)
            return True
        else:
            handler._json(404, {'error': 'not-found'})
            return True
        handler._json(200, payload)
    except (ValueError, OSError, KeyError) as error:
        handler._json(400, {'error': str(error)})
    return True
