"""Geometry-only corrections and independent B/C/D assignment."""
from rules import NAMES,D_KEYS,accessory_and_layout,bias,cardinal,closed_rows,loop,no_loop
from geometry import direction

ATTACH={"B":"BM","M":"MF","N":"NG","C":"CI","G":"GG","H":"HH","I":"IF","Y":"YP"}

def refined_frame(m):
    oval=m["circle"]>=.925 and m["hull"]>.90
    rect=m["polygon"]==4 and m["type4"]=="axis" and m["hull"]>=.92
    regular=oval or rect or m["polygon"] in (3,4) and m["hull"]>=.92 and m["contourStraight"]>=.72
    hole=m["hole"]
    inner=m["inner"]
    if regular and inner and m["holesRaw"]:
        iw,ih=inner["box"][2:]
        _,_,w,h,_=m["body"]
        fraction=max(iw/w,ih/h)
        lr,ud,rot=inner["sym"]
        balanced=inner["count"]==1 and inner["centered"]
        round_dot=inner["ellipse"]>=.90 and inner["convex"]>=.89 and inner["ends"]<=1
        core=balanced and inner["junctions"]==0
        geometric=""
        if core and (round_dot and fraction<=.29 or inner["ends"]==0 and min(lr,ud)>=.84 and fraction<=.59 and
                     (inner["ellipse"]>=.91 or inner["polygon"]==4 and inner["extent"]>=.80)):
            geometric="A"
        elif core and inner["straight"]>=.90 and inner["corners"]==0 and inner["ends"]==2 and max(iw,ih)>=3*min(iw,ih):
            geometric="B"
        elif balanced and inner["junctions"]>=1 and inner["ends"]>=4 and (min(lr,ud)>=.80 or rot>=.88):
            geometric="C"
        elif balanced and rot>=.82 and inner["polygon"] in (3,4) and inner["convex"]>=.90 and inner["straight"]>=.87:
            geometric="D"
        if geometric:
            return "X"+(geometric if oval else chr(ord(geometric)+4) if rect else "I")
        complex_inside=inner["count"]>1 or inner["junctions"]>=2 or m["inside"][-2]>=2.75
        return "W"+(("B" if complex_inside else "A") if oval else ("D" if complex_inside else "C") if rect else "E")
    if rect and hole and not inner:
        px,py=m["positions"][0]
        if hole["polygon"] in (3,4) and hole["convex"]>=.93 and bias(px,py,.14) and .38<=m["darkBody"]<=.87:
            return "LL"
        if hole["convex"]<.83 or hole["polygon"]>=6 and hole["ellipse"]<.80:
            return "WC"
    if not regular and m["nested"] and inner and (inner["junctions"]>=1 or inner["ends"]>=3 or m["junctions"]>=5):
        return "SF"
    return ""

def angular(m):
    bent=m["hinge"]
    if not bent or m["holesRaw"] or m["components"]!=1:
        return ""
    dot,balance,key,axis=bent
    if axis and abs(dot)<=.28:
        return "B"+dict(K="A",J="B",M="C",N="D").get(key,"K")
    if dot>=.06 and balance>=.29 and m["strokeWidth"]<=.24:
        if key in ("J","K","N","M") and balance<.60:
            return "B"+dict(K="A",J="B",M="C",N="D")[key] if dot<=.34 and m["straight_ratio"]>=.92 and key=="N" and balance>=.47 else "BK"
        return "B"+dict(W="E",S="F",D="G",A="H").get(key,"K")
    return ""

def shaft(m):
    raw=m["arrow"]
    if not raw or not m["arrowProfile"]:
        return "", ""
    kind,key=raw
    rear,shaft,neck,head,flank,tip=m["arrowProfile"]
    w,h=m["size"]
    lr,ud,rot=m["attrs"][:3]
    sym=ud if key in "AD" else lr
    diagonal=key in "JKNM"
    if kind=="H" and not diagonal and sym>=.80 and m["hull"]>=.61:
        return "PH",key
    if m["hinge"] or m["rays"]>=4 and diagonal or diagonal and m["junctions"]>=2 or diagonal and m["strokeWidth"]>.23:
        return "", ""
    if not diagonal and sym>=.81 and .20<=m["strokeWidth"]<=.52 and .63<=m["hull"]<=.85 and \
       neck>=.87 and max(rear,shaft)<=.64 and neck-tip>=.58:
        return "P"+kind,key
    peak=max(neck,head,flank)
    if shaft<=.35 and (peak>=1.8*max(.06,shaft) or peak-min(rear,shaft)>=.40) and \
       tip<=.58 and (diagonal or sym>=.865 and (tip<.22 or tip<1.07*max(shaft,.13))) and \
       not (m["endpoints"]>=4 and m["junctions"]==1 and abs(tip-shaft)<.06 and neck>=.86) and \
       (not m["holesRaw"] or kind=="D" and sym>=.82):
        return "P"+kind,key
    if kind=="D" and not diagonal and sym>=.85 and neck>=.72 and tip<=.55 and min(rear,shaft)<=.53:
        return "PD",key
    return "", ""

