"""High-resolution, locked-font, cautiously accepted multi-view glyph descriptors."""
import gzip,hashlib,json,math
from pathlib import Path
import numpy as np
from PIL import Image,ImageFont
from shape_lab_features import font_cmap,components
from shape_strategy_lab import LAB,save

ROOT=LAB/'首次优化';VERSION='glyph-quality-v2-64px-render-resilient'
STRUCTURE_NAMES=['logRatio','density','holes','parts','holeArea','symV','symH','centroidX','centroidY',
    'topInk','bottomInk','leftInk','rightInk','horizontalPeak','verticalPeak','strokeThickness',
    'skeletonEndpoints','skeletonJunctionRegions','extraX','extraY','extraArea','holeX','holeY','diagonal']
STRUCTURE_WEIGHTS=[.32,.14,.30,.22,.15,.16,.16,.12,.12,.12,.12,.12,.12,.12,.12,.10,.22,.22,.12,.12,.12,.12,.12,.08]


def skeleton(mask):
    a=mask.copy()
    for _ in range(48):
        changed=False
        for phase in (0,1):
            p=np.pad(a,1);ns=[p[:-2,1:-1],p[:-2,2:],p[1:-1,2:],p[2:,2:],p[2:,1:-1],p[2:,:-2],p[1:-1,:-2],p[:-2,:-2]]
            count=sum(v.astype('uint8') for v in ns)
            transitions=sum((~ns[i]&ns[(i+1)%8]).astype('uint8') for i in range(8))
            if phase==0:gate=~(ns[0]&ns[2]&ns[4])&~(ns[2]&ns[4]&ns[6])
            else:gate=~(ns[0]&ns[2]&ns[6])&~(ns[0]&ns[4]&ns[6])
            remove=a&(count>=2)&(count<=6)&(transitions==1)&gate
            if remove.any():a[remove]=False;changed=True
        if not changed:break
    return a


