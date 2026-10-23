"""Deterministic font coverage and visual descriptors, without Unicode-name hints."""
from __future__ import annotations
import hashlib
import struct
from functools import lru_cache
from pathlib import Path
import numpy as np
from PIL import Image, ImageFont

VERSION = 'glyph-rle-v1'
FONT_SIZE = 48
PREFERRED = ('seguisym.ttf','segoeui.ttf','seguihis.ttf','Nirmala.ttc','ebrima.ttf',
             'arial.ttf','LeelawUI.ttf','malgun.ttf','msyh.ttc','himalaya.ttf',
             'monbaiti.ttf','phagspa.ttf','javatext.ttf','mmrtext.ttf','sylfaen.ttf',
             'gadugi.ttf','taile.ttf','ntailu.ttf','msyi.ttf','mvboli.ttf',
             'seguiemj.ttf','l_10646.ttf','micross.ttf','cambria.ttc',
             'msgothic.ttc','YuGothR.ttc','msjh.ttc','NotoSansSC-VF.ttf')


def font_cmap(path: Path, index=0) -> tuple[set[int], str]:
    """Read Unicode cmap formats 4/12/13. Reject missing glyph IDs and symbol maps."""
    data=path.read_bytes()
    u16=lambda p:struct.unpack_from('>H',data,p)[0]
    u32=lambda p:struct.unpack_from('>I',data,p)[0]
    offset=u32(12+4*index) if data[:4]==b'ttcf' else 0
    tables={}
    for i in range(u16(offset+4)):
        p=offset+12+16*i;tables[data[p:p+4]]=u32(p+8)
    if b'head' in tables and u16(tables[b'head']+16)&0x4000:
        return set(),path.stem # OpenType Last Resort glyphs are generic range markers, not real coverage.
    coverage=set();cmap=tables.get(b'cmap')
    if cmap is None:return coverage,path.stem
    for i in range(u16(cmap+2)):
        p=cmap+4+8*i;platform,encoding=u16(p),u16(p+2)
        if not (platform==0 or platform==3 and encoding in (1,10)):continue
        sub=cmap+u32(p+4);fmt=u16(sub)
        if fmt in (12,13):
            for j in range(u32(sub+12)):
                start,end,glyph=struct.unpack_from('>III',data,sub+16+12*j)
                if start>0x10ffff or end>0x10ffff:continue
                if fmt==13:
                    if glyph:coverage.update(range(start,end+1))
                else:coverage.update(range(start+(glyph==0),end+1))
        elif fmt==4:
            n=u16(sub+6)//2;endp=sub+14;startp=endp+2*n+2;deltap=startp+2*n;rangep=deltap+2*n
            for j in range(n):
                start,end=u16(startp+2*j),u16(endp+2*j)
                delta,roff=u16(deltap+2*j),u16(rangep+2*j)
                for cp in range(start,min(end,0xfffe)+1):
                    if not roff:gid=(cp+delta)&0xffff
                    else:
                        address=rangep+2*j+roff+2*(cp-start)
                        if address+2>len(data):continue
                        raw=u16(address);gid=(raw+delta)&0xffff if raw else 0
                    if gid:coverage.add(cp)
    family=path.stem
    if b'name' in tables:
        p=tables[b'name'];strings=p+u16(p+4)
        names=[]
        for i in range(u16(p+2)):
            r=p+6+12*i;platform,encoding,language,name_id,length,off=struct.unpack_from('>6H',data,r)
            if name_id==1 and platform in (0,3):
                try:names.append((language!=0x409,data[strings+off:strings+off+length].decode('utf-16-be')))
                except UnicodeError:pass
        if names:family=sorted(names)[0][1]
    return coverage,family


