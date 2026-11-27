"""Rebuild the isolated Stage 3 draft from the locked v4.1 sources."""
import base64
from collections import Counter, defaultdict
import hashlib
import html
import io
import json
import math
from pathlib import Path
import random
import runpy
import sys

OUT = Path(__file__).resolve().parent
if (OUT / "deps").is_dir():
    sys.path.insert(0, str(OUT / "deps"))

import cv2
import numpy as np
from PIL import Image, __version__ as pillow_version
from importlib.metadata import version

SRC = OUT.parent / "整体重规划-20261121-BC族表v0"
ROOT = next(p for p in OUT.parents if p.name == "worktree")
THRESHOLDS = (112, 128, 144)
FEATURES = "全域特征标注-29096-v4.1.json"
PREVIOUS = "BC分配结果-全域-v4.1.json"
OLD_B = "BCD分配结果-全域-方案B-v4.1.json"
OLD_C = "BCD分配结果-全域-方案C-v4.1.json"
CELLS = "BC-676格规则-v4.1.json"
BLIND = "族内特征-加权.json"
AUDIT = ROOT / "数据/三模式/规则库/四键实验/人工审议.json"
HISTORY = "D层三方案全域评估-明细.json"
V4_SCRIPT = "BC分配-全域-v4.py"
D_SCRIPT = "BCD分配-D层三方案.py"
IMAGE_SCRIPT = "生成全域特征标注.py"
INPUTS = [SRC / n for n in (FEATURES, PREVIOUS, OLD_B, OLD_C, CELLS, BLIND, HISTORY,
                           V4_SCRIPT, D_SCRIPT, IMAGE_SCRIPT, "族内特征标注口径-冻结.md",
                           "BC分配结果-全域-v4.json","BC分配统计-全域-v4.1.json")]
INPUTS += [AUDIT, ROOT / "数据/三模式/shape-stage.json",
           ROOT / "原型/键位编辑器/data/structure-count-bindings.json"]

cv2.setNumThreads(1)
V4 = runpy.run_path(str(SRC / V4_SCRIPT))
D = runpy.run_path(str(SRC / D_SCRIPT))
IMAGE = D["GLYPH"]
O20 = V4["O20"]
IMAGE["fit_shape"].__globals__["cv2"] = cv2

B_RULE = {
    "A": ("○", "外缘近椭圆而且单一，至多有一个居中闭孔。"),
    "B": ("∠", "单线主体主要沿直段走，出现至少一处明显折角。"),
    "C": ("∪", "单线主体以弯曲为主，白色凹口由一侧伸到整字中心附近。"),
    "D": ("ɑ", "肉眼可见一个由主笔围成的闭环。"),
    "E": ("8", "整字内有两个或更多闭孔。"),
    "F": ("d", "单孔居一侧，孔外有一条纵贯大半墨形的直干。"),
    "G": ("∿", "单线无闭孔，走势呈弯曲且整字没有深侧口。"),
    "H": ("ɿ", "无孔主体有外伸钩尾。"),
    "I": ("J", "一条直干在端部接出弧钩。"),
    "J": ("q", "单孔旁有长外伸，且整字偏纵长。"),
    "K": ("Q", "单孔旁有长外伸，且整字方扁。"),
    "L": ("□", "一个闭孔被直边围成的近凸多边形包住。"),
    "M": ("Π", "有两条分开的竖干，各自纵贯主体。"),
    "N": ("⊢", "一条纵干中段伸出一条显著横枝。"),
    "O": ("✳", "墨线在整字中部相交，并向至少三路伸出明显的臂。"),
    "P": ("→", "长干接出明确的箭头。"),
    "Q": ("╱", "整字呈独立点或细长直线。"),
    "R": ("Т", "有一道接近横贯全宽的顶梁，下方连着竖落的笔画。"),
    "S": (":", "墨件主要左右分离，或一个墨件嵌在另一件的边界内。"),
    "T": ("!", "上下分离的墨件中有一个明显小点或短附标。"),
    "U": ("=", "主体由上下分离、体量相近的墨件组成。"),
    "V": ("…", "至少三个分离墨件有相近大小和外形，或形成多方向散布。"),
    "W": ("⑴", "规则外框包住笔画较复杂或有交接的内容。"),
    "X": ("⊡", "规则外框包住简单、紧凑的几何墨件。"),
    "Y": ("⌚", "整字轮廓可辨为器物。"),
    "Z": ("♞", "整字轮廓可辨为生物。"),
}
B_RULE["S"] = ("Ⅱ", B_RULE["S"][1])

