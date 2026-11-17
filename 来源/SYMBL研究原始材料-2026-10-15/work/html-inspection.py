import pathlib,re,urllib.request,concurrent.futures
p=pathlib.Path('work');s=(p/'unicode-table.html').read_text('utf-8')
for needle in ['<meta charset','font','<svg','<img','data-code','char-list','unicode-table','data-char','data-symbol','symbol-cell']:
 print('\nNEEDLE',needle)
 hits=list(re.finditer(re.escape(needle),s)); print('count',len(hits))
 for m in hits[:4]: print(s[max(0,m.start()-100):m.start()+350])
us=sorted(set(re.findall(r'https://symbl-cdn.com/[^"<> ]+\.(?:css|js)(?:\?[^"<> ]*)?',s)))
def get(u):
 try:
  r=urllib.request.urlopen(urllib.request.Request(u,headers={'User-Agent':'Mozilla/5.0','Referer':'https://symbl.cc/'}),timeout=25);b=r.read();f=p/u.split('/')[-1].split('?')[0];f.write_bytes(b);return(f.name,len(b))
 except Exception as e:return (u,str(e))
for r in concurrent.futures.ThreadPoolExecutor(6).map(get,us):print(r)
