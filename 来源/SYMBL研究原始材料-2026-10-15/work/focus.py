import pathlib,re,html,json
p=pathlib.Path('work');css=(p/'deferred-styles.css').read_text('utf-8');js=(p/'character-table.js').read_text('utf-8');s=(p/'unicode-table.html').read_text('utf-8')
for n in ['u0000','u13000','u1d400','u1f800','u20000']:
 hits=re.findall(r'[^{}]*\b'+n+r'\b[^{}]*\{[^}]*\}',css);print(n,'\n'.join(hits))
for n in ['key:"dec2font"','key:"_renderSymbol"','key:"_buildSymbolModel"','key:"_rerenderTable"','key:"_resolveRenderCodePoint"','key:"_renderLine"']:
 i=js.find(n);print('\n',n,i,js[i:i+1800] if i>=0 else '')
print('\nHTML DATA')
for k,v in re.findall(r'(data-[\w-]+)="([^"]*)"',s):
 if any(x in k for x in ['symbol','blocks-table']):
  value=html.unescape(v)
  if len(value)>400: print(k,len(value),value[:170])
  else:print(k,value)
print('\nFONT COUNT',len(re.findall('@font-face',css)))