A_KEYS = "ACDEFGHIJKLMNOPQ"
COMPLEXITY = ("简线或简单双线", "常规轮廓", "密集多笔", "带小附标")
TEXTURE = ("常规线迹", "粗线迹", "斜势", "近邻平行双线")
COMPLEXITY_FORMULA = (
    "无小附标且 L≤1.85、骨架交接团≤1",
    "无小附标且其余判据均未命中",
    "无小附标且（L≥2.65 或骨架交接团≥4）",
    "次要墨件面积≤主件的30%、尺度≤全字长边的45%，且与主体包围盒分开",
)
TEXTURE_FORMULA = (
    "其余三种线迹均未命中",
    "无双线，且中位骨架半径换算线宽 W≥0.115",
    "无双线且 W<0.115，墨形长轴至少偏离横竖15°且主次方差比≥2.5",
    "两条长边近似平行、投影重叠且间距较近，中间沿空隙可穿行",
)

def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()

def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))

def save(name, obj):
    (OUT / name).write_text(json.dumps(obj, ensure_ascii=False, separators=(",", ":")) + "\n",
                            encoding="utf-8")

def tight_mask(gray, threshold):
    y, x = np.where(gray < threshold)
    if not len(x):
        return None
    return (gray[y.min():y.max()+1, x.min():x.max()+1] < threshold).astype(np.uint8)

def runs(array):
    bounds = np.flatnonzero(np.diff(np.r_[False, array.astype(bool), False]))
    return list(zip(bounds[::2], bounds[1::2], strict=True))

def trace_corners(core, start, scale):
    pixels = {tuple(p) for p in np.argwhere(core)}
    point = tuple(start)
    path = []
    while point in pixels:
        path.append(point[::-1])
        pixels.remove(point)
        y,x = point
        allowed = [(y+dy,x+dx) for dy,dx in ((0,1),(1,0),(0,-1),(-1,0))
                   if (y+dy,x+dx) in pixels]
        if not allowed:
            allowed = [(y+dy,x+dx) for dy,dx in ((1,1),(1,-1),(-1,1),(-1,-1))
                       if (y+dy,x+dx) in pixels]
        if not allowed:
            break
        if len(allowed) != 1:
            return 0
        point = allowed[0]
    if len(path) < 10 or len(pixels) > 1:
        return 0
    points = np.array(path,dtype=np.float32)
    vertices = cv2.approxPolyDP(points,.032*scale,False).reshape(-1,2)
    if not 3 <= len(vertices) <= 5:
        return 0
    segments = np.diff(vertices,axis=0)
    lengths = np.linalg.norm(segments,axis=1)
    if min(lengths) < .18*scale:
        return 0
    cosines = np.sum(segments[:-1]*segments[1:],axis=1)/(lengths[:-1]*lengths[1:])
    return int(np.count_nonzero((cosines <= math.cos(math.radians(34))) &
                                (cosines >= math.cos(math.radians(151)))))

