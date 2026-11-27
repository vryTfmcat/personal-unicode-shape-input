"""BCD predicates consume pixel geometry only; O20 is applied by the caller."""
from geometry import direction
import math

D_DIR = {"W":"正上","A":"正左","S":"正下","D":"正右","J":"左上","K":"右上","N":"左下","M":"右下"}
D_ATTR = dict(zip("HBCPGLUREITVXQFYZ",
    ("空心常规","实心常规","空心小巧","实心小巧","双轴对称","左右对称","上下对称","旋转对称",
     "双线空心","虚线","斜倾","两件","三件","四件及以上","常规","冻结 O 类","缺证")))
D_KEYS = D_DIR | D_ATTR
NAMES = dict(zip("ABCDEFGHIJKLMNOPQRSTUVWXYZ",(
    "圆与椭圆","折角与方折","开口单弧","紧凑单孔环","三孔及以上","直干附圈","S 弯与波浪",
    "直干弧钩","单叉曲线","单孔带尾","双孔","三角与多边形","多竖干","横枝与梳齿","交叉放射",
    "箭头","单线点线","贯通顶线","左右内外件","小附标","上下成件","重复散件","字符外框",
    "几何外框","复杂无孔曲线","缺证")))

def bias(x,y,dead=.12):
    dx,dy=x-.5,y-.5
    if max(abs(dx),abs(dy)) < dead:
        return ""
    if min(abs(dx),abs(dy)) < .55*max(abs(dx),abs(dy)):
        return direction(dx if abs(dx)>abs(dy) else 0,dy if abs(dy)>=abs(dx) else 0)
    return direction(dx,dy)

def cardinal(key):
    return {"J":"W","K":"W","N":"S","M":"S"}.get(key,key)

def accessory_and_layout(m):
    parts=m["boxes"]
    w,h=m["size"]
    if len(parts)<2:
        return []
    main=parts[0]
    others=parts[1:]
    x,y,ww,hh,area=main
    tiny=[p for p in others if p[4] <= .34*area and max(p[2:4]) <= .51*max(w,h)]
    above=[p for p in tiny if p[1]+p[3] <= y+1]
    below=[p for p in tiny if p[1] >= y+hh-1]
    options=[]
    if len(tiny)==len(others) and len(above)+len(below)==len(tiny):
        if above and below:
            options.append(("TC","V"))
        elif len(tiny)>=2:
            options.append(("TF", "W" if above else "S"))
        else:
            q=tiny[0]
            horizontal=(q[0]+q[2]/2)-(x+ww/2)
            vertical=-1 if above else 1
            side=direction(horizontal,vertical*max(ww,hh)*.45) if abs(horizontal)>=.25*ww else ("W" if above else "S")
            options.append((("TD" if above else "TE") if side not in "WS" else ("TA" if above else "TB"),side))
    if len(parts)>=3:
        cx=[(p[0]+p[2]/2)/w for p in parts]
        cy=[(p[1]+p[3]/2)/h for p in parts]
        dx,dy=max(cx)-min(cx),max(cy)-min(cy)
        ordered=sorted(zip(cx,cy))
        delta=ordered[-1][1]-ordered[0][1]
        collinear=abs(delta)>=.26 and all(abs(yy-ordered[0][1]-
                       delta*(xx-ordered[0][0])/max(.01,dx))<.19 for xx,yy in ordered)
        if dy<.18: c="A"
        elif dx<.18: c="B"
        elif collinear or (m["holesRaw"]==2 and len(parts)==3 and dx>=.30 and dy>=.30): c="C"
        elif len(parts)>=4 and any(abs(a-c)<.10 and abs(b-d)<.10 for a,b in ordered
                                  for c,d in ordered if (a,b)!=(c,d)): c="E"
        elif len(parts)<=4: c="D"
        else: c="F"
        options.append(("V"+c,"X" if len(parts)==3 else "Q"))
    if m["nested"]:
        options.append(("SF","V"))
    if len(parts)==2:
        left,right=sorted(parts,key=lambda p:p[0])
        if left[0]+left[2] <= right[0]+1:
            if left[4]<.35*right[4]: c="D"
            elif right[4]<.35*left[4]: c="E"
            elif all(p[3]>=2*p[2] for p in parts): c="A"
            elif m["attrs"][0]>.78: c="B"
            else: c="C"
            options.append(("S"+c,"V"))
    upper,lower=sorted(parts[:2],key=lambda p:p[1])
    if upper[1]+upper[3] <= lower[1]+1 and lower[4]>=.30*upper[4] and upper[4]>=.30*lower[4]:
        c="A" if all(2*p[3]<=p[2] for p in parts) else "C" if m["holesRaw"] else "D" if m["junctions"]>=4 else "B"
        options.append(("U"+c,"V" if len(parts)==2 else "X" if len(parts)==3 else "Q"))
    return options