def inventory(font_dir: Path, extra_dirs: list[Path] | None=None, target_codepoints: set[int] | None=None) -> list[dict]:
    files=[]
    for name in PREFERRED:
        path=font_dir/name
        if path.is_file():files.append(path)
    preferred=set(files)
    # Append only fonts/faces that add needed codepoints, keeping the initial reference order.
    files.extend(sorted(p for p in font_dir.iterdir() if p.suffix.lower() in ('.ttf','.otf','.ttc') and p not in preferred))
    for folder in extra_dirs or []:
        files.extend(sorted(p for p in folder.iterdir() if p.suffix.lower() in ('.ttf','.otf','.ttc')))
    result=[];covered=set()
    for path in dict.fromkeys(files):
        try:
            header=path.read_bytes()[:12];faces=struct.unpack_from('>I',header,8)[0] if header[:4]==b'ttcf' else 1
        except (OSError,struct.error):continue
        for index in range(faces):
            try:
                coverage,family=font_cmap(path,index)
                needed=coverage if target_codepoints is None else coverage & target_codepoints
                if not (path in preferred and index==0) and not needed-covered:continue
                font=ImageFont.truetype(str(path),FONT_SIZE,index=index)
            except (OSError,ValueError,struct.error):continue
            result.append({'path':str(path),'index':index,'family':family,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
                           'coverage':coverage,'font':font})
            covered.update(needed)
    return result


def components(mask: np.ndarray, connectivity=8) -> list[dict]:
    """Run-length union-find. Work scales with rows/runs rather than Python pixels."""
    parent=[];runs=[];previous=[]
    def root(i):
        while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
        return i
    for y,row in enumerate(mask):
        edges=np.flatnonzero(np.diff(np.r_[False,row,False].astype(np.int8)))
        current=[];k=0;expand=int(connectivity==8)
        for start,end in zip(edges[::2],edges[1::2]):
            i=len(parent);parent.append(i);runs.append((int(start),int(end),y));current.append(i)
            while k<len(previous) and runs[previous[k]][1]+expand<=start:k+=1
            j=k
            while j<len(previous) and runs[previous[j]][0]-expand<end:
                a,b=root(i),root(previous[j])
                if a!=b:parent[max(a,b)]=min(a,b)
                j+=1
        previous=current
    grouped={}
    for i,(start,end,y) in enumerate(runs):
        r=root(i);g=grouped.setdefault(r,{'area':0,'x0':start,'x1':end,'y0':y,'y1':y+1,'sx':0.,'sy':0.,'edge':False})
        count=end-start;g['area']+=count;g['sx']+=(start+end-1)*count/2;g['sy']+=y*count
        g['x0']=min(g['x0'],start);g['x1']=max(g['x1'],end);g['y0']=min(g['y0'],y);g['y1']=max(g['y1'],y+1)
        g['edge']|=start==0 or end==mask.shape[1] or y==0 or y==mask.shape[0]-1
    for g in grouped.values():g['cx']=g.pop('sx')/g['area'];g['cy']=g.pop('sy')/g['area']
    return sorted(grouped.values(),key=lambda g:-g['area'])


def longest(values: np.ndarray) -> int:
    edges=np.flatnonzero(np.diff(np.r_[False,values,False].astype(np.int8)))
    return int(max(edges[1::2]-edges[::2],default=0))