def line_network(mask, scale):
    padded = np.pad(mask, 1)
    skeleton = cv2.ximgproc.thinning(padded * 255) > 0
    h, w = mask.shape
    neighbors = np.stack([skeleton[1+dy:1+dy+h, 1+dx:1+dx+w] for dy, dx in
                          ((-1,0),(-1,1),(0,1),(1,1),(1,0),(1,-1),(0,-1),(-1,-1))])
    degree = (neighbors & ~np.roll(neighbors, 1, axis=0)).sum(axis=0)
    core = skeleton[1:-1, 1:-1]
    ends = np.argwhere(core & (degree == 1))
    endpoints = len(ends)
    forks = (core & (degree >= 3)).astype(np.uint8)
    junctions = cv2.connectedComponents(forks, connectivity=8)[0] - 1
    radii = cv2.distanceTransform(padded, cv2.DIST_L2, 5)[skeleton]
    width = max(1., 2 * float(np.median(radii)) - 1) if radii.size else min(h, w)
    length = int(core.sum())
    lines = cv2.HoughLinesP(core.astype(np.uint8) * 255, 1, np.pi/180,
                            max(5, round(scale * .12)), minLineLength=max(4, round(scale * .13)),
                            maxLineGap=max(1, round(scale * .035)))
    coverage = np.zeros_like(mask)
    segments = []
    for x1, y1, x2, y2 in lines.reshape(-1, 4) if lines is not None else ():
        dx, dy = int(x2-x1), int(y2-y1)
        norm = math.hypot(dx, dy)
        angle = math.degrees(math.atan2(dy, dx)) % 180
        cv2.line(coverage, (x1,y1), (x2,y2), 1, 3)
        segments.append((int(x1), int(y1), int(x2), int(y2), dx, dy, norm, angle))
    corners = trace_corners(core,ends[0],scale) if endpoints == 2 and junctions == 0 else 0
    straight = int((coverage.astype(bool) & core).sum()) / max(1, length)
    vertical = sorted((x1+x2)/2 for x1,y1,x2,y2,dx,dy,norm,angle in segments
                      if abs(dx) <= .15*abs(dy) and abs(dy) >= .55*h)
    stems = []
    for x in vertical:
        if not stems or x - stems[-1] >= max(3, .16*w):
            stems.append(x)
    branch = any(abs(dy) <= .16*abs(dx) and abs(dx) >= .38*w and
                 .22*h <= (y1+y2)/2 <= .78*h and
                 min(x1,x2)-.07*w <= x <= max(x1,x2)+.07*w
                 for x1,y1,x2,y2,dx,dy,norm,angle in segments for x in stems)
    parallel = False
    for i, (x1,y1,x2,y2,dx,dy,norm,angle) in enumerate(segments):
        if norm < .46*scale:
            continue
        for u1,v1,u2,v2,_,_,other,theta in segments[i+1:]:
            if other < .42*scale or min(abs(angle-theta), 180-abs(angle-theta)) > 8:
                continue
            lo, hi = sorted(((dx*(u-x1)+dy*(v-y1))/norm for u,v in ((u1,v1),(u2,v2))))
            lo, hi = max(0,lo), min(norm,hi)
            gap = (dx*((v1+v2)/2-y1)-dy*((u1+u2)/2-x1))/norm
            if hi-lo < .34*scale or not max(2,1.45*width,.055*scale) <= abs(gap) <= .21*scale:
                continue
            offsets = np.linspace(lo, hi, 9)
            xx = np.rint(x1 + offsets*dx/norm-gap*dy/(2*norm)).astype(int).clip(0,w-1)
            yy = np.rint(y1 + offsets*dy/norm+gap*dx/(2*norm)).astype(int).clip(0,h-1)
            if mask[yy, xx].sum() <= 2:
                parallel = True
                break
        if parallel:
            break
    top_stem = any(abs(dx) <= .15*abs(dy) and min(y1,y2) <= .22*h and max(y1,y2) >= .68*h
                   for x1,y1,x2,y2,dx,dy,norm,angle in segments)
    fork_centered = bool(forks[math.floor(h*.21):math.ceil(h*.79), math.floor(w*.21):math.ceil(w*.79)].any())
    return endpoints, junctions, straight, corners, len(stems), branch, length, width, parallel, top_stem, fork_centered