def closed_rows(m,extra):
    holes=m["holesRaw"]
    hulling=m["hull"]
    vertex=m["polygon"]
    _,_,w,h,area=m["body"]
    inside=m["inside"]
    oval=m["circle"]>=.925 and hulling>.90
    rect=vertex==4 and m["type4"]=="axis" and hulling>=.92
    poly=(3<=vertex<=8 and hulling>=.92 and m["circle"]<.92 and
          (vertex<=4 or m.get("contourStraight",0)>=.65))
    framed=oval or rect or (poly and vertex in (3,4))
    if framed and inside and holes>=1:
        count,ink,iw,ih,e,j,straight,length,inner_holes=inside
        if max(iw,ih)<=.24*max(w,h) and not e and not j or inner_holes==1 and length<2.8 and not j:
            subtype=0
        elif not oval and not rect and e==0 and not j and not inner_holes and ink>=.29*iw*ih:
            subtype=0
        elif j==0 and inner_holes==0 and (straight>=.82 or count>=2 and length<=2.1) and e<=4:
            subtype=1
        elif j<=2 and e>=3 and straight>=.72 and not inner_holes:
            subtype=2
        elif inner_holes<=1 and length<=1.7 and j<=1 and straight>=.67:
            subtype=3
        else:
            if not oval and not rect:
                return "WE"
            return "WG" if m["parallel"] else ("W" + ("B" if length>2.75 or count>=3 else "A") if oval
                                                 else "W" + ("D" if length>2.75 or count>=3 else "C"))
        return "X"+("ABCD"[subtype] if oval else "EFGH"[subtype] if rect else "I")
    if not inside and holes==2 and m["components"]==1 and (oval or rect) and m["junctions"]>=2:
        if oval and m["straight_ratio"]>=.58:
            return "XB"
        if rect and m["straight_ratio"]>=.76:
            return "XF"
    if not inside and holes==4 and framed and m["junctions"]>=3 and (m["straight_ratio"]>=.79 or
       oval and m["centeredJunction"] and min(m["attrs"][:2])>=.88):
        return "XC" if oval else "XG" if rect else "XI"
    if m.get("twinCircle") and m["straight_ratio"]<=.55:
        return "AI"
    if oval and (m["components"]==1 or extra) and holes<=1 and min(w,h)>=9:
        if extra:
            return "AG"
        if holes and m["junctions"]==0:
            px,py=m["positions"][0]
            if max(abs(px-.5),abs(py-.5))>=.20:
                return "AD" if .20<=m["darkBody"]<=.80 else "AE"
        if not holes and m["darkBody"]<=.66 and m["endpoints"]>=2:
            return ""
        return "A"+"ABC"[m["shape"]]
    if not inside and holes==1 and .87<=m["circle"]<.925 and hulling>=.89 and not m["midBranch"] and \
       m["endpoints"]==1 and m["tail"]<.40 and m.get("contourStraight",0)<.40:
        return "AH"
    if holes<=1 and (m["components"]==1 or extra) and min(w,h)>=8 and poly and (holes or m["darkBody"]>=.40):
        if extra: return "LN"
        if vertex==3: return "L"+"ABCD"["WSAD".index(m["tip"])]
        if vertex==4:
            if holes and bias(*m["positions"][0],.22) and .52<=m["darkBody"]<=.85:
                return "LL"
            if rect and m["type4"]=="axis": return "L"+"EFG"[m["shape"]]
            return "LH" if m["type4"]=="diamond" else "LI"
        if vertex>=5 and m["darkBody"]>=.37: return "LJ"
    if holes==1 and vertex<=5 and not inside and hulling>=.70 and m.get("contourStraight",0)>=.72 and \
       m["endpoints"]==1 and max(m["gaps"])>=.37:
        return "LM"
    if holes==0 and m["components"]==1 and m["rays"]>=5 and .57<=hulling<=.86 and \
       m.get("contourStraight",0)>=.71 and m["darkBody"]>=.48:
        return "LK"
    if m["components"]==1 and holes<=1 and vertex in (5,6) and .78<=hulling<.92 and \
       m["straight_ratio"]>=.87 and m.get("contourStraight",0)>=.80 and m["darkBody"]>=.66 and max(m["attrs"][:2])<.82:
        return "LO"
    if holes==1 and extra and hulling>.86 and vertex<=4:
        return "LN"
    if holes==0 and m["components"]>=5 and m["is_repeated_scatter"] and m["darkBody"]>.94 and m["attrs"][0]>.82 and m["attrs"][1]>.82:
        if all(max(p[2:4])<=.23*max(m["size"]) for p in m["boxes"]) and m["ink"]<.33*m["size"][0]*m["size"][1] and \
           len(m["boxes"])>=7 and m["size"][0]*4>=3*m["size"][1] and m["size"][1]*4>=3*m["size"][0]:
            return "AF"
    return ""

