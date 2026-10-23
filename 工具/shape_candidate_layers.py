"""Lossless candidate layers and contrast-based path suggestions, not deployment."""
from collections import defaultdict
import re


LAYERS = ('primary','component','supplement','pending')


def route_layer(row, route, object_id=None):
    if (route.get('connectedStrokeGroupEvidence') and object_id
            and object_id.endswith(':connected-horizontal-stroke-group')):
        return 1
    if route.get('localBranchProof'):
        return 2
    if route.get('frameEvidence') or route.get('spineEvidence') or route.get('componentEvidence') or route.get('objectPartitionProof') or route.get('reviewedLoopEvidence'):
        return 1
    quality = route.get('lookupEvidence')
    if quality:
        if not quality['verified']:
            return 3
        if object_id and 'verifiedJunctions' in quality:
            match = re.search(r'junction-(\d+)$',object_id)
            if match and int(match.group(1)) not in quality['verifiedJunctions']:
                return 3
        if quality.get('dominantSubject') is False:
            return 2
    if route.get('componentPartitionProof'):
        return 0 if row['familyKey']==route['familyKey'] else 1
    if route['target']=='body':
        if route['familyKey']==row['familyKey'] and not route.get('supplementOnly'):
            return 0
        if route.get('reviewedRetain') or (route['familyKey']=='b' and route.get('supplementOnly')):
            return 1
        if quality and quality['kind']=='hook-ink-prototype' and quality['verified']:
            return 1
        return 2
    return 3


class CandidateLayers:
    def __init__(self, rows):
        self.entries = defaultdict(dict)
        self.paths = {}
        self.characters = {}
        for row in rows:
            cp = row['cp']
            self.characters[cp] = row['char']
            routes = row['familyRoutes']
            lookup = {(r['bucket']+r['familyKey'],r['target']):r for r in routes}
            primary = next((r for r in routes if r['familyKey']==row['familyKey'] and r['bucket']==row['bucket']),None)
            self.add(row['bucket'],cp,route_layer(row,primary) if primary else 3)
            for route in routes:
                code = route['bucket']+route['familyKey']
                self.add(code,cp,route_layer(row,route))
            hints = []
            for path in row['paths']:
                code = path['code']
                tiers = [route_layer(row,lookup[(code[:2],e['familyTarget'])],e['objectId']) for e in path['evidence']]
                tier = min(tiers)
                for length in range(1,len(code)+1):
                    self.add(code[:length],cp,tier)
                hints.append({'code':code,'layer':LAYERS[tier],'preferred':path.get('preferred',False)})
            self.paths[cp] = hints

    def add(self, prefix, cp, tier):
        old = self.entries[prefix].get(cp,4)
        self.entries[prefix][cp] = min(old,tier)

    def query(self, prefix, mode='all'):
        if mode not in ('all','focused'):
            raise ValueError('mode must be all or focused')
        entries = self.entries.get(prefix,{})
        groups = {name:[cp for cp,tier in entries.items() if tier==i] for i,name in enumerate(LAYERS)}
        all_candidates = [cp for name in LAYERS for cp in groups[name]]
        focused = groups['primary']+groups['component']
        return {'prefix':prefix,'mode':mode,'candidates':all_candidates if mode=='all' else focused,
                'groups':groups,'allCount':len(all_candidates),'focusedCount':len(focused),
                'supplementCount':len(groups['supplement']),'pendingCount':len(groups['pending']),
                'scope':'proposed-view-policy; all mode retains every candidate'}

    def suggestions(self, cp, limit=3):
        choices = [dict(p,allCandidates=len(self.entries[p['code']])) for p in self.paths.get(cp,[])
                   if p['layer'] in ('primary','component')]
        choices.sort(key=lambda p:(p['allCandidates'],not p['preferred'],-len(p['code']),p['code']))
        preferred=next((p for p in choices if p['preferred']),None)
        if preferred:
            choices=[preferred]+[p for p in choices if p is not preferred]
        return choices[:limit]


if __name__=='__main__':
    import argparse
    import json
    from pathlib import Path
    from shape_keyboard_trial import load
    p=argparse.ArgumentParser()
    p.add_argument('--run',type=Path,required=True)
    p.add_argument('--query',required=True)
    p.add_argument('--mode',choices=('all','focused'),default='all')
    p.add_argument('--limit',type=int,default=20)
    args=p.parse_args()
    rows=(row for path in sorted((args.run/'details').glob('*.json')) for row in load(path)['records'])
    index=CandidateLayers(rows)
    result=index.query(args.query,args.mode)
    result['preview']=[index.characters[cp] for cp in result.pop('candidates')[:args.limit]]
    result['groupCounts']={key:len(value) for key,value in result.pop('groups').items()}
    print(json.dumps(result,ensure_ascii=False))
