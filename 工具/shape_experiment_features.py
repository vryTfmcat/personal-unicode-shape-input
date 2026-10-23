"""Isolated subject/contour descriptors. Never changes the historical 216D cache."""
from __future__ import annotations
import math
import numpy as np
from PIL import Image, ImageFont
from shape_lab_features import components
from shape_quality_v2 import skeleton

VERSION = 'subject-contour-local-arms-v2'


def dilate(mask, radius=1):
    result=mask.copy()
    for _ in range(radius):
        p=np.pad(result,1)
        result=np.logical_or.reduce([p[dy:dy+mask.shape[0],dx:dx+mask.shape[1]] for dy in range(3) for dx in range(3)])
    return result


def component_mask(mask, item, connectivity=8):
    """Recover the actual connected component, not every pixel in its bbox."""
    crop=mask[item['y0']:item['y1'],item['x0']:item['x1']]
    h,w=crop.shape;bits=_bits(crop);left=sum(1<<(y*w) for y in range(h));right=left<<(w-1)
    remaining=bits
    while remaining:
        reached=_flood(bits,remaining&-remaining,w,left,right,connectivity)
        if reached.bit_count()==item['area']:
            result=np.zeros_like(mask);result[item['y0']:item['y1'],item['x0']:item['x1']]=_array(reached,crop.shape)
            return result
        remaining &= ~reached
    raise ValueError('Component could not be recovered')