def measure(gray, threshold):
    mask = tight_mask(gray, threshold)
    if mask is None:
        return None
    h, w = mask.shape
    scale = max(h, w)
    n, labels, stats, centers = cv2.connectedComponentsWithStats(mask, connectivity=8)
    parts = sorted((tuple(map(int, box)) for box in stats[1:] if box[4] >= 2),
                   key=lambda box: -box[4])
    if not parts:
        parts = [tuple(map(int, stats[1]))]
    _, white, whites, holes_center = cv2.connectedComponentsWithStats(
        1 - np.pad(mask, 1), connectivity=4)
    hole_ids = [i for i in range(1, len(whites)) if i != white[0,0] and whites[i,4] >= 2]
    positions = [[round(float((holes_center[i][0]-1)/max(1,w-1)),3),
                  round(float((holes_center[i][1]-1)/max(1,h-1)),3)] for i in hole_ids]
    y, x = np.nonzero(mask)
    mb = mask.astype(bool)
    attrs = [IMAGE["iou"](mb, r) for r in (mb[:,::-1], mb[::-1,:], mb[::-1,::-1])]
    attrs += [(x.mean()+.5)/w, (y.mean()+.5)/h, float(mask.mean())]

    endpoints, junctions, straight, corners, stems, branch, length, width, parallel, top_stem, fork_centered = line_network(mask, scale)
    norm_length = max(length, int(mask.sum())/max(1., width)*.77) / scale
    if len(x) >= 3:
        xx, yy = float(x.var()), float(y.var())
        xy = float(np.mean((x-x.mean())*(y-y.mean())))
        spread = math.hypot(xx-yy, 2*xy)
        elongation = math.sqrt((xx+yy+spread)/max(.001, xx+yy-spread))
        skew = abs(math.degrees(math.atan2(2*xy,xx-yy))/2)
        skew = min(skew, 90-skew)
    else:
        elongation, skew = 1., 0.
    top = any(start <= .12*w and end >= .88*w for line in mask[:max(1, math.ceil(h*.14))]
              for start,end in runs(line))
    top = bool(top and h >= 10 and .48 <= h/w <= 2.1
               and np.count_nonzero(mask[math.ceil(.24*h):]) >= .39*len(x)
               and top_stem)
    sides = [mask, mask[::-1], mask.T, mask.T[::-1]]
    opening = 0.
    for side in sides:
        height, breadth = side.shape
        if min(height,breadth) < 5:
            continue
        for a,b in runs(~side[:max(1,math.ceil(.43*height))].any(axis=0)):
            if a >= .10*breadth and b <= .90*breadth:
                opening = max(opening, (b-a)/breadth)

    contours,_ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    contour = max(contours, key=cv2.contourArea)
    hull = cv2.convexHull(contour)
    perimeter = cv2.arcLength(hull, True)
    vertices = len(cv2.approxPolyDP(hull, .025*perimeter, True))
    convexity = cv2.contourArea(contour)/max(1, cv2.contourArea(hull))
    if min(h,w) >= 7 and len(holes_center) >= 3:
        ellipse = IMAGE["fit_shape"](mb, positions, len(parts))[0] == "A"
    else:
        ellipse = False
    x0,y0,w0,h0,area0 = parts[0]
    nested = any(x0 <= u and y0 <= v and u+a <= x0+w0 and v+b <= y0+h0
                 for u,v,a,b,_ in parts[1:])
    outer_ellipse = False
    if nested and min(h,w) >= 12 and convexity >= .93:
        envelope = np.zeros_like(mask)
        cv2.drawContours(envelope, [contour], 0, 1, -1)
        normalized = cv2.resize(envelope, (48,48), interpolation=cv2.INTER_NEAREST_EXACT)
        axis = (np.arange(48)-23.5)/24
        circle = axis[:,None]**2 + axis[None,:]**2 <= 1
        outer_ellipse = bool(.49 <= h/w <= 2.05 and IMAGE["iou"](normalized.astype(bool),circle) >= .953)
    frame = (vertices == 4 and convexity >= .93 and min(h,w) >= 12) or ellipse or outer_ellipse
    extras = [p for p in parts[1:] if p[4] >= max(2, .035*area0)]
    accessory = any(p[4] <= .30*area0 and max(p[2:4]) <= .45*scale and
                    (p[0]+p[2] <= x0 or x0+w0 <= p[0] or p[1]+p[3] <= y0 or y0+h0 <= p[1])
                    for p in extras)
    dx,dy = [],[]
    for a in range(len(parts)):
        u1,v1,w1,h1,_ = parts[a]
        for u2,v2,w2,h2,_ in parts[a+1:]:
            dx.append(max(u1-u2-w2, u2-u1-w1))
            dy.append(max(v1-v2-h2, v2-v1-h1))
    substantial = [p for p in parts if p[4] >= .045*area0]
    repeating = len(substantial) >= 3 and (
        min(p[4] for p in substantial) >= .50*area0 and
        max(p[2]/p[3] for p in substantial) <= 1.60*min(p[2]/p[3] for p in substantial))
    scatter = len(substantial) >= 3 and max(dx,default=-1) >= .14*w and max(dy,default=-1) >= .14*h \
        and min(p[4] for p in substantial) >= .28*area0
    xsplit = bool(len(parts) >= 2 and min(dx) >= max(1,.04*w))
    ysplit = bool(len(parts) >= 2 and min(dy) >= max(1,.04*h))
    if xsplit and ysplit:
        xsplit, ysplit = min(dx)/w > min(dy)/h, min(dx)/w <= min(dy)/h
    dot = ysplit and accessory
    vertical_parts = ysplit and parts[1][4] >= .33*area0
    inner_complex = False
    if frame and nested:
        major = int(np.argmax(stats[1:,cv2.CC_STAT_AREA]))+1
        content = (mask > 0) & (labels != major)
        if content.any():
            ey,ex = np.where(content)
            inner = content[ey.min():ey.max()+1, ex.min():ex.max()+1].astype(np.uint8)
            network = line_network(inner,max(inner.shape))
            inner_complex = len(parts) >= 4 or network[1] > 0 or network[6] >= 2.2*max(inner.shape)
    tail = 0.
    hole_x = .5
    if len(hole_ids) == 1:
        hx,hy,hw,hh,ha = whites[hole_ids[0]]
        hole_x = positions[0][0]
        vy = max(hy-1, h-(hy-1+hh)) / h
        vx = max(hx-1, w-(hx-1+hw)) / w
        tail = max(vy * (1 if h >= .75*w else .8), vx * (1 if w >= .75*h else .8))
    return dict(holesRaw=len(hole_ids), positions=positions, ratio=round(h/w,3), components=len(parts),
                size=[w,h], boxes=parts, attrs=[float(a) for a in attrs], endpoints=endpoints,
                junctions=junctions, straight_ratio=round(straight,5), corner_count=corners,
                verticalStems=stems, horizontalBranch=bool(branch), topBar=top,
                centeredJunction=fork_centered, opening=opening,
                convexity=convexity, outerVertices=vertices, ellipse=ellipse, frame=frame,
                nested=nested, complexInterior=inner_complex, tail=tail, holeX=hole_x,
                is_horizontal_split=xsplit or nested, is_vertical_with_dot=dot,
                is_vertical_parts=vertical_parts, is_repeated_scatter=bool(repeating or scatter),
                lineLength=norm_length, strokeWidth=width/scale, accessory=accessory,
                skew=skew, elongation=elongation, parallel=bool(parallel))

