"""Additional measurements for arrow tips, physical dots and compound geometry."""
import sys
from pathlib import Path
from collections import deque
OUT=Path(__file__).resolve().parent
PREV=OUT.parent/"整体重规划-20261125-v6.1-BCD纠偏与T1落地"
sys.path.insert(0,str(PREV))
from run61 import P,LEDGER,SCAN,INDEX
from pixels61 import topology,stats_for,np,cv2,outline,font_path,BoundsPen,direction,checksummed,font_manifest

def arrow_measure(mask,m):
    ends,forks,points=topology(mask)
    scale=max(mask.shape)
    h,w=mask.shape
    options=[]
    graph={tuple(p) for p in points}
    for fork in forks:
        if len(ends)!=3:
            break
        delta=ends-fork
        lengths=np.linalg.norm(delta,axis=1)
        order=np.argsort(lengths)
        a,b,c=delta[order]
        l,r,t=lengths[order]
        if not (.06*scale<=l<=r<=.43*scale and t>=1.25*r and l>=.48*r):
            continue
        u,v=a/l,b/r
        polar=float(u@v)
        if not -.86<polar<.56:
            continue
        if min(fork[0]/w,fork[1]/h,1-fork[0]/w,1-fork[1]/h)>.24:
            continue
        root=tuple(fork)
        goal=tuple(ends[order[-1]])
        pending=deque([root])
        came={root:None}
        while pending and goal not in came:
            x,y=pending.popleft()
            for dx,dy in ((1,0),(-1,0),(0,1),(0,-1),(1,1),(1,-1),(-1,1),(-1,-1)):
                nxt=(x+dx,y+dy)
                if nxt in graph and nxt not in came:
                    came[nxt]=(x,y)
                    pending.append(nxt)
        if goal not in came:
            continue
        path=[]
        node=goal
        while node is not None:
            path.append(node)
            node=came[node]
        path.reverse()
        if len(path)<.38*scale:
            continue
        k=max(3,min(len(path)-1,round(.23*scale)))
        tangent=fork-np.array(path[k])
        normal=np.linalg.norm(tangent)
        if normal<=2:
            continue
        axis=-(u+v)
        if float(axis@tangent)<-.28*normal:
            continue
        # Shaft direction immediately before the point predominates over style
        # differences in the lengths of the two arrowhead wings.
        axial=1.65*tangent/normal+.35*axis/np.linalg.norm(axis)
        path_pts=np.asarray(path)
        bow=np.abs(c[0]*(path_pts[:,1]-fork[1])-c[1]*(path_pts[:,0]-fork[0]))/t
        curved=float(np.quantile(bow,.72))>=.10*scale
        options.append((l/r,direction(*axial),curved))
    if options:
        _,key,curve=max(options)
        return key,curve
    return "",False

def font_evidence(cp,face,hashes):
    if not face:
        return None
    font=outline(font_path(face,hashes))
    glyph=font.getBestCmap().get(cp)
    if not glyph:
        return None
    gs=font.getGlyphSet()
    pen=BoundsPen(gs)
    gs[glyph].draw(pen)
    if not pen.bounds:
        return None
    x,y,a,b=pen.bounds
    return round(max(a-x,b-y)/font["head"].unitsPerEm,4)

def extra(gray,t,m,em):
    mask=P["tight_mask"](gray,t)
    h,w=mask.shape
    holes=m["holesRaw"]
    arrowTip,curve="",False
    if holes<=1 and m["components"]==1 and m["endpoints"]==3 and m["junctions"] in (1,2) and min(h,w)>=12:
        arrowTip,curve=arrow_measure(mask,m)
    feet=False
    stem=None
    if holes in (1,2):
        body=mask
        col=np.mean(body,axis=0)
        ids=np.flatnonzero(col>=.78)
        if len(ids):
            stem=float(ids.mean()+.5)/w
        if holes==1 and m["hole"] and m["hole"]["polygon"]==3 and m["attrs"][0]>=.81:
            z=round(.84*h)
            avg=body[z:].mean(axis=0)
            if avg[:w//3].max(initial=0)>=.35 and avg[-w//3:].max(initial=0)>=.35 and \
               avg[w//3:2*w//3].mean()<=.10:
                feet=True
    checker=0.
    if holes==2 and m["components"]<=2 and min(h,w)*5>=4*max(h,w) and m["attrs"][2]>=.87:
        norm=cv2.resize(mask,(32,32),interpolation=cv2.INTER_NEAREST_EXACT).astype(bool)
        for n in (2,4):
            units=np.arange(32)//(32//n)
            pattern=(units[:,None]+units[None,:])%2==0
            checker=max(checker,float(np.mean(norm==pattern)),float(np.mean(norm==~pattern)))
    folded=False
    if holes==2 and m["components"]==1 and m["polygon"] in (3,4) and m["type4"]!="diamond" and m["ink"]>=.70*w*h:
        cs,_=cv2.findContours(mask,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
        perimeter=cv2.arcLength(cs[0],True)
        cut=cv2.approxPolyDP(cs[0],max(1.0,.014*perimeter),True)
        folded=len(cut)>=7 and m["attrs"][2]>=.76
    return dict(tip62=arrowTip,curve62=curve,stem62=stem,feet62=feet,checker62=checker,
                inverse62=folded,em62=em)