def arrow61(m):
    if m["curved"]:
        return "PF",m["curved"]
    p=shaft(m)
    if p[0]:
        return p
    lr,ud,rot=m["attrs"][:3]
    g=m["gaps"]
    i=max(range(4),key=g.__getitem__)
    if m["components"]==1 and not m["holesRaw"]:
        if m["endpoints"]==3 and m["junctions"]==1 and g[i]>=.86 and sorted(g)[-2]<=.12 and \
           .25<=m["hull"]<=.41 and .05<=m["strokeWidth"]<=.15 and m["lineLength"]>=2.25:
            return "PF",("A" if m["slope"]<0 else "D") if i>=2 else ("W" if m["bend"]>0 else "S")
        if .33<=m["hull"]<=.56 and m["polygon"]>=5 and m["strokeWidth"]>=.105 and \
           m["endpoints"]==2 and m["straight_ratio"]<=.55 and g[i]>=.66 and g[i^1]<=.08 and \
           (ud if i<2 else lr)>=.66 and m["shape"]==0:
            return "PD","ADSW"[i]
        if .25<=m["hull"]<=.54 and m["polygon"] in (5,6) and rot>=.86 and m["elongation"]>=2.8 and \
           m["endpoints"]>=4 and not m["centeredJunction"]:
            w,h=m["size"]
            return "PC","D" if w>=h*1.6 else "W" if h>=w*1.6 else "K" if m["slope"]<0 else "M"
    if m["components"]==2 and m["endpoints"]>=6 and m["junctions"]>=2 and m["straight_ratio"]>=.69 and \
       .30<=m["hull"]<=.56 and max(lr,ud,rot)>=.87:
        if all(p[2]>=2*p[3] for p in m["boxes"]):return "PG","D"
        if all(p[3]>=2*p[2] for p in m["boxes"]):return "PG","W"
    return "", ""

def main_shape(m,layouts,extra):
    holes=m["holesRaw"]
    base=refined_frame(m)
    if base:
        return base,""
    p,pdir=arrow61(m)
    if p:
        return p,pdir
    if not holes and m["rays"]>=5 and m["endpoints"]>=5 and m["junctions"]>=1 and \
       m["straight_ratio"]>=.72 and (max(m["attrs"][:3])>=.83 or m["strokeWidth"]<=.24):
        return ("OE" if m["rays"]>=8 else "OD"),""
    _,_,w,h,_=m["body"]
    e,j=m["endpoints"],m["junctions"]
    if not holes and m["components"]==1 and m["hull"]>=.91 and m["polygon"]==4 and \
       (m["elongation"]>=4 or min(w,h)*5<=2*max(w,h)) and m["straight_ratio"]>=.87:
        return ("QB" if h>=w else "QA"),""
    bend=angular(m)
    if bend:
        return bend,m["hinge"][2]
    if not holes and m["components"]==1 and e in (2,3) and j<=1:
        g=m["gaps"]
        i=max(range(4),key=g.__getitem__)
        if g[i]>=.50 and g[i^1]<=.19 and (m["attrs"][1 if i<2 else 0]>=.70 or g[i]>=.74 and sorted(g)[-2]<=.19) and \
           m["hull"]<=.81 and m["rays"]<3:
            return "C"+"ABCD"[i],"DAWS"[i]
    if extra and m["bodyGeo"]:
        sub,_=main_shape(m["bodyGeo"],[],False)
        if sub and sub[0] in ATTACH:
            return ATTACH[sub[0]],""
        if sub:
            return sub,""
    stem_bar=holes==1 and m["midBranch"] and m["midBands"] and j>=1 and m["stems"] and not m["inside"]
    dot_pair=len(m["boxes"])==3 and layouts and layouts[0][0]=="TC" and \
             5*m["body"][3]<m["body"][2] and min(m["attrs"][:2])>=.87
    old=closed_rows(m,extra) if not stem_bar and not dot_pair else ""
    # Keep the original positive frame checks, but avoid inheriting permissive
    # detached-interior and thin-radial fallbacks.
    if old=="LJ" and not (m["straight_ratio"]>=.78 and m["contourStraight"]>=.78 and m["circle"]<.85 and
                           not (holes and e==1 and j==1 and m["darkBody"]<.65)):
        old=""
    if old=="LK" and m["rays"]>=5 and e>=5:
        old=""
    if old:
        return old,m["tip"] if old[0]=="L" and old[1] in "ABCD" else ""
    if m["components"]>=3 and not m["inside"] and m["boxes"][0][4]<=.60*m["ink"] and \
       sum(a[3]>=.83*m["size"][1] and a[2]<=.27*m["size"][0] for a in m["boxes"])==2 and \
       m["attrs"][0]>=.64 and m["straight_ratio"]<=.74:
        return "WF",""
    if holes:
        if m["topBeam"] and m["body"][3]>=.75*m["size"][1] and j>=3 and holes<=2 and not m["inside"]:
            return "RD",""
        return loop(m,extra)
    if dot_pair:
        return "UC","X"
    sub,hint=no_loop(m,extra)
    if sub in ("BE","BF","BG","BH") and (not m["hinge"] or m["hinge"][1]<.43):
        return "BK",hint
    return sub,hint

