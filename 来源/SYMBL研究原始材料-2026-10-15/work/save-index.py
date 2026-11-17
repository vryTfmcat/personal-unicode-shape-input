from pathlib import Path
import hashlib,json
p=Path(r'C:\Users\86137\Documents\Codex\Obsidian\Obsidian-codx\70_unicode\个人Unicode音型输入法')
f=p/'个人Unicode音型输入法.md';s=f.read_text('utf-8');entry='- [[来源/SYMBL字符显示实现分析-REA参考-2026-10-15|SYMBL 字符显示实现分析（REA 参考）]]\n';anchor='- [[来源/来源范围与综述]]\n'
if entry not in s:
 assert anchor in s
 f.write_text(s.replace(anchor,anchor+entry,1),'utf-8')
name='SYMBL字符显示实现分析-REA参考-2026-10-15.md'
assert (p/'来源'/name).read_bytes()==(Path('outputs')/name).read_bytes()
e=json.loads(Path('outputs/SYMBL字符显示-证据-2026-10-15.json').read_text('utf-8'))
assert all(e['checks'].values())
print('Verified report copies, 8 source checks, and project index link.')