def b_candidates(m):
    if m is None:
        return []
    w,h = m["size"]
    j,e = m["junctions"],m["endpoints"]
    holes,parts = m["holesRaw"],m["components"]
    straight = m["straight_ratio"]
    found = []
    if m["frame"] and m["nested"] and holes >= 1:
        found.append("W" if m["complexInterior"] else "X")
    if m["is_repeated_scatter"]:
        found.append("V")
    if m["is_vertical_with_dot"]:
        found.append("T")
    if m["is_vertical_parts"]:
        found.append("U")
    if m["is_horizontal_split"]:
        found.append("S")
    if parts == 1 and holes >= 1:
        if m["ellipse"]:
            found.append("A")
        if holes == 1 and m["convexity"] >= .94 and 3 <= m["outerVertices"] <= 5 and not m["ellipse"]:
            found.append("L")
        if holes == 1 and m["tail"] >= .52 and e >= 1:
            if m["verticalStems"] and abs(m["holeX"]-.5) >= .17:
                found.append("F")
            found.append("J" if h/w >= 1.27 else "K")
        found.append("D" if holes == 1 else "E")
    if parts == 1 and holes == 0:
        if m["topBar"]:
            found.append("R")
        if m["verticalStems"] >= 2:
            found.append("M")
        if m["horizontalBranch"] and j:
            found.append("N")
        if j in (1,2) and 3 <= e <= 8 and straight >= .68 and min(w,h) >= 9 and \
           m["centeredJunction"] and max(abs(m["attrs"][3]-.5),abs(m["attrs"][4]-.5)) <= .15:
            found.append("O")
        if max(w,h) <= 9 or (m["elongation"] >= 5 and e <= 2 and not j):
            found.append("Q")
        bent_line = straight >= .84 and m["corner_count"] and m["strokeWidth"] <= .22
        if e == 2 and not j and bent_line:
            found.append("B")
        if e == 2 and not j and m["opening"] >= .23 and straight <= .72 and m["strokeWidth"] <= .23:
            found.append("C")
        if e == 2 and not j and straight <= .47 and m["opening"] <= .15 and m["lineLength"] >= .95:
            found.append("G")
    return found