def describe(mask: np.ndarray, width: int, height: int, font_size=FONT_SIZE) -> dict:
    if not mask.any():raise ValueError('empty glyph')
    # Topology uses at most 48 px on its longest side; physical size retains original bbox.
    if max(mask.shape)>48:
        picture=Image.fromarray(mask.astype(np.uint8)*255);picture.thumbnail((48,48),Image.Resampling.NEAREST)
        mask=np.asarray(picture)>127
    h,w=mask.shape;ink=int(mask.sum());fg=[g for g in components(mask,8) if g['area']>=2]
    bg=[g for g in components(~np.pad(mask,1),4) if not g['edge'] and g['area']>=2]
    for g in bg:
        for key in ('x0','x1','cx'):g[key]-=1
        for key in ('y0','y1','cy'):g[key]-=1
    xs,ys=np.nonzero(mask)[1],np.nonzero(mask)[0]
    hr=np.array([longest(row) for row in mask]);vr=np.array([longest(col) for col in mask.T])
    def thickness(values):
        p=int(values.argmax());good=values>=values[p]*.9;lo=hi=p
        while lo>0 and good[lo-1]:lo-=1
        while hi+1<len(values) and good[hi+1]:hi+=1
        return hi-lo+1
    ht,vt=thickness(hr),thickness(vr)
    corners=np.zeros_like(mask);cw,ch=max(1,int(w*.2)),max(1,int(h*.2))
    corners[:ch,:cw]=corners[:ch,-cw:]=corners[-ch:,:cw]=corners[-ch:,-cw:]=True
    sy=1-float(np.logical_xor(mask,mask[:,::-1]).sum())/max(1,ink*2)
    sx=1-float(np.logical_xor(mask,mask[::-1,:]).sum())/max(1,ink*2)
    if len(xs)>1 and np.std(xs)>0 and np.std(ys)>0:diagonal=float(np.corrcoef(xs,ys)[0,1])
    else:diagonal=0.
    border=[float(mask[:max(1,h//6)].mean()),float(mask[-max(1,h//6):].mean()),
            float(mask[:,:max(1,w//6)].mean()),float(mask[:,-max(1,w//6):].mean())]
    image=Image.fromarray(mask.astype(np.uint8)*255).resize((8,8),Image.Resampling.BOX)
    bit=np.asarray(image,dtype=np.float32)/255
    major=fg[0] if fg else {'area':ink,'x0':0,'x1':w,'y0':0,'y1':h,'cx':w/2,'cy':h/2}
    extras=[g for g in fg[1:4] if g['area']>=max(2,ink*.01)]
    return {'width':width,'height':height,'extentEm':round(max(width,height)/font_size,5),
            'ratio':round(width/max(1,height),5),'density':round(ink/(w*h),5),
            'holes':len(bg),'components':len(fg),'holeRatio':round(sum(g['area'] for g in bg)/(w*h),5),
            'symV':round(sy,5),'symH':round(sx,5),'diagonal':round(diagonal,5),
            'cornerInk':round(float(mask[corners].sum())/ink,5),
            'hRun':round(float(hr.max())/w,5),'vRun':round(float(vr.max())/h,5),
            'lineCoverage':round(min(1.,float(hr.max()*ht+vr.max()*vt-ht*vt)/ink),5),
            'hPos':round(float(hr.argmax())/max(1,h-1),5),'vPos':round(float(vr.argmax())/max(1,w-1),5),
            'centroidX':round(float(xs.mean())/max(1,w-1),5),'centroidY':round(float(ys.mean())/max(1,h-1),5),
            'border':border,'maskSize':[w,h], 'major':major,'extras':extras,'holeObjects':bg[:3],
            'bitmap':[round(float(x),3) for x in bit.flatten()]}


def extract(char: str, fonts: list[dict], preferred_family: str | None=None) -> dict:
    cp=ord(char);choices=[f for f in fonts if cp in f['coverage']]
    if preferred_family:choices.sort(key=lambda f:f['family']!=preferred_family)
    if not choices:return {'observed':False,'reason':'no-font-cmap'}
    for source in choices:
        try:
            core=source['font'].getmask(char,mode='L');box=core.getbbox()
            if box is None:continue
            arr=np.asarray(core,dtype=np.uint8).reshape(core.size[1],core.size[0])
            arr=arr[box[1]:box[3],box[0]:box[2]];mask=arr>=96
            if not mask.any():continue
            props=describe(mask,box[2]-box[0],box[3]-box[1])
            return dict(props,observed=True,font=source['family'],fontPath=source['path'],fontIndex=source.get('index',0))
        except (ValueError,OSError):continue
    return {'observed':False,'reason':'empty-or-unsupported-render'}