def arrow(m):
    ax=m["attrs"]
    e,j=m["endpoints"],m["junctions"]
    w,h=m["size"]
    g=m["gaps"]
    if m["components"]==1 and not m["holesRaw"] and .25<=m["hull"]<=.54 and m["polygon"] in (5,6):
        if ax[2]>=.83 and m["elongation"]>=2.8 and e>=4 and not m["centeredJunction"]:
            return "PC","D" if w>=h*1.6 else "W" if h>=w*1.6 else "K" if m.get("slope",0)<0 else "M"
        if e==4 and j==2 and m["elongation"]>=2.8 and abs(w-h)>.32*max(w,h):
            i=0 if w>=h else 2
            if min(g[i:i+2])<=.10 and max(g[i:i+2])<=.14 and ax[1 if i==0 else 0]>=.88:
                return "PH","DAWS"[i+int(ax[3]>.5 if i==0 else ax[4]>.5)]
    if m["arrow"]:
        kind,key=m["arrow"]
        diagonal=key in "JKNM"
        axial_sym=ax[1 if key in "AD" else 0]
        solid_dart=kind=="H" and not diagonal
        shaft_ok=(.25<=m["hull"]<=.79 and m["strokeWidth"]<=.23 and (
            not diagonal and axial_sym>=.67 or diagonal and m["shape"]==0 and
            m["elongation"]>=1.55 and abs(m.get("bend",0))>=.28))
        if solid_dart or shaft_ok and (not m["holesRaw"] or kind=="D" and
                                      not diagonal and axial_sym>=.84 and j>=2 and e>=2):
            if kind in "AB" and e>=4 and j>=2 and axial_sym>=.88 and not diagonal:
                kind="D"
            return "P"+kind,key
    # A broad outlined arrowhead has a pointed front and two balanced wings
    # surrounding a deep axial recess. Thin round open arcs fall outside this test.
    if m["components"]==1 and m["holesRaw"]==0 and .33<=m["hull"]<=.56 and m["polygon"]>=5 and \
       m["strokeWidth"]>=.105 and m["endpoints"]==2 and m["straight_ratio"]<=.55:
        g=m["gaps"]
        i=max(range(4),key=g.__getitem__)
        sym=m["attrs"][1 if i<2 else 0]
        if g[i]>=.66 and g[i^1]<=.08 and sym>=.66 and m["shape"]==0:
            return "PD","ADSW"[i]
    if m["components"]==1 and e==3 and j==1 and m["polygon"]>=4:
        i=max(range(4),key=m["gaps"].__getitem__)
        if m["gaps"][i]>=.48 and min(m["gaps"])<=.14 and m["strokeWidth"]<=.14:
            if m["straight_ratio"]>=.86 and m["verticalStems"] and m["bands"] and abs(m.get("bend",0))>=.34 and \
               max(g)>=.62:
                return "PE","DAWS"[i]
            if m["polygon"]>=5 and m["straight_ratio"]<=.55 and m["lineLength"]>=2.15 and m["hull"]<=.57:
                return "PF","ADSW"[i]
    if m["components"]==2 and e>=6 and j>=2 and m["straight_ratio"]>=.63 and .28<=m["hull"]<=.62 and \
       (ax[2]>=.80 or ax[0]>=.84 or ax[1]>=.84):
        if all(p[2]>=2*p[3] for p in m["boxes"]):
            return "PG","D" if ax[3]>=.5 else "A"
        if all(p[3]>=2*p[2] for p in m["boxes"]):
            return "PG","W" if ax[4]<=.5 else "S"
    return "", ""

