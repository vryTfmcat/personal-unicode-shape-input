import urllib.request, pathlib, re, concurrent.futures
p=pathlib.Path('work');s=(p/'unicode-table.html').read_text('utf-8')
us=sorted(set(re.findall(r'https://symbl-cdn.com/[^"<> ]+\.(?:css|js)(?:\?[^"<> ]*)?',s)))
def get(u):
 b=urllib.request.urlopen(u,timeout=30).read(); f=p/u.split('/')[-1].split('?')[0]; f.write_bytes(b);return (f.name,len(b))
for r in concurrent.futures.ThreadPoolExecutor(6).map(get,us):print(r)
for fn in p.glob('*.css'):
 t=fn.read_text('utf-8');print('\nCSS',fn.name)
 for m in re.finditer(r'@font-face|unicode-range|font-family',t):print(t[max(0,m.start()-70):m.start()+240])
