import pathlib,re
p=pathlib.Path('work')
for fn in list(p.glob('*.css'))+[p/'character-table.js',p/'main.js']:
 s=fn.read_text('utf-8');print('\nFILE',fn.name)
 pats= ['@font-face','unicode-range','font-family','character-table__symbol','background-image','fromCodePoint','clipboard','IntersectionObserver','webp','/i/svg','symbl-cdn','/i/','fetch(','ajax'] if fn.suffix=='.js' else ['@font-face','unicode-range','font-family','character-table__symbol']
 for n in pats:
  hits=list(re.finditer(re.escape(n),s)); print(n,len(hits))
  for m in hits[:5]: print(s[max(0,m.start()-130):m.start()+350])