def a_shape(m):
    if m["accessory"]:
        return 3
    if m["lineLength"] >= 2.65 or m["junctions"] >= 4:
        return 2
    if m["lineLength"] <= 1.85 and m["junctions"] <= 1:
        return 0
    return 1

def a_texture(m):
    if m["parallel"]:
        return 3
    if m["strokeWidth"] >= .115:
        return 1
    if m["skew"] >= 15 and m["elongation"] >= math.sqrt(2.5):
        return 2
    return 0

def a_key(m):
    return A_KEYS[4*a_shape(m)+a_texture(m)]

def glyph_pages(features, hashes):
    grouped = defaultdict(list)
    for cp, r in features.items():
        if r["source"]:
            grouped[(ROOT / r["source"]["path"]).resolve()].append(cp)
    for path,cps in grouped.items():
        actual = digest(path)
        sources = {features[cp]["source"]["sha256"] for cp in cps}
        if sources != {actual}:
            raise ValueError(f"锁定图源 SHA256 不符 {path}")
        hashes[str(path)] = actual
        kind = features[cps[0]]["source"]["kind"]
        if kind == "锁定轮廓渲染":
            page = IMAGE["svg_pixels"](path.read_bytes())
        elif kind == "锁定栅格":
            with Image.open(path) as im:
                page = np.asarray(im.convert("L") if im.mode == "L" else IMAGE["matte"](im))
        elif kind != "已有字体渲染":
            raise ValueError(kind)
        for cp in cps:
            src = features[cp]["source"]
            if kind == "已有字体渲染":
                gray = IMAGE["render_font"](int(cp[2:],16), path, src["faceIndex"])
            elif src.get("cropXYWH"):
                x,y,w,h = src["cropXYWH"]
                gray = page[y:y+h,x:x+w]
                assert gray.shape == (h,w), (cp,path)
            else:
                gray = page
            yield cp,gray

def extract(features, hashes):
    measured = {}
    for cp,gray in glyph_pages(features,hashes):
        measured[cp] = {str(t): measure(gray, t) for t in THRESHOLDS}
        if len(measured) % 4000 == 0:
            print("Measured",len(measured),flush=True)
    assert len(measured) == 29089 and all(v["128"] for v in measured.values())
    return measured

def classify(cp, measurements, old, baseline_anchor, cells):
    old_b = old["BC"][0]
    rank = {t: b_candidates(m) for t,m in measurements.items()}
    central = rank.get("128", [])
    first = {t: candidates[0] if candidates else None for t,candidates in rank.items()}
    # D/E are observable fallback classes, but the generic D/E result is not
    # affirmative evidence for moving previously assigned non-default rows.
    targeted = old["bDefault"] or old_b in "DE" or old["BC"] == "GZ"
    proposal = central[0] if central and targeted else None
    accepted = proposal is not None and all(v == proposal for v in first.values())
    selected = proposal if accepted else old_b
    b_default = old["bDefault"] and not accepted
    # Independent runs expose the threshold dependence of every stage.
    # Operational draft B uses the above three-threshold release gate.
    independent = {}
    gated = {}
    for t in map(str,THRESHOLDS):
        m = measurements.get(t)
        for pool,b in ((independent, (first.get(t) or old_b) if targeted else old_b),
                       (gated,selected)):
            if cp in O20:
                code = baseline_anchor
            elif not m:
                code = old_b+"ZZZ"
            else:
                h = min(m["holesRaw"],3)
                bc,_ = V4["select"](b, {"codepoint":cp,"ratio":m["ratio"],"holes":h,"measured":m})
                assert bc in cells
                d,_ = D["global_key"](cp,{"holes":h},{cp:m["attrs"]})
                code = bc+d+a_key(m)
            pool[t] = code
    return dict(BCDA=gated["128"], thresholds=gated, independentThresholds=independent,
                bDefault=b_default, bProposal=proposal, bAccepted=accepted, rankedB=rank)

