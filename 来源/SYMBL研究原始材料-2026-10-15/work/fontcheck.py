import pathlib,re,urllib.request,json
p=pathlib.Path('work');css=(p/'deferred-styles.css').read_text('utf-8');js=(p/'character-table.js').read_text('utf-8')
print('FONT NAMES',re.findall(r'@font-face\{font-family:([^;]+)',css))
for needle in ['_substituteSymbols=','substituteSymbols:','copySymbol','charHtml','_getSymbolsForRender','_countLine=']:
 print('\n',needle)
 for m in list(re.finditer(re.escape(needle),js))[:3]:print(js[max(0,m.start()-150):m.start()+800])
for name in ['u0000','u13000','u1f400']:
 u=f'https://symbl-cdn.com/fonts/u/{name}.woff2'
 try:
  b=urllib.request.urlopen(urllib.request.Request(u,headers={'User-Agent':'Mozilla/5.0','Referer':'https://symbl.cc/'}),timeout=20).read();(p/(name+'.woff2')).write_bytes(b)
  from fontTools.ttLib import TTFont
  f=TTFont(p/(name+'.woff2'));c=f.getBestCmap();print('FONT SAMPLE',name,len(b),len(c),hex(min(c)),hex(max(c)),f['name'].getDebugName(1),f['name'].getDebugName(13))
 except Exception as e:print(name,str(e))
