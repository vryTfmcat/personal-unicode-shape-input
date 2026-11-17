from pathlib import Path
from fontTools.ttLib import TTFont
for p in Path('work').glob('u*.woff2'):
 f=TTFont(p);c=f.getBestCmap(); print(p.name,'bytes',p.stat().st_size,'cmap',len(c),'minmax',hex(min(c)),hex(max(c)),'family',f['name'].getDebugName(1),'license',f['name'].getDebugName(13))
