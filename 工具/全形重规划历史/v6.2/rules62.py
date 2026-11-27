"""v6.2 BCD geometry and D direction contract."""
from pixels62 import direction
from rules61 import classify as previous, accessory_and_layout, arrow61, symmetry, bias, loop, ATTACH
from rules import NAMES,D_KEYS

ATTACHED={"AG","LN","DI","FI","JH","KG","EG",*ATTACH.values()}
OPPOSITE=dict(zip("WASDJKNM","SDWAMN KJ".replace(" ","")))
# W↔S, A↔D, J↔M, K↔N.
BC_BEARING={"BA":"N","BB":"M","BC":"J","BD":"K","BE":"S","BF":"W","BG":"A","BH":"D",
            "CA":"A","CB":"D","CC":"S","CD":"W","CE":"A","CF":"D","CG":"S","CH":"W",
            "IA":"W","IB":"S","IC":"A","ID":"D"}
DIR_SET=set("WASDJKNM")

def attachment(m):
    x,y,w,h,area=m["body"]
    small=[]
    for a,b,c,d,n in m["boxes"][1:]:
        separated=a+c<=x+1 or x+w<=a+1 or b+d<=y+1 or y+h<=b+1
        if separated and n<=.37*area and max(c,d)<=.55*max(m["size"]):
            dx=(a+c/2-x-w/2)/w
            dy=(b+d/2-y-h/2)/h
            if a>=x and a+c<=x+w and abs(dx)<.25:
                dx=0
            if b>=y and b+d<=y+h and abs(dy)<.25:
                dy=0
            small.append((dx,dy,n))
    if not small:
        return ""
    if any(dy<-.45 for _,dy,_ in small) and any(dy>.45 for _,dy,_ in small):
        return "V"
    weight=sum(n for _,_,n in small)
    dx=sum(a*n for a,_,n in small)/weight
    dy=sum(b*n for _,b,n in small)/weight
    if abs(dx)<.36*abs(dy):
        dx=0
    if abs(dy)<.36*abs(dx):
        dy=0
    return direction(dx,dy)

def arrow(m):
    code,hint=arrow61(m)
    if not code:
        return "",""
    lr,ud,rot=m["attrs"][:3]
    if code=="PF":
        if m["tip62"] and m["curve62"]:
            hint=m["tip62"]
            if hint in "WS" and m["shape"]==1 and m["elongation"]>=3 and m["skew"]>=22:
                horizontal=(m["slope"]>0)==(hint=="S")
                hint={("W",True):"K",("W",False):"J",("S",True):"M",("S",False):"N"}[hint,horizontal]
            return code,hint
        # For a nearly complete ring the thinned tip may merge into the arc.
        # A very deep single aperture and one short three-ended fork supports the case.
        g=m["gaps"]
        if m["endpoints"]==3 and m["junctions"]==1 and max(g)>=.86 and sorted(g)[-2]<=.12 and \
           .25<=m["hull"]<=.41 and .05<=m["strokeWidth"]<=.15 and m["lineLength"]>=2.25:
            return code,hint
        return "",""
    if m["holesRaw"]>2 or (m["components"]==1 and m["junctions"]>=5):
        return "",""
    if code in ("PA","PB","PD") and m["arrowProfile"]:
        rear,stem,neck,head,flank,tip=m["arrowProfile"]
        if max(lr,ud,rot)>=.84 and abs(neck-head)<=.08 and abs(rear-tip)<=.045 and abs(stem-flank)<=.095:
            return "",""
        if code=="PB" and (m["shape"]!=0 or m["elongation"]<1.66 or tip>.45):
            return "",""
        if code=="PA" and m["endpoints"]==2 and m["junctions"]==0 and not m["tip62"]:
            return "",""
    return code,hint

def ring_in_ring(m):
    n=m["inner"]
    return (m["components"]==2 and m["holesRaw"]==2 and m["circle"]>=.93 and m["hull"]>=.94 and n and
            n["count"]==1 and n["centered"] and n["ends"]==0 and n["junctions"]==0 and
            min(n["sym"][:2])>=.86 and n["ellipse"]>=.91 and n["convex"]>=.92 and
            all(max(abs(x-.5),abs(y-.5))<=.12 for x,y in m["positions"]))

def frame_two(m):
    holes=m["positions"]
    if m["holesRaw"]!=2 or m["components"]!=1 or m["hull"]<.94 or m["endpoints"]>2 or m["junctions"]<2 or m["darkBody"]>.61:
        return ""
    (x,y),(u,v)=holes
    if min(abs(x-u),abs(y-v)) > .10:
        return ""
    if m["polygon"]==3 and m["straight_ratio"]>=.83:
        return "XI"
    if m["polygon"]==4 and m["type4"]=="axis" and m["straight_ratio"]>=.80:
        return "XF"
    if m["circle"]>=.95 and (m["straight_ratio"]>=.55 and (m["attrs"][0]>.84 or m["attrs"][1]>.84)):
        return "XB"
    return ""

def compact_marks(m):
    if m["holesRaw"]:
        return ""
    if m["components"]==1 and m["em62"] is not None and m["em62"]<=.29 and m["circle"]>=.91 and \
       m["hull"]>=.93 and min(m["attrs"][:2])>=.86:
        return "QE"
    if m["components"]==2 and m["endpoints"]<=4 and m["junctions"]==0:
        q,r=m["boxes"]
        if r[4]>=.80*q[4] and max(q[2:4])<=1.45*min(q[2:4]) and max(r[2:4])<=1.45*min(r[2:4]) and \
           (q[4]+r[4])<=.56*m["size"][0]*m["size"][1] and m["attrs"][2]>=.78:
            return "QF"
    return ""