def loop(m,extra):
    holes=m["holesRaw"]
    pos=m["positions"]
    elongated=m["shape"]
    if holes>=3:
        if m["parallel"]: return "EF","E"
        if extra: return "EG",""
        if holes>=6: return "EE",""
        if holes>=4: return "ED",""
        if m["endpoints"]>=2 and max(m["gaps"])>.32: return "EC",""
        px=[x for x,y in pos]; py=[y for x,y in pos]
        return ("EB" if min(max(px)-min(px),max(py)-min(py))<.16 else "EA"),""
    if holes==2:
        (x,y),(u,v)=pos
        dx,dy=abs(x-u),abs(y-v)
        if .43*max(dx,dy)<=min(dx,dy) and min(dx,dy)>.095: return "KC",""
        if extra: return "KG",""
        if m["components"]==1 and m["verticalStems"] and dx<.13 and max(abs(x-.5),abs(u-.5))>.12 and \
           (m["endpoints"] or m["attrs"][0]<.59):
            return "KD",bias((x+u)/2,(y+v)/2)
        if m["components"]==1 and m["hull"]>.94 and m["junctions"]>=2 and (m["circle"]>.90 or m["type4"]=="axis"):
            return "KE",""
        if m["endpoints"]>=2 and max(m["gaps"])>.46: return "KF",""
        return ("KA" if dy>=dx else "KB"),""
    if holes==1:
        x,y=pos[0]
        mdir=bias(x,y,.13)
        outward=max(m["gaps"])
        if m["stems"] or m["verticalStems"]:
            if m["midBranch"] and m["midBands"] and m["junctions"]>=1:
                return "FH",mdir or m["midBranch"]
            if abs(x-.5)>=.12 or (m["stems"] and max(m["gaps"][:2])>=.08 and not m["topBeam"]):
                if extra: return "FI",mdir
                side=0 if x>=.5 else 3
                level=0 if y<.39 else 1 if y>.61 else 2
                return "F"+"ABCDEF"[side+level],mdir
            if m["stems"]>=1 and m["endpoints"]>=2 and abs(x-.5)<.14 and abs(y-.5)<.15:
                return "FG",mdir
        if m["endpoints"] and (m["tail"]>=.48 or outward>=.44):
            i=max(range(4),key=m["gaps"].__getitem__)
            tail="ADSW"[i] if outward>=.44 else {"W":"S","S":"W","A":"D","D":"A"}.get(cardinal(mdir),"S")
            c="H" if extra else "F" if m["endpoints"]>=4 else "E" if tail=="S" and m["opening"]>.26 else \
              "G" if elongated==2 and tail in "AD" else dict(S="A",W="B",A="C",D="D")[tail]
            return "J"+c,tail
        if extra: return "DI",mdir
        if m["junctions"] and m["midBands"] and max(m["gaps"][:2])>.19:
            return "DH",mdir
        card=cardinal(mdir)
        return "D"+(dict(W="B",S="C",A="D",D="E").get(card) or "AGF"[elongated]),mdir
    return "", ""

