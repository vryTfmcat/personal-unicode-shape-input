"""Supplement the v6 pixel measurements for the v6.1 boundary corrections."""
from geometry import *
from functools import lru_cache

def symmetry(a):
    return [P["IMAGE"]["iou"](a.astype(bool),b.astype(bool))
            for b in (a[:,::-1],a[::-1,:],a[::-1,::-1])]

def stats_for(mask):
    if not mask.any():
        return None
    yy,xx=np.where(mask)
    x,y,w,h=int(xx.min()),int(yy.min()),int(np.ptp(xx)+1),int(np.ptp(yy)+1)
    a=mask[y:y+h,x:x+w].astype(np.uint8)
    cs,_=cv2.findContours(a,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
    c=max(cs,key=cv2.contourArea)
    hull=cv2.convexHull(c)
    poly=cv2.approxPolyDP(c,max(1.1,.033*cv2.arcLength(c,True)),True)
    v=len(poly)
    rectangle=cv2.contourArea(c)/max(1,w*h)
    def roundn(x):return round(float(x),4)
    return dict(box=[x,y,w,h],polygon=v,extent=roundn(rectangle),ellipse=roundn(circle_score(c,a.shape)),
                convex=roundn(cv2.contourArea(c)/max(1,cv2.contourArea(hull))),sym=[roundn(s) for s in symmetry(a)])

def topology(a):
    padded=np.pad(a,1)
    skeleton=cv2.ximgproc.thinning(padded*255)>0
    core=skeleton[1:-1,1:-1]
    h,w=a.shape
    neighbors=np.stack([skeleton[1+dy:1+dy+h,1+dx:1+dx+w] for dy,dx in
                        ((-1,0),(-1,1),(0,1),(1,1),(1,0),(1,-1),(0,-1),(-1,-1))])
    degree=(neighbors & ~np.roll(neighbors,1,axis=0)).sum(axis=0)
    endpoints=np.argwhere(core & (degree==1))[:,::-1]
    branches=np.argwhere(core & (degree>=3))[:,::-1]
    y,x=np.where(core)
    points=np.column_stack((x,y))
    return endpoints,branches,points

def hinge(ends,pts):
    if len(ends)!=2 or len(pts)<8:
        return []
    a,b=ends.astype(float)
    base=b-a
    norm=np.linalg.norm(base)
    if norm<5:
        return []
    depth=np.abs(base[0]*(pts[:,1]-a[1])-base[1]*(pts[:,0]-a[0]))/norm
    p=pts[np.argmax(depth)]
    u,v=a-p,b-p
    l,r=np.linalg.norm(u),np.linalg.norm(v)
    if min(l,r)<3 or max(depth)<.10*max(l,r):
        return []
    dot=float(np.dot(u,v)/(l*r))
    # Retain a sharp turning point only when the ink follows two coherent arms.
    distances=[]
    for arm,le in ((u,l),(v,r)):
        d=pts-p
        t=np.clip(d@arm/le**2,0,1)
        distances.append(np.linalg.norm(d-t[:,None]*arm,axis=1))
    residual=np.minimum(*distances)
    if np.quantile(residual,.85) > max(1.7,.065*max(l,r)):
        return []
    return [round(dot,3),round(float(min(l,r)/max(l,r)),3),
            direction(*(u/l+v/r)),bool(all(min(abs(t)) <= .32*max(abs(t)) for t in (u,v)))]

def curved_head(a, ends, junctions, pts, m):
    if len(ends)!=3 or not len(junctions) or m["junctions"]>2 or m["hull"]>.65:
        return ""
    scale=max(a.shape)
    options=[]
    for pivot in junctions:
        vec=ends-pivot
        lengths=np.linalg.norm(vec,axis=1)
        order=np.argsort(lengths)
        u,v,tail=vec[order]
        l,r,long=lengths[order]
        if min(l,r)<.08*scale or r>.39*scale or l<.51*r or long<1.33*r:
            continue
        u0,v0=u/l,v/r
        cos=float(u0@v0)
        if not -.83<=cos<=.53:
            continue
        axis=-(u0+v0)
        axis/=np.linalg.norm(axis)
        # The stem leaves the tip between the short wings, and bends away deeper in.
        near=pts-pivot
        axial=near@(-axis)
        perp=np.abs(near@np.array([-axis[1],axis[0]]))
        bridge=np.count_nonzero((axial>=.12*scale)&(axial<=.28*scale)&(perp<=.085*scale))
        bow=np.abs(tail[0]*near[:,1]-tail[1]*near[:,0])/long
        curved=np.quantile(bow,.70)>=.14*scale
        deep=max(m["gaps"])>=.67 and sorted(m["gaps"])[-2]<=.24
        if curved and (bridge>=3 and float((tail/long)@(-axis))>=-.55 or deep and l>=.66*r):
            options.append((min(l,r)/max(l,r),direction(*axis)))
    return max(options)[1] if options else ""

def supplement(gray,t,m):
    a=P["tight_mask"](gray,t)
    h,w=a.shape
    n,labels,stat,_=cv2.connectedComponentsWithStats(a,connectivity=8)
    ids=sorted(range(1,n),key=lambda i:-stat[i,4])
    ix=ids[0]
    bx,by,bw,bh,area=map(int,stat[ix])
    body=(labels[by:by+bh,bx:bx+bw]==ix).astype(np.uint8)
    embed=[i for i in ids[1:] if bx<=stat[i,0] and by<=stat[i,1] and
           stat[i,0]+stat[i,2]<=bx+bw and stat[i,1]+stat[i,3]<=by+bh and stat[i,4]>=2]
    probe=dict(inner=None,hole=None,hinge=[],curved="",bodyGeo=None,rBelow=None,arrowProfile=[])
    if m["arrow"]:
        dx,dy=VECTORS[DIRS.index(m["arrow"][-1])]
        y,x=np.where(a)
        axis=x*dx+y*dy
        across=-dy*x+dx*y
        t0=(axis-axis.min())/max(1,np.ptp(axis))
        width=max(1,np.ptp(across))
        for lo,hi in ((0,.19),(.22,.40),(.43,.58),(.61,.77),(.80,.92),(.92,1.01)):
            z=across[(t0>=lo)&(t0<hi)]
            probe["arrowProfile"].append(round(float(np.ptp(z))/width,4) if len(z) else 0.)
    if embed:
        inner=np.isin(labels,embed).astype(np.uint8)
        data=stats_for(inner)
        x,y,iw,ih=data["box"]
        tile=inner[y:y+ih,x:x+iw]
        e,j,straight,corner,*_=P["line_network"](tile,max(tile.shape))
        data.update(count=len(embed),straight=straight,corners=corner,ends=e,junctions=j,
                    centered=abs(x+iw/2-bx-bw/2)<=.105*bw and abs(y+ih/2-by-bh/2)<=.105*bh)
        probe["inner"]=data
    if m["holesRaw"]==1 and (m["polygon"]==4 or m["circle"]>.92):
        _,white,stats,_=cv2.connectedComponentsWithStats(1-np.pad(a,1),connectivity=4)
        outside=white[0,0]
        hid=max((i for i in range(1,len(stats)) if i!=outside),key=lambda i:stats[i,4],default=0)
        if hid:
            probe["hole"]=stats_for((white[1:-1,1:-1]==hid).astype(np.uint8))
    if m["holesRaw"]==0 and m["components"]==1 and (m["endpoints"] in (2,3) or m["arrow"]):
        ends,junctions,pts=topology(a)
        probe["hinge"]=hinge(ends,pts)
        if m["endpoints"]==3 and min(w,h)>=14:
            probe["curved"]=curved_head(a,ends,junctions,pts,m)
    if len(ids)>1 and not m["holesRaw"] and int(area)>=.58*m["ink"] and any(
       stat[i,4] <= .34*area and max(stat[i,2:4])<=.51*max(w,h) for i in ids[1:]):
        isolated=P["measure"]((1-body)*255,128)
        if isolated:
            iso=supplement((1-body)*255,128,measure((1-body)*255,128,isolated))
            probe["bodyGeo"]=iso
    if m["topBeam"]:
        b=body[max(1,round(.12*bh)):]
        if b.any():
            ys,xs=np.where(b)
            probe["rBelow"]=symmetry(b)+[(float(xs.mean())+.5)/bw,(float(ys.mean())+.5)/len(b)]
    return dict(m,**probe)

