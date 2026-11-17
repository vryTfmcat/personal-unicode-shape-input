import pathlib,re
p=pathlib.Path('work');js=(p/'character-table.js').read_text('utf-8');css=(p/'deferred-styles.css').read_text('utf-8')
for needle in ['key:"_updateItem"','key:"_changeClassLink"','key:"_getSymbolsForRender"','key:"_onResizePage"','key:"mount"']:
 i=js.find(needle); print(needle,js[i:i+1700] if i>=0 else 'absent')
i=js.find('m.innerHTML');print('INNERHTML',js[max(0,i-500):i+700])
for rule in re.findall(r'[^{}]*character-table__char[^{}]*\{[^}]*\}',css):print(rule)
