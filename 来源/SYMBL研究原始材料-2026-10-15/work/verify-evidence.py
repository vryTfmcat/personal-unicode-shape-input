import json,pathlib,re,hashlib
from fontTools.ttLib import TTFont
p=pathlib.Path('work'); js=(p/'character-table.js').read_text('utf-8');css=(p/'deferred-styles.css').read_text('utf-8')
checks={
 'font_bucket_1024': '1024*Math.floor(t/1024)' in js,
 'font_faces_128':len(re.findall('@font-face',css))==128,
 'no_unicode_range_in_downloaded_css':all('unicode-range' not in q.read_text('utf-8') for q in p.glob('*.css')),
 'virtual_dom_mount':'this._renderer.mount(this._countItemsOnScreen)' in js,
 'codepoint_api':'String.fromCodePoint(a)' in js,
 'utf8_html':'charset=utf-8' in (p/'unicode-table.html').read_text('utf-8').lower(),
 'u13000_class':'.u13000{font-family:u13000}' in css,
 'no_u20000_face':'font-family:u20000;' not in css,
}
files=[]
for name in ['unicode-table.html','symbl.css','deferred-styles.css','charcter-card.css','character-table.js','main.js','vendor-core.js','rea-static-evidence.json']:
 b=(p/name).read_bytes();files.append({'file':name,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()})
fonts=[]
for name in ['u0000','u13000','u1f400']:
 q=p/(name+'.woff2');f=TTFont(q);c=f.getBestCmap();fonts.append({'file':q.name,'bytes':q.stat().st_size,'sha256':hashlib.sha256(q.read_bytes()).hexdigest(),'cmap_entries':len(c),'min':hex(min(c)),'max':hex(max(c)),'license_name_13':f['name'].getDebugName(13),'sample_codepoint':{'u0000':'U+0041','u13000':'U+1319F','u1f400':'U+1F514'}[name],'sample_in_cmap':int({'u0000':'0041','u13000':'1319F','u1f400':'1F514'}[name],16) in c})
sections=[]
for n in ['dec2font','_changeClassLink','_renderItem','_resolveRenderCodePoint','_onResizePage','_getSymbolsForRender']:
 i=js.find('key:"'+n+'"');sections.append({'file':'character-table.js','function':n,'character_offset_zero_based':i,'excerpt':js[i:i+800]})
e=json.loads((p/'rea-static-evidence.json').read_text('utf-8'));partial=e['details']['partial_observation']
out={'captured_local_date':'2026-10-15','timezone':'Asia/Shanghai','target':'https://symbl.cc/en/unicode-table/','rea_version':'6.5.0','rea_status':'partial_inventory_only_semantic_analysis_failed','rea_error':{k:e[k] for k in ['error','code','message']},'rea_reason':e['details']['reason'],'rea_evidence_id':partial['evidence_id'],'checks':checks,'source_files':files,'font_samples':fonts,'source_locations':sections,'limitations':['No browser runtime capture: debug browser launch rejected by automatic approval policy.','REA AST analysis unavailable due to Windows native self-test Win32 32 at C:\\ root.','cmap presence does not prove correct visible glyphs or all-platform shaping.','Font CSS face names cover U+0000..U+1FFFF buckets only; no universal Unicode coverage established.']}
(p/'symbl-evidence-summary.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),'utf-8')
print(json.dumps({'checks':checks,'fonts':fonts,'rea_evidence_id':partial['evidence_id']},ensure_ascii=False,indent=2))
assert all(checks.values())
