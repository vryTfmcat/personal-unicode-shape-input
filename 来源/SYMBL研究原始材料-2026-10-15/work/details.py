import pathlib,re,json
p=pathlib.Path('work');s=(p/'deferred-styles.css').read_text('utf-8')
for pat in [r'\.u0000[^}]*}',r'\.u13000[^}]*}',r'\.u1d400[^}]*}',r'\.u[0-9a-f]+[^}]*}',r'@font-face[^}]*}']:
 hits=re.findall(pat,s);print(pat,len(hits));print('\n'.join(hits[:4]))
s=(p/'character-table.js').read_text('utf-8')
for n in ['dec2font','_getSymbolModel','substitute','_render','charHtml','requestAnimationFrame','scroll','rowHeight','_rows','_getSymbolHref']:
 print('\nJS',n)
 for m in list(re.finditer(re.escape(n),s))[:4]:print(s[max(0,m.start()-220):m.start()+1000])
s=(p/'unicode-table.html').read_text('utf-8')
print('HEADER',s[:400]);m=s.find('data-blocks-table');print('AFTER BLOCK JSON',s[s.find('data-text-private',m):s.find('data-text-private',m)+1800])