def pointed_angle(m):
    g=m["gaps"]
    i=max(range(4),key=g.__getitem__)
    reflected=m["attrs"][1 if i<2 else 0]
    if m["components"]==1 and not m["holesRaw"] and m["polygon"]==3 and m["endpoints"] in (2,3) and \
       g[i]>=.44 and reflected>=.67 and g[i]-min(g)>=.19 and .28<=m["hull"]<=.62:
        return "B"+"GHEF"[i]
    return ""

def primary(m,prev):
    code=prev[:2]
    holes=m["holesRaw"]
    p,h=arrow(m)
    if p:
        return p,h
    if code[0]=="P":
        w,h=m["size"]
        if m["verticalStems"] and holes==0 or (m["stems"] and holes==0 and max(m["gaps"])>=.37):
            return ("HC" if m["attrs"][3]>=.54 else "HB"),""
        if holes==0:
            return "YE",""
        fallback,hint=loop(m,False)
        return fallback or "ZB",hint
    if m["inverse62"]:
        return "XC",""
    if m["checker62"]>=.91:
        return "LO",""
    outer=frame_two(m)
    if outer:
        return outer,""
    if ring_in_ring(m):
        return "XA",""
    if code in ("WB","WD") and m["hole"] and m["inner"] and m["inner"]["count"]==2 and \
       m["inner"]["centered"] and m["hole"]["sym"][0]>=.87 and m["hole"]["ellipse"]>=.75 and \
       m["inner"]["sym"][0]>=.90 and m["inner"]["box"][2]*2<=m["inner"]["box"][3] and \
       m["hole"]["box"][2]<.42*m["size"][0]:
        return ("WA" if code=="WB" else "WC"),""
    stem=m["stem62"]
    if stem is not None:
        if holes==2 and .33<=stem<=.67 and m["junctions"]<=3 and m["attrs"][0]>=.81 and \
           abs(m["positions"][0][1]-m["positions"][1][1])<=.10 and \
           min(x for x,y in m["positions"])<=stem-.10 and max(x for x,y in m["positions"])>=stem+.10:
            return "FG",""
        if holes==1 and code=="FG":
            x,y=m["positions"][0]
            if abs(stem-.5)>=.17 and abs(stem-x)>=.18:
                left=stem<x
                return ("F"+("ABC" if left else "DEF")[0 if y<.38 else 1 if y>.62 else 2]),\
                       ("D" if left else "A")
            return "DA",""
    if holes==1 and code=="LH" and m["hole"] and m["hole"]["polygon"]==3 and m["hole"]["convex"]>=.91 and \
       max(abs(x-.5) for x in m["positions"][0])>=.105:
        return "LL",""
    if code=="NC" and not m["verticalStems"] and not m["stems"] and m["endpoints"]<=2 and m["junctions"]==0:
        return ("GA" if m["shape"]!=2 else "GC"),""
    mark=compact_marks(m)
    if mark:
        return mark,""
    angle=pointed_angle(m)
    if angle:
        return angle,""
    return code,""

def classify62(m,position=""):
    if m is None:
        return "ZAZ",[],[]
    initial,old_paths,_=previous(m,position)
    b,hint=primary(m,initial)
    family=b[0]
    lr,ud,rot,x,y=m["attrs"][:5]
    attrs=symmetry(m["attrs"])
    d=initial[-1]
    paths=list(old_paths)
    # If the shape has moved families, retain layout alternatives only.
    if b!=initial[:2]:
        paths=[p for p in paths if p[0] in "STUV"]
    if b=="QE":
        d="P"
    elif b=="QF":
        d="V"
    elif b in ATTACHED:
        d=attachment(m) or "Z"
    elif family=="P":
        d=hint if hint in DIR_SET else "Z"
    elif family in "JN":
        d=hint or initial[-1]
        if family=="J" and b in ("JA","JB","JC","JD"):
            d=dict(JA="S",JB="W",JC="A",JD="D")[b]
        if family=="N":
            if b in ("NA","NC","NB","ND"):
                d="D" if b in ("NA","NC") else "A"
            elif d not in DIR_SET:
                gx=m["gaps"]
                if m["midBranch"]:
                    d=m["midBranch"]
                elif abs(gx[2]-gx[3])>=.19:
                    d="S" if gx[2]>gx[3] else "W"
                elif abs(gx[1]-gx[0])>=.19:
                    d="D" if gx[1]>gx[0] else "A"
                else:
                    d="F"
    elif family in "BCI":
        d=BC_BEARING.get(b)
        if not d:
            old_d=initial[-1]
            d=(OPPOSITE.get(old_d) if b==initial[:2] and family in "BC" else "") or bias(x,y,.045) or "F"
    elif family in "REKGHY":
        if b=="EF":
            d="E"
        else:
            d=(attrs or ("E" if m["parallel"] else "") or
               ("T" if m["skew"]>=14 and m["elongation"]>=1.65 else "") or bias(x,y,.04) or "F")
    elif family in "ALWX" and initial[0] not in "ALWX":
        d="H" if m["holesRaw"] else "B"
    elif family=="F" and hint:
        d=hint
    if b=="LL" and initial[:2]=="LH":
        paths.append("LHH")
    if b=="XA" and ring_in_ring(m):
        paths.append("AAE")
    if family=="D" and m["feet62"]:
        paths.append("JAS")
    if family=="X" and frame_two(m):
        k,kd=loop(m,False)
        if k.startswith("K"):
            paths.append(k+(kd or attrs or "F"))
    if family=="L" and b[1] in "ABCD" and m["tip"]:
        paths.append(b+m["tip"])
    out=b+d
    paths=list(dict.fromkeys(p for p in paths if p!=out))
    ranks=[] if family=="Z" else list(dict.fromkeys([family]+[p[0] for p in paths]))[:2]
    return out,paths,ranks

