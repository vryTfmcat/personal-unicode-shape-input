"""Pixel measurements and source verification for the isolated v6 experiment."""
from collections import defaultdict
from functools import lru_cache
from pathlib import Path
import math
import runpy
import io

OUT = Path(__file__).resolve().parent
V5 = OUT.parent / "整体重规划-20261124-B分流与可解释A层"
V41 = OUT.parent / "整体重规划-20261121-BC族表v0"
P = runpy.run_path(str(V5 / "stage3.py"))
ROOT, THRESHOLDS = P["ROOT"], P["THRESHOLDS"]
cv2, np, Image = P["cv2"], P["np"], P["Image"]
read, digest = P["read"], P["digest"]
from PIL import ImageFont, ImageDraw
from fontTools.ttLib import TTFont
from fontTools.pens.boundsPen import BoundsPen

EDITOR = ROOT / "原型/键位编辑器"
MANIFEST = EDITOR / "fonts/manifest.json"
DIRS = "DM SNAJWK".replace(" ","")
VECTORS = np.array([(math.cos(i*math.pi/4),math.sin(i*math.pi/4)) for i in range(8)])
ELLIPSE_AXIS = (np.arange(32)-15.5)/16
ELLIPSE = ELLIPSE_AXIS[:,None]**2+ELLIPSE_AXIS[None,:]**2 <= 1

def checksummed(path, hashes, expected=None):
    key = str(path.resolve())
    if key not in hashes:
        hashes[key] = digest(path)
    if expected and hashes[key] != expected:
        raise ValueError(f"SHA256 不符 {path}")
    return hashes[key]

def font_manifest():
    return {cp: face for face in read(MANIFEST)["faces"] for cp in face["codepoints"]}

@lru_cache(maxsize=None)
def outline(path):
    return TTFont(path)

@lru_cache(maxsize=20)
def pil_face(path):
    font = TTFont(path)
    font.flavor = None
    buffer = io.BytesIO()
    font.save(buffer)
    return ImageFont.truetype(io.BytesIO(buffer.getvalue()),54,layout_engine=ImageFont.Layout.BASIC)

def font_path(face, hashes):
    path = EDITOR/"fonts"/face["file"]
    checksummed(path,hashes,face["sha256"])
    return path

def placement(cp, face, hashes):
    if not face:
        return ""
    font = outline(font_path(face,hashes))
    name = font.getBestCmap().get(cp)
    if not name:
        return ""
    glyphs = font.getGlyphSet()
    pen = BoundsPen(glyphs)
    glyphs[name].draw(pen)
    if not pen.bounds:
        return ""
    _, bottom, _, top = pen.bounds
    em = font["head"].unitsPerEm
    if bottom >= .17*em and top-bottom <= .52*em:
        return "W"
    if bottom <= -.07*em and top <= .35*em and top-bottom <= .52*em:
        return "S"
    return ""