def render(char,path,index,fonts):
    core=None;used_size=None
    for size in (96,48,64,128):
        key=(path,index,size)
        try:
            if key not in fonts:fonts[key]=ImageFont.truetype(path,size,index=index)
            core=fonts[key].getmask(char,mode='L');used_size=size;break
        except (OSError,ValueError):continue
    if core is None:return None
    box=core.getbbox()
    if not box:return None
    image=Image.frombytes('L',core.size,bytes(core)).crop(box);width,height=image.size
    scale=60/max(width,height);image=image.resize((max(1,round(width*scale)),max(1,round(height*scale))),Image.Resampling.LANCZOS)
    canvas=Image.new('L',(64,64));canvas.paste(image,((64-image.width)//2,(64-image.height)//2))
    return np.asarray(canvas,dtype=np.float32)/255,math.log(max(.05,width/max(1,height))),used_size


def describe(image,log_ratio):
    threshold=.35 if image.max()>.35 else max(.0001,float(image.max())*.5)
    mask=image>threshold;all_fg=components(mask,8);fg=[g for g in all_fg if g['area']>=2] or all_fg
    bg=[g for g in components(~np.pad(mask,1),4) if not g['edge'] and g['area']>=2]
    ink=max(1,mask.sum());density=float(mask.mean());ys,xs=np.nonzero(mask)
    extra=fg[1] if len(fg)>1 else None;hole=bg[0] if bg else None
    small=np.array(Image.fromarray((image*255).astype('uint8')).resize((32,32),Image.Resampling.BOX))>96
    sk=skeleton(small);p=np.pad(sk,1);degree=sum(p[1+dy:33+dy,1+dx:33+dx].astype('uint8') for dy,dx in [(-1,-1),(-1,0),(-1,1),(0,-1),(0,1),(1,-1),(1,0),(1,1)])
    endpoint=min(12,int((sk&(degree==1)).sum()))/12
    junction=min(12,len(components(sk&(degree>=3),8)))/12
    perimeter=(mask&~(np.roll(mask,1,0)&np.roll(mask,-1,0)&np.roll(mask,1,1)&np.roll(mask,-1,1))).sum()
    diagonal=float(np.corrcoef(xs,ys)[0,1]) if np.std(xs)>0 and np.std(ys)>0 else 0.
    stats=[log_ratio,density,min(6,len(bg))/6,min(8,len(fg))/8,sum(g['area'] for g in bg)/4096,
        1-float(np.logical_xor(mask,mask[:,::-1]).sum())/(2*ink),1-float(np.logical_xor(mask,mask[::-1,:]).sum())/(2*ink),
        float(xs.mean()/63),float(ys.mean()/63),float(mask[:12].mean()),float(mask[-12:].mean()),float(mask[:,:12].mean()),float(mask[:,-12:].mean()),
        float(mask.sum(1).max()/64),float(mask.sum(0).max()/64),float(ink/max(1,perimeter)/64),endpoint,junction,
        extra['cx']/63 if extra else .5,extra['cy']/63 if extra else .5,extra['area']/ink if extra else 0,
        (hole['cx']-1)/63 if hole else .5,(hole['cy']-1)/63 if hole else .5,diagonal]
    dy,dx=np.gradient(image);magnitude=np.hypot(dx,dy);angle=np.mod(np.arctan2(dy,dx),np.pi);bins=np.minimum(7,(angle/(np.pi/8)).astype('int32'))
    hog=[]
    for y in range(0,64,16):
        for x in range(0,64,16):hog.extend(np.bincount(bins[y:y+16,x:x+16].flatten(),weights=magnitude[y:y+16,x:x+16].flatten(),minlength=8))
    hog=np.sqrt(np.array(hog,dtype='float32'));hog/=max(1e-6,np.linalg.norm(hog))
    return np.array(stats,dtype='float32'),hog


def build(records,source):
    ROOT.mkdir(parents=True,exist_ok=True);folder=ROOT/'缓存';folder.mkdir(exist_ok=True)
    observed=[r for r in records if r['feature']['observed']]
    manifest={'version':VERSION,'cp':[r['cp'] for r in observed],'fonts':source['featureManifest']['fonts'],
        'primary':[(r['cp'],r['feature']['fontPath'],r['feature'].get('fontIndex',0)) for r in observed]}
    signature=hashlib.sha256(json.dumps(manifest,sort_keys=True).encode()).hexdigest()[:20];cache=folder/(signature+'.npz')
    quality_path=folder/(signature+'.quality.jsonl.gz')
    if cache.exists() and quality_path.exists():
        with np.load(cache) as data:pixels=data['pixels'];stats=data['stats'];hog=data['hog']
    else:
        candidates=[]
        for f in source['featureManifest']['fonts']:
            coverage,_=font_cmap(Path(f['path']),f.get('index',0));candidates.append((f,coverage))
        fonts={};pixels=[];stats=[];hog=[];qa=[];partial=folder/(signature+'.partial.npz')
        if partial.exists():
            with np.load(partial) as data:
                pixels=list(data['pixels']);stats=list(data['stats']);hog=list(data['hog']);qa=[json.loads(s) for s in data['quality']]
            print(f'恢复字形检查点 {len(pixels)}/{len(observed)}',flush=True)
        completed=len(pixels)
        with gzip.open(quality_path,'wt',encoding='utf-8') as stream:
            for q in qa:stream.write(json.dumps(q,ensure_ascii=True)+'\n')
            for i,r in enumerate(observed[completed:],completed+1):
                f=r['feature'];result=render(r['char'],f['fontPath'],f.get('fontIndex',0),fonts)
                if result is None:raise ValueError(f'锁定主字体失效 U+{r["cp"]:04X}')
                primary,ratio,native_size=result
                a,h=describe(primary,ratio);views=[primary];attributes=[a];histograms=[h]
                q={'cp':r['cp'],'primaryFont':f['font'],'renderSize':native_size,'alternate':None,'acceptedViews':1,'reviewFlags':[]}
                if native_size!=96:q['reviewFlags'].append('native-size-fallback')
                alternate=next((item for item,cov in candidates if r['cp'] in cov and item['family']!=f['font']),None)
                if alternate:
                    result=render(r['char'],alternate['path'],alternate.get('index',0),fonts)
                    if result is not None:
                        other,other_ratio,other_size=result;b,g=describe(other,other_ratio);rms=float(np.sqrt(((primary-other)**2).mean()))
                        accepted=abs(ratio-other_ratio)<math.log(1.3) and a[2]==b[2] and a[3]==b[3] and rms<.22
                        q['alternate']={'font':alternate['family'],'renderSize':other_size,'rms':rms,'accepted':bool(accepted)}
                        if accepted:views.append(other);attributes.append(b);histograms.append(g);q['acceptedViews']=2
                        else:q['reviewFlags'].append('alternate-font-disagreement')
                    else:q['reviewFlags'].append('alternate-font-render-failed')
                if np.count_nonzero(primary>.35)<12:q['reviewFlags'].append('few-ink-pixels')
                if primary.max()<=.35:q['reviewFlags'].append('weak-ink-intensity')
                # Average descriptors of agreeing views; display always uses the actual primary glyph.
                pixel_views=[np.array(Image.fromarray((v*255).astype('uint8')).resize((32,32),Image.Resampling.BOX),dtype='float32').flatten()/255 for v in views]
                pixels.append(np.mean(pixel_views,0));stats.append(np.mean(attributes,0));hog.append(np.mean(histograms,0))
                stream.write(json.dumps(q,ensure_ascii=True)+'\n')
                qa.append(q)
                if i%2000==0:
                    np.savez_compressed(partial,pixels=np.array(pixels),stats=np.array(stats),hog=np.array(hog),quality=np.array([json.dumps(q) for q in qa]))
                    print(f'高精度字形与结构 {i}/{len(observed)}',flush=True)
        pixels=np.array(pixels,dtype='float32');stats=np.array(stats,dtype='float32');hog=np.array(hog,dtype='float32')
        np.savez_compressed(cache,pixels=pixels,stats=stats,hog=hog)
        save(folder/(signature+'.manifest.json'),manifest)
    mean=pixels.mean(0);z=pixels-mean;values,vectors=np.linalg.eigh(z.T@z/max(1,len(z)-1));basis=vectors[:,-64:][:,::-1].copy()
    for col in range(64):
        if basis[np.argmax(abs(basis[:,col])),col]<0:basis[:,col]*=-1
    scale=float(np.sqrt(max(1e-8,values[-64:].sum())));sm=stats.mean(0);ss=np.maximum(stats.std(0),.1)
    visual=z@basis/scale;structural=(stats-sm)/ss*np.array(STRUCTURE_WEIGHTS)
    matrix=np.concatenate([visual,structural,hog*.5],1).astype('float32')
    model={'featureVersion':VERSION,'pixelMean':mean.tolist(),'basis':basis.tolist(),'visualScale':scale,
        'structureNames':STRUCTURE_NAMES,'structureMean':sm.tolist(),'structureScale':ss.tolist(),'structureWeights':STRUCTURE_WEIGHTS,
        'hogMultiplier':.5,'dimensions':matrix.shape[1],'pixelVarianceExplained':float(values[-64:].sum()/max(1e-8,values.sum())),
        'featureCache':str(cache),'qualityRecords':str(quality_path),'scopeSignature':signature,'referenceSize':96,'canvas':64}
    return observed,matrix,model