def no_loop(m,extra):
    e,j=m["endpoints"],m["junctions"]
    w,h=m["size"]
    straight=m["straight_ratio"]
    gaps=m["gaps"]
    open_i=max(range(4),key=gaps.__getitem__)
    opened="DAWS"[open_i]
    ax=m["attrs"]
    if m["components"]<=2 and max(w,h)<=10 or m["components"]==2 and all(p[4]<=.54*m["ink"] and max(p[2:4])<=.53*max(w,h) for p in m["boxes"]):
        return ("QE" if m["components"]==1 else "QF"),""
    if m["rays"]>=4 and m["hull"]<=.72 and m["rays"]<=10 and \
       ((m["rays"]>=5 and straight>=.64) or (m["rays"]==4 and max(gaps)-min(gaps)<=.20)) and (e>=4 or j>=1):
        return "O"+("E" if m["rays"]>=8 else "D" if m["rays"]>=5 else
                    "F" if m["hull"]>=.55 else "A" if m["bands"] else "B"),""
    if m["topBeam"] and not (m["midBranch"] and m["bands"]>=2 and j<=3):
        return "R"+("F" if extra else "B" if m["stems"]>=2 else "E" if j>=3 else "C" if straight<=.56 else "A"),""
    if (m["midBranch"] and m["bands"]>=2 and m["hull"]<.82 and j<=4) or \
       (m["horizontalBranch"] and m["midBands"] and (m["stems"] or m["verticalStems"]) and j<=5 and not m["parallel"]):
        side=m["midBranch"] or ("D" if ax[3]<=.50 else "A")
        if extra: return "NG",side
        if m["bands"]>=3: return ("NC" if side=="D" else "ND"),side
        if ax[0]>.83: return "NE",""
        if not m["stems"] and straight<.65: return "NF",side
        return ("NA" if side=="D" else "NB"),side
    if m["components"]==1 and m["rays"]==3 and .34<=m["hull"]<=.65 and j==1 and e==3 and \
       straight>=.70 and min(w,h)*5>=max(w,h)*4 and not m["midBranch"]:
        return "OC",""
    arc_sym=ax[1] if open_i<2 else ax[0]
    if m["components"]==1 and gaps[open_i]>=.42 and e==2 and not j and \
       (straight<=.76 or arc_sym>=.72 and m["contourStraight"]<.72) and m["hull"]<.81 and gaps[open_i^1]<=.29:
        deep=(m["opening"]<.22 and .72<=w/h<=1.38 and arc_sym<.78)
        return "C"+("I" if extra else "ABCDEFGH"[open_i+4*deep]),opened
    if m["components"]==1 and j==0 and e==2 and 4*w>=5*h and ax[2]>=.79 and \
       straight<=.87 and m["hull"]<=.76 and m["lineLength"]>=.94:
        return ("GD" if m["lineLength"]>=2.35 else "GC"),""
    if j<=3 and m["verticalStems"] and straight<=.83 and e>=3 and gaps[3]>=.55 and \
       gaps[2]<.14 and ax[0]>.68:
        return ("HH" if extra else "HG" if m["verticalStems"]>=2 else "HB"),""
    if m["verticalStems"]>=2 or m["components"]>=2 and m["stems"]>=2:
        if extra: return "MF",""
        if max(m["stems"],m["verticalStems"])>=3: return "ME",""
        return ("MA" if m["components"]>=2 else "MD" if m["bands"] and gaps[2]>.35 else
                "MB" if m["midBands"] else "MC"),""
    if m["corner_count"] and straight>=.81 and j==0:
        if extra:return "BM",opened
        if m["corner_count"]>=3:return "BL",opened
        if m["corner_count"]==2:return ("BJ" if max(gaps)>=.32 else "BI"),opened
        dx=ax[3]-.5; dy=ax[4]-.5
        if m["bands"] and m["stems"] and min(abs(dx),abs(dy))>.045:
            quadrant=direction(-dx,-dy)
            if quadrant in "KJMN":return "B"+dict(K="A",J="B",M="C",N="D")[quadrant],quadrant
        return ("B"+dict(W="E",S="F",D="G",A="H")[opened] if max(gaps)>.19 else "BK"),opened
    if e<=2 and j==0 and (m["elongation"]>=4 or (min(w,h)<=3 and max(w,h)>=7)):
        side="A" if w>=2*h else "B" if h>=2*w else "C" if m.get("slope",0)<0 else "D"
        if m["components"]>1 or e>2:return "QG",""
        return "Q"+side,""
    if (m["stems"]>=1 or m["verticalStems"]>=1) and straight<=.88 and m["hull"]<.84 and j<=3:
        if extra:return "HH",""
        if m["midBands"]>=2 and e>=3:return "HG",""
        if m["stems"] and max(gaps[2:])>=.42 and min(gaps[2:])>=.21:return "HE",""
        if ax[3]>=.55:return ("HC" if ax[4]>.52 else "HD"),""
        return ("HB" if j else "HA" if h>=w else "HF"),""
    if j in (1,2) and e in (3,4,5) and (straight<=.84 or m["centeredJunction"] and m["rays"]<3 and straight<=.95):
        opening=("W" if ax[4]<.47 else "S") if h>w*1.25 and abs(ax[4]-.5)>.029 else \
                opened if gaps[open_i]>.25 else bias(ax[3],ax[4],.07)
        c="F" if extra else dict(W="A",S="B",A="C",D="D").get(opening,"E")
        return "I"+c,opening
    if m["components"]==1 and e==2 and not j and straight<=.79 and m["lineLength"]>=1.15:
        if extra:return "GG",""
        if m["opening"]<.10 and m["lineLength"]>=2.20:return "GE",""
        if w>=h*1.25:return ("GD" if m["lineLength"]>=2.35 else "GC"),""
        if m["elongation"]>=2.5 and m["skew"]>=24:return "GF",""
        return ("GA" if m.get("bend",0)>=0 else "GB"),""
    if m["lineLength"]>=1.65 or j>=2:
        if extra:return "YP",""
        centroid=cardinal(bias(ax[3],ax[4],.11))
        idx=dict(W=0,S=1,A=2,D=3).get(centroid,4)
        if m["shape"]==0 and max(gaps[:2])>.47:
            idx=2 if gaps[1]>gaps[0] else 3
        return "Y"+chr(65+5*m["shape"]+idx),centroid
    return "", ""

