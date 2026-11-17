import urllib.request, pathlib, re
p=pathlib.Path('work')
u='https://symbl.cc/en/unicode-table/'
r=urllib.request.urlopen(u,timeout=30)
b=r.read(); (p/'unicode-table.html').write_bytes(b)
s=b.decode('utf-8'); print('headers',dict(r.headers));print('bytes',len(b))
for x in re.findall(r'<(?:link|script)\b[^>]*>',s):
 if 'stylesheet' in x or 'src=' in x: print(x)
print('sample',s[s.find('unicode-table'):s.find('unicode-table')+100])