def _bits(mask):return int.from_bytes(np.packbits(mask.ravel(),bitorder='little').tobytes(),'little')
def _array(bits,shape):
    n=shape[0]*shape[1]
    return np.unpackbits(np.frombuffer(bits.to_bytes((n+7)//8,'little'),dtype='uint8'),bitorder='little')[:n].reshape(shape).astype(bool)
def _flood(allowed,seed,width,left,right,connectivity):
    reached=seed
    while True:
        horizontal=reached|((reached&~right)<<1)|((reached&~left)>>1)
        expanded=(horizontal|(horizontal<<width)|(horizontal>>width)) if connectivity==8 else (horizontal|(reached<<width)|(reached>>width))
        expanded &= allowed
        if expanded==reached:return reached
        reached=expanded


def filled(mask):
    background=~np.pad(mask,1);h,w=background.shape;bits=_bits(background)
    left=sum(1<<(y*w) for y in range(h));right=left<<(w-1)
    border=((1<<w)-1)|(((1<<w)-1)<<((h-1)*w))|left|right
    outside=_flood(bits,bits&border,w,left,right,4)
    return mask|_array(bits&~outside,background.shape)[1:-1,1:-1]


def crossing_topology(mask):
    """Crossing number counts graph arms, unlike raw 8-neighbour pixel degree."""
    sk=skeleton(mask);p=np.pad(sk,1)
    ns=[p[:-2,1:-1],p[:-2,2:],p[1:-1,2:],p[2:,2:],p[2:,1:-1],p[2:,:-2],p[1:-1,:-2],p[:-2,:-2]]
    transitions=sum((~ns[i]&ns[(i+1)%8]).astype('uint8') for i in range(8))
    # A multi-pixel intersection can contain several degree-three pixels. Merge
    # only nearby junction cores, then count their local exit ports. Whole-glyph
    # endpoints would incorrectly call a tree with many separate forks radial.
    cores=sk&(transitions>=3)
    # Diagonal X crossings can leave a 2x2 skeletal block whose individual
    # crossing numbers are only two. Recover that local graph node explicitly.
    blocks=sk[:-1,:-1]&sk[1:,:-1]&sk[:-1,1:]&sk[1:,1:]
    for dy,dx in ((0,0),(0,1),(1,0),(1,1)):
        cores[dy:dy+blocks.shape[0],dx:dx+blocks.shape[1]] |= blocks
    junctions=[]
    for region in components(dilate(cores,2),8):
        zone=component_mask(dilate(cores,2),region)
        core=zone&cores
        ports=sk&~zone&dilate(zone)
        item=dict(region)
        item['armCount']=len(components(ports,8))
        item['coreBbox']=bounds(core)
        item['measurement']='local-exit-ports-radius-2'
        junctions.append(item)
    return {'endpoints':int((sk&(transitions==1)).sum()),'junctions':len(junctions),
            'junctionObjects':junctions,'skeleton':sk}


def bounds(mask):
    yy,xx=np.nonzero(mask)
    return [int(xx.min()),int(yy.min()),int(xx.max()+1),int(yy.max()+1)]


def normalized(mask,size=32):
    if not mask.any():return np.zeros((size,size))
    x0,y0,x1,y1=bounds(mask)
    return np.array(Image.fromarray(mask[y0:y1,x0:x1].astype('uint8')*255).resize((size,size),Image.Resampling.BOX))/255


def signature(mask,thin=None,fill=None):
    """Filled contour has first priority; thin strokes form a separate second view."""
    fill=filled(mask) if fill is None else fill;contour=normalized(fill,16)
    thin=normalized(skeleton(mask) if thin is None else thin,16)
    # Each view is normalized as a block, not weighted implicitly by pixel count.
    return np.r_[contour.flatten()/16,thin.flatten()/32].astype('float32')


def render(char,path,index=0,size=96,weight=0,fonts=None):
    fonts={} if fonts is None else fonts;key=(str(path),index,size)
    if key not in fonts:fonts[key]=ImageFont.truetype(str(path),size,index=index)
    font=fonts[key];core=font.getmask(char,mode='L');box=core.getbbox()
    if box is None:raise ValueError('empty glyph')
    im=Image.frombytes('L',core.size,bytes(core)).crop(box)
    extent=max(im.size)/size
    scale=60/max(im.size);im=im.resize((max(1,round(im.width*scale)),max(1,round(im.height*scale))),Image.Resampling.LANCZOS)
    canvas=Image.new('L',(64,64));canvas.paste(im,((64-im.width)//2,(64-im.height)//2))
    mask=np.array(canvas)>.35*255
    if weight:
        p=np.pad(mask,1)
        views=[p[1+dy:65+dy,1+dx:65+dx] for dy,dx in ((0,0),(1,0),(-1,0),(0,1),(0,-1))]
        mask=np.logical_or.reduce(views) if weight>0 else np.logical_and.reduce(views)
        if not mask.any():raise ValueError('weight perturbation erased glyph')
    return mask,extent


def observe(mask,extent=1.):
    fg=[g for g in components(mask,8) if g['area']>=3]
    if not fg:raise ValueError('no observable ink')
    # Prefer the enclosing outline, rather than the component with most black pixels.
    major=max(fg,key=lambda g:(g['x1']-g['x0'])*(g['y1']-g['y0']))
    full=bounds(mask);full_area=(full[2]-full[0])*(full[3]-full[1])
    major_area=(major['x1']-major['x0'])*(major['y1']-major['y0'])
    body=mask.copy() if major_area<full_area*.6 else component_mask(mask,major)
    silhouette=filled(body)
    x0,y0,x1,y1=bounds(body);w,h=x1-x0,y1-y0
    topology=crossing_topology(body)
    holes=[g for g in components(~np.pad(body,1),4) if not g['edge'] and g['area']>=5]
    for g in holes:
        for k in ('x0','x1','cx'):g[k]-=1
        for k in ('y0','y1','cy'):g[k]-=1
    yy,xx=np.nonzero(body);cov=np.cov(np.array([xx,yy])) if len(xx)>2 else np.eye(2)
    values,vectors=np.linalg.eigh(cov);v=vectors[:,-1]
    anisotropy=float(values[-1]/max(.001,values[0]))
    angle=math.degrees(math.atan2(-v[1],v[0]))%180
    # Original absolute size stays distinct from shape-normalized masks.
    return {'bbox':[x0,y0,x1,y1],'ratio':w/h,'extent':extent,'density':float(body.sum()/(w*h)),
            'holes':holes,'parts':fg,'body':body,'silhouette':silhouette,'mask':mask,
            'endpoints':topology['endpoints'],'junctions':topology['junctions'],
            'junctionObjects':topology['junctionObjects'],'signature':signature(body,topology['skeleton'],silhouette),
            'angle':angle,'anisotropy':anisotropy}


def serialize(f):
    return {k:v for k,v in f.items() if k not in ('mask','body','silhouette','signature')}