def symmetry(values,threshold=.81):
    lr,ud,rot=values[:3]
    if min(lr,ud)>=threshold:return "G"
    if lr>=threshold+.025:return "L"
    if ud>=threshold+.025:return "U"
    if rot>=threshold+.025:return "R"
    return ""

def attribute(m,primary,hint,position):
    family=primary[0]
    holes=m["holesRaw"]
    sym=symmetry(m["attrs"])
    x,y=m["attrs"][3:5]
    closed="E" if m["parallel"] and holes>=2 else ("C" if holes else "P") if position else ("H" if holes else "B")
    count="F" if m["components"]<2 else "V" if m["components"]==2 else "X" if m["components"]==3 else "Q"
    tilt="T" if m["skew"]>=14 and m["elongation"]>=1.65 else ""
    if family in "ALWX":
        return "I" if primary=="AF" else closed
    if family in "BCPFJN":
        return hint or sym or bias(x,y,.06) or tilt or "F"
    if family in "STUV":
        return hint or count
    if family=="R":
        below=m["rBelow"] or m["attrs"]
        orient=bias(*below[3:5],.055)
        orient={"W":"","K":"D","J":"A"}.get(orient,orient)
        return symmetry(below) or orient or ("E" if m["parallel"] else "") or tilt or count
    if primary=="EF":
        return "E"
    dominant=bias(x,y,.06)
    if not dominant and family in "HEGYDIK" and max(m["attrs"][:3]) < .80:
        dominant=bias(x,y,.04)
        if not dominant:
            gaps=m["gaps"]
            dx,dy=gaps[1]-gaps[0],gaps[3]-gaps[2]
            if max(abs(dx),abs(dy))>=.17:
                dominant=direction(dx,dy) if min(abs(dx),abs(dy))>=.50*max(abs(dx),abs(dy)) else direction(
                    dx if abs(dx)>abs(dy) else 0,dy if abs(dy)>=abs(dx) else 0)
    return sym or dominant or tilt or count

def classify(m,position=""):
    if m is None:
        return "ZAZ",[],[]
    layouts=accessory_and_layout(m)
    extra=any(bc[0]=="T" for bc,d in layouts)
    primary,hint=main_shape(m,layouts,extra)
    if layouts and (not primary or not extra and primary[0] not in "WXS" and not m["holesRaw"] and
                    m["boxes"][0][4]<.65*m["ink"] and layouts[0][0][0] in "SUV"):
        primary,hint=layouts[0]
    if not primary:
        return "ZBZ",[],[]
    d=attribute(m,primary,hint,position)
    second=[bc+key for bc,key in layouts if bc!=primary]
    for key in (position if primary[0]=="A" else "",hint if primary[0] in "ALWX" else "",
                symmetry(m["attrs"]) if primary[0] in "ALWX" else "",
                "B" if primary[0]=="P" and m["darkBody"]>.38 else ""):
        if key and key!=d:
            second.append(primary+key)
    ranks=list(dict.fromkeys([primary[0]]+[c[0] for c in second]))[:2]
    return primary+d,list(dict.fromkeys(second)),ranks