def pictorial_images(records, hashes, faces):
    groups = defaultdict(list)
    for cp,r in records.items():
        preview = r.get("preview") or {}
        if preview.get("kind") == "locked-font-binary-64px":
            groups[preview["url"]].append((cp,preview))
    done = set()
    for url,items in groups.items():
        path = EDITOR/url
        checksummed(path,hashes)
        with Image.open(path) as image:
            for cp,r in items:
                x,y = r["x"],r["y"]
                done.add(cp)
                yield cp,np.array(image.crop((x,y,x+64,y+64)).convert("L")),"锁定栅格"
    for cp in records.keys()-done:
        face = faces.get(cp)
        if not face:
            continue
        font = pil_face(font_path(face,hashes))
        text = chr(cp)
        x,y,x1,y1 = font.getbbox(text)
        if x1 <= x or y1 <= y:
            continue
        image = Image.new("L",(x1-x,y1-y),255)
        ImageDraw.Draw(image).text((-x,-y),text,font=font,fill=0)
        image.thumbnail((60,60),Image.Resampling.LANCZOS)
        canvas = Image.new("L",(64,64),255)
        canvas.paste(image,((64-image.width)//2,(64-image.height)//2))
        yield cp,np.asarray(canvas),"锁定清单字库轮廓"

def typology(mask):
    h,w = mask.shape
    # Broad proportional descriptions (integer inequalities) only where the specification names them.
    return 1 if 4*h >= 5*w else 2 if 4*w >= 5*h else 0

def circle_score(contour, shape):
    filled = np.zeros(shape,np.uint8)
    cv2.drawContours(filled,[contour],0,1,-1)
    normal = cv2.resize(filled,(32,32),interpolation=cv2.INTER_NEAREST_EXACT).astype(bool)
    return np.count_nonzero(normal & ELLIPSE)/max(1,np.count_nonzero(normal | ELLIPSE))

def direction(dx,dy):
    if abs(dx)+abs(dy) < 1e-7:
        return ""
    return DIRS[int(round(math.atan2(dy,dx)/(math.pi/4)))%8]

def band_lengths(binary):
    n,_,s,_ = cv2.connectedComponentsWithStats(binary.astype(np.uint8),connectivity=8)
    return n-1,s

def horizontal_runs(mask, fraction):
    w = mask.shape[1]
    kernel = np.ones((1,max(1,math.ceil(fraction*w))),np.uint8)
    eroded = cv2.erode(mask,kernel,borderType=cv2.BORDER_CONSTANT,borderValue=0)
    return np.flatnonzero(eroded.any(axis=1)).tolist()

def groups(values):
    result = []
    for item in values:
        if not result or item > result[-1][-1]+1:
            result.append([])
        result[-1].append(item)
    return result

def radial_profile(mask):
    h,w = mask.shape
    if min(w,h) < 9:
        return 0
    y,x = np.where(mask)
    x,y = 2*(x+.5)/w-1,2*(y+.5)/h-1
    theta = np.arctan2(y,x)
    distance = np.hypot(x,y)
    sector = np.floor((theta+np.pi)*72/(2*np.pi)).astype(int).clip(0,71)
    profile = np.zeros(72)
    np.maximum.at(profile,sector,distance)
    smooth = sum(np.roll(profile,k) for k in (-2,-1,0,1,2))/5
    peak = max(smooth)
    peaks = (smooth >= np.roll(smooth,1)) & (smooth > np.roll(smooth,-1)) & (smooth >= .66*peak)
    return int(sum(p and min(smooth[(i-6)%72:i] if i>=6 else np.take(smooth,range(i-6,i),mode="wrap")) < .81*v
                   and min(np.take(smooth,range(i+1,i+7),mode="wrap")) < .81*v
                   for i,(p,v) in enumerate(zip(peaks,smooth))))

def arrow_form(mask, m, solidity, vertices):
    """Match tapered heads and shafts using axial sections in eight directions."""
    h,w = mask.shape
    if min(h,w) < 8 or m["components"] != 1 or (solidity > .91 and vertices <= 4):
        return ""
    y,x = np.where(mask)
    points = np.column_stack((x,y))
    candidates = []
    for i,(dx,dy) in enumerate(VECTORS):
        axis, across = points @ np.array([dx,dy]),points @ np.array([-dy,dx])
        length = np.ptp(axis)
        width = np.ptp(across)
        if length < 11 or width < 8 or 1.23*width < length*.29:
            continue
        t = (axis-axis.min())/length
        centers, spans, middles = [],[],[]
        for a,b in ((0,.19),(.22,.40),(.43,.58),(.61,.77),(.80,.92),(.92,1.01)):
            z = across[(t>=a)&(t<b)]
            if not len(z):
                break
            lo,hi = float(z.min()),float(z.max())
            spans.append((hi-lo+1)/width)
            centers.append((lo+hi)/2)
            middles.append(np.count_nonzero(abs(z-(lo+hi)/2)<=.085*width)/len(z))
        if len(spans) != 6:
            continue
        tail, shaft, neck, head, flank, tip = spans
        centered = max(centers)-min(centers) <= .25*width
        if not centered:
            continue
        # An open or solid wedge has a narrow shaft, a broadened head and a tip on that axis.
        if max(tail,shaft) <= .63 and max(head,flank) >= .77 and tip < .79*max(head,flank) and length >= .88*width:
            kind = "D" if m["holesRaw"] or (m["strokeWidth"] >= .15 and min(middles[3:5]) < .09) else ("B" if i%2 else "A")
            candidates.append((max(head,flank)-max(tail,shaft)+.2*(1-tip),kind,DIRS[i]))
        # Dart shape: separated rear wings converge onto one solid central tip.
        if vertices == 3 and .47 <= solidity <= .81 and tail >= .76 and tip <= .34 and middles[0] <= .10 and middles[4] >= .22:
            candidates.append((.95+tail-tip,"H",DIRS[i]))
        # Broad outline arrowheads leave an axial gap between the two rear wings.
        if not i%2 and .34 <= solidity <= .57 and vertices >= 5 and tail >= .82 and tip <= .37 and \
           middles[0] <= .10 and middles[1] <= .10 and middles[2] <= .10 and middles[4] >= .15 and \
           m["strokeWidth"] >= .095 and .66*width <= length <= 1.16*width:
            candidates.append((.68+tail-tip,"D",DIRS[i]))
    if not candidates:
        return ""
    _,kind,key=max(candidates)
    opposite=DIRS[(DIRS.index(key)+4)%8]
    if kind in "AB" and any(k in "AB" and d==opposite for _,k,d in candidates):
        return "C"+key
    return kind+key

def measure(gray,t,m=None):
    mask = P["tight_mask"](gray,t)
    if mask is None:
        return None
    m = m or P["measure"](gray,t)
    if m is None:
        return None
    h,w = mask.shape
    n,labels,stats,centers = cv2.connectedComponentsWithStats(mask,connectivity=8)
    order = sorted(range(1,n),key=lambda i:int(stats[i,4]),reverse=True)
    x,y,sw,sh,area = map(int,stats[order[0]])
    if len(order)>1:
        body = (labels[y:y+sh,x:x+sw] == order[0]).astype(np.uint8)
    else:
        body = mask
    contours,_ = cv2.findContours(body,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
    contour = max(contours,key=cv2.contourArea)
    hull = cv2.convexHull(contour)
    area_hull = cv2.contourArea(hull)
    hull_perim = cv2.arcLength(hull,True)
    poly = cv2.approxPolyDP(hull,.031*hull_perim,True).reshape(-1,2)
    vertices = len(poly)
    convexity = cv2.contourArea(contour)/max(1,area_hull)
    ellipse = circle_score(contour,body.shape) if min(body.shape) >= 7 else 0
    inside = [i for i in order[1:] if x <= stats[i,0] and y <= stats[i,1] and
              stats[i,0]+stats[i,2] <= x+sw and stats[i,1]+stats[i,3] <= y+sh and stats[i,4]>=2]
    inner = (np.isin(labels,inside)).astype(np.uint8)
    inner_hints = []
    if inside:
        ii = np.argwhere(inner)
        by,bx = ii.min(axis=0)
        ey,ex = ii.max(axis=0)+1
        tile = inner[by:ey,bx:ex]
        line = P["line_network"](tile,max(tile.shape))
        ins = P["measure"]((1-tile)*255,128)
        inner_hints = [len(inside),int(inner.sum()),int(ex-bx),int(ey-by),line[0],line[1],line[2],
                       line[6]/max(tile.shape),ins["holesRaw"] if ins else 0]
    box = [int(v) for v in (x,y,sw,sh,area)]
    outer_direction = ""
    poly_type = ""
    if vertices == 3:
        lens = [(float(np.linalg.norm(poly[a]-poly[b])),(a,b,c)) for a,b,c in ((0,1,2),(1,2,0),(2,0,1))]
        _,(a,b,c) = min(lens,key=lambda item: abs(float(np.linalg.norm(poly[item[1][2]]-poly[item[1][0]]))-
                                                  float(np.linalg.norm(poly[item[1][2]]-poly[item[1][1]]))))
        p,q,r = poly[a],poly[b],poly[c]
        p0 = (p+q)/2
        vector = r-p0
        outer_direction = ("D" if vector[0]>0 else "A") if abs(vector[0])>abs(vector[1]) else ("S" if vector[1]>0 else "W")
    elif vertices == 4:
        edges = np.roll(poly,-1,axis=0)-poly
        orth = [abs(float(a@b))/max(1,float(np.linalg.norm(a)*np.linalg.norm(b))) for a,b in zip(edges,np.roll(edges,-1,axis=0))]
        axis_edges = sum(min(abs(a),abs(b)) <= .18*max(abs(a),abs(b)) for a,b in edges)
        poly_type = "axis" if max(orth)<.28 and axis_edges>=3 else "diamond" if axis_edges==0 and min(w,h)*5>=max(w,h)*3 else "oblique"
    profile = []
    for side in (body.T[::-1],body.T,body,body[::-1]): # right, left, up, down
        hh,ww=side.shape
        if min(hh,ww)<5:
            profile.append(0.)
            continue
        depth = np.argmax(np.pad(side,((0,1),(0,0)),constant_values=1)>0,axis=0)
        mid=depth[ww//4:max(ww//4+1,3*ww//4)]
        profile.append(float(np.median(mid))/hh)
    hlines = groups(horizontal_runs(body,.46))
    vlines = groups(horizontal_runs(body.T,.59))
    beam=horizontal_runs(body,.74)
    top = bool(hlines and min(hlines[0]) <= max(2,.13*sh) and
               vlines and any(i <= .13*sh for i in beam) and
               not any(i >= .83*sh for i in horizontal_runs(body,.72)))
    # Horizontal branches can start on a curved backbone. Count separated horizontal bands.
    bands = [g for g in hlines if len(g)>=2]
    middles = [g for g in bands if .18*sh <= sum(g)/len(g) <= .82*sh]
    left = right = 0
    for g in bands:
        yy=g[len(g)//2]
        xx=np.flatnonzero(body[yy])
        if len(xx):
            left += int(xx[0] <= .28*sw and xx[-1] >= .60*sw)
            right += int(xx[-1] >= .72*sw and xx[0] <= .40*sw)
    mid_signed = ""
    if middles and min(sw,sh)>=9:
        g=max(middles,key=len)
        yy=g[len(g)//2]
        band=np.flatnonzero(body[yy])
        earlier=np.argwhere(body[max(0,yy-max(3,sh//6)):max(0,yy-len(g))])
        later=np.argwhere(body[min(sh,yy+len(g)):min(sh,yy+max(3,sh//6))])
        if len(band) and len(earlier) and len(later):
            local=(np.median(earlier[:,1])+np.median(later[:,1]))/2
            mid_signed = "D" if (band[-1]-local) >= .34*sw and (local-band[0]) <= .25*sw else "A" if (local-band[0]) >= .34*sw and (band[-1]-local) <= .25*sw else ""
    area_total=int(mask.sum())
    shx=np.flatnonzero(body[:,max(0,sw//2)])
    blank_gap = (max(np.diff(shx),default=0)/sh if len(shx)>2 else 0)
    a = m["attrs"]
    peaks=radial_profile(mask) if len(order)==1 and m["holesRaw"]==0 and .7 <= h/w <= 1.43 else 0
    iy,ix=np.where(body)
    slope=float(np.mean((ix-ix.mean())*(iy-iy.mean())))
    track=[float(np.mean(ix[(iy>=start)&(iy<stop)]))/sw
           for start,stop in ((0,sh/3),(sh/3,2*sh/3),(2*sh/3,sh))
           if ((iy>=start)&(iy<stop)).any()]
    if len(track)==3:
        bend=track[0]-track[2]
    else:
        bend=0.
    ext=cv2.approxPolyDP(contour,.022*max(1,cv2.arcLength(contour,True)),True).reshape(-1,2)
    if len(ext)>=3:
        steps=np.roll(ext,-1,axis=0)-ext
        sizes=np.linalg.norm(steps,axis=1)
        made_straight=float(np.sum(sizes[sizes>=.22*max(sw,sh)])/max(1,sizes.sum()))
    else:
        made_straight=0.
    twin_circle=False
    if m["holesRaw"]==2 and m["components"]==1 and m["junctions"]>=2:
        (hx,hy),(kx,ky)=m["positions"]
        active=body if abs(hx-kx)>=abs(hy-ky) else body.T
        counts=active.sum(axis=0)
        width_counts=np.array([np.ptp(np.where(active[:,i])[0])+1 if counts[i] else 0 for i in range(active.shape[1])])
        middle=width_counts[len(counts)//2]
        twin_circle=bool(len(counts)>=15 and middle<.78*max(width_counts[:len(counts)//2]) and
                         middle<.78*max(width_counts[len(counts)//2:]))
    return dict(m, body=box, shape=typology(body), hull=round(convexity,4), polygon=vertices,
                type4=poly_type, tip=outer_direction, circle=round(ellipse,4), inside=inner_hints,
                gaps=profile, bands=len(bands), midBands=len(middles), midBranch=mid_signed,
                leftBands=left,rightBands=right, stems=len(vlines), topBeam=top,
                ink=area_total, throat=blank_gap, rays=peaks, darkBody=float(body.mean()),
                arrow=arrow_form(mask,m,convexity,vertices), slope=slope, bend=bend,
                contourStraight=made_straight,twinCircle=twin_circle)