def classify(m, position=""):
    if m is None:
        return "ZAZ",[],[]
    layouts=accessory_and_layout(m)
    extra=any(bc[0]=="T" for bc,d in layouts)
    holes=m["holesRaw"]
    centered_dot_pair=len(m["boxes"])==3 and layouts and layouts[0][0]=="TC" and \
                      5*m["body"][3]<m["body"][2] and min(m["attrs"][:2])>=.87
    stem_bar=holes==1 and m["midBranch"] and m["midBands"] and m["junctions"]>=1 and m["stems"] and not m["inside"]
    base="" if stem_bar or centered_dot_pair else closed_rows(m,extra)
    p,pdir=arrow(m)
    if p and not base:
        primary,hint=p,pdir
    elif base:
        primary,hint=base,m["tip"] if base[0]=="L" and base[1] in "ABCD" else ""
    elif m["components"]>=3 and not m["inside"] and m["boxes"][0][4]<=.60*m["ink"] and \
         sum(p[3]>=.83*m["size"][1] and p[2]<=.27*m["size"][0] for p in m["boxes"])==2 and \
         m["attrs"][0]>=.64 and m["straight_ratio"]<=.74:
        primary,hint="WF",""
    elif holes:
        if m["topBeam"] and m["body"][3]>=.75*m["size"][1] and m["junctions"]>=3 and holes<=2 and not m["inside"]:
            primary,hint="RD",""
        else:
            primary,hint=loop(m,extra)
    else:
        primary,hint=no_loop(m,extra)
        if layouts and not (primary.startswith("R") or primary.startswith(("Q","M")) and not extra):
            primary,hint=layouts[0]
        if centered_dot_pair:
            primary,hint="UC","X"
    if not primary:
        return "ZBZ",[],[]
    family=primary[0]
    lr,ud,rot,x,y,_=m["attrs"]
    sym="G" if min(lr,ud)>=.78 else "L" if lr>=.83 else "U" if ud>=.83 else "R" if rot>=.81 else ""
    closed="E" if m["parallel"] and holes>=2 else ("C" if holes else "P") if position else ("H" if holes else "B")
    count="F" if m["components"]<2 else "V" if m["components"]==2 else "X" if m["components"]==3 else "Q"
    if family in "ALWX":
        d="I" if primary=="AF" else closed
    elif family in "BCPFJN":
        d=hint or sym or bias(x,y) or "F"
    elif family in "STUV":
        d=hint or count
    elif family=="R":
        d="W"
    else:
        d="E" if family=="E" and primary=="EF" else (sym or bias(x,y) or ("T" if m["skew"]>=22 and m["elongation"]>2.4 else count))
    code=primary+d
    second=[]
    for bc,key in layouts:
        if bc!=primary:
            second.append(bc+key)
    for key in (position if family=="A" else "",hint if family in "ALWX" else "",sym if family in "ALWX" else "",
                "B" if family=="P" and m["darkBody"]>.38 else ""):
        if key and key!=d:
            second.append(primary+key)
    ranks=list(dict.fromkeys([family]+[c[0] for c in second]+([p[0]] if p else [])))[:2]
    return code,list(dict.fromkeys(second)),ranks

