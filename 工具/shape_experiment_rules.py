"""Versioned proposal dictionaries and object-bound exhaustive rule paths."""
from __future__ import annotations
import math
import copy
import numpy as np
from shape_lab_features import components
from shape_experiment_features import component_mask, observe,crossing_topology,bounds,normalized

FAMILIES={
 'o':('round-outline','圆／椭圆轮廓','○O0◯●◌'), 's':('quadrilateral','四边形轮廓','□■▢◇◆'),
 't':('triangle','三角轮廓','△▲▷'), 'r':('radial','放射／星芒','✳✴✵✷✺☆★'),
 'l':('line','线条','─│╱╲∥'), 'c':('open-arc','开口曲弧','C(⌒◡◜◝◟◞'),
 'u':('u-shape','U形','U∪∩⊂⊃⊔'), 'a':('angle','角折','∠⌜⌟'),
 'j':('hook','钩弯','Jʃɟ'), 'h':('fork','分叉','YΨ'),
 'x':('cross','交叉','+×✕'), 'w':('wave','波形','~∿≈'),
 'd':('dots','点／点群','·∴∵⁙'), 'p':('irregular-loop','不规则回环','∞♧♧'),
 'm':('compound','复合形','♜♞⚒')}

# New keys are proposals only, and never enter the effective legacy codebook.
RULES={
 'd':('component.filled_round','内部实心点／圆面','confirmed','内部紧凑实心构件','⊙','○'),
 'o':('component.hollow_circle','内部空心圆环','confirmed','内部独立环形墨构件','⊚','⊙'),
 'l':('component.line','单一直线','confirmed','可识别直线构件','⊖','○'),
 'n':('component.repeated','重复排列构件','confirmed','至少两个相似、分离的构件','∥','│'),
 'x':('component.cross','内部交叉','confirmed','内部有明确交叉结构','⊕','⊙'),
 'u':('outline.gap','轮廓开口／缺口','confirmed','开口曲线的缺口','C','O'),
 'p':('outline.half','半轮廓','confirmed','半圆弧类轮廓','◡','O'),
 'f':('outline.quarter','四分之一轮廓','confirmed','四分之一圆弧类轮廓','◜','O'),
 'h':('proportion.flat','横扁','confirmed','整体宽高比大于1.25','─','│'),
 'v':('proportion.tall','纵长','confirmed','整体宽高比小于0.8','│','─'),
 's':('proportion.near_round','近圆','confirmed','近圆轮廓且宽高比0.8～1.25','○','□'),
 'e':('topology.no_hole','无闭孔','proposal','主体无稳定闭合空区','C','O'),
 'c':('topology.one_hole','单闭孔','proposal','主体有一个稳定闭合空区','O','∞'),
 'i':('topology.multi_hole','多闭孔','proposal','主体有多个稳定闭合空区','∞','O'),
 'k':('topology.separated','分离部件组','proposal','多个分离墨部件','∴','●'),
 'm':('skeleton.branch','分叉骨架','proposal','同一局部交点有3或4个支臂','Y','O'),
 'r':('skeleton.radial','放射骨架','proposal','同一局部交点有5个及以上支臂','✳','O'),
 't':('component.external_dot','外部点块','proposal','主体外紧凑实心构件','i','⊙'),
 'y':('component.external_stroke','外部线状构件','proposal','主体外明确的线状构件','Q','O')}

TRIAL_KEYS={'a':'内含角折','b':'半填充','g':'四分之一空白扇区','j':'钩尾','q':'四分之一黑色扇区'}


def dictionary():
    return {k:dict(zip(('function','meaning','status','condition','positive','negative'),v),
                   target=v[3],thresholdStatus='experiment',conflicts=[]) for k,v in RULES.items()}


def family_dictionary():
    return {k:{'id':'family.'+v[0],'meaning':v[1],'anchors':list(dict.fromkeys(v[2])),
               'status':'proposal','boundary':'按锁定字体的主体轮廓与骨架匹配；低置信度不强归类',
               'counterexamples':['□' if k=='o' else '○' if k!='o' else '□']} for k,v in FAMILIES.items()}


def semantic_family_dictionary():
    """Semantic identity does not require an accepted keyboard binding."""
    result={v['id']:dict(v,candidateKey=k) for k,v in family_dictionary().items()}
    result['family.double-loop']={'id':'family.double-loop','meaning':'双环','candidateKey':None,
        'anchors':['∞','8'],'counterexamples':['B'], 'status':'boundary-approved-key-unassigned',
        'boundary':'两个可见环体；两孔本身不足以判定同主族。B只作为备选入口候选。'}
    return result


def position(x,y,cx,cy):
    dx,dy=x-cx,y-cy
    if max(abs(dx),abs(dy))<.12:return None
    if min(abs(dx),abs(dy))>=.12:return ('j' if dx<0 else 'k') if dy<0 else ('n' if dx<0 else 'm')
    return ('a' if dx<0 else 'd') if abs(dx)>abs(dy) else ('w' if dy<0 else 's')


def obj(identity,kind,box,body,extent,*,area=None,orientation=None):
    x0,y0,x1,y1=box;bx0,by0,bx1,by1=body
    scale=max(bx1-bx0,by1-by0)
    return {'id':identity,'kind':kind,'bbox':list(map(float,box)),
            'relativeSize':max(x1-x0,y1-y0)/scale,'extentEm':extent,
            'relativePosition':[(x0+x1-bx0-bx1)/(2*scale),(y0+y1-by0-by1)/(2*scale)],
            'area':area,'orientation':orientation}


def properties(o):
    result=[]
    if o['kind'] in ('body','contour-section'):
        size=o['extentEm'];key='z' if size<=.35 else 'x' if size<=.60 else 'c' if size<=.90 else 'v'
        result.append((key,'原始字形最长边／渲染字号'))
    elif o['kind'] not in ('opening','contour-section'):
        size=o['relativeSize'];key='z' if size<=.18 else 'x' if size<=.35 else 'c' if size<=.50 else 'v'
        result.append((key,'该对象最长边／主体最长边'))
    if o['kind']!='body':
        dx,dy=o['relativePosition'];key=position(dx,dy,0,0)
        if key:result.append((key,'该对象中心相对主体中心'))
    angle=o.get('orientation')
    if angle is not None:
        if o.get('orientationMode')=='cross':
            if min(angle,90-angle)<=12:result.append(('e','内部交叉的各臂与轴向对齐'))
            elif abs(angle-45)<=12:result.append(('q','内部交叉相对轴向斜置'))
        elif min(angle,180-angle)<=12:result += [('h','对象长轴横向'),('e','对象长轴正置')]
        elif abs(angle-90)<=12:result += [('i','对象长轴纵向'),('e','对象长轴正置')]
        else:result += [('q','对象长轴斜置'),('r' if angle<90 else 'l','对象长轴倾斜方向')]
    return result


def facts(f,family,templates=None):
    """No property may be borrowed from an object selected by another rule."""
    b=f['bbox'];body=obj('body','body',b,b,f['extent'],orientation=f['angle'] if f['anisotropy']>1.5 else None)
    result=[]
    def add(key,o,why):result.append({'third':key,'function':RULES[key][0],'object':copy.deepcopy(o),'reason':why,'status':RULES[key][2]})
    if f['ratio']>1.25:add('h',body,'整体宽高比>1.25')
    if f['ratio']<.8:add('v',body,'整体宽高比<0.8')
    if family=='o' and .8<=f['ratio']<=1.25:add('s',body,'圆族主体近等宽高')
    if not f['holes']:add('e',body,'主体没有面积≥5像素的闭孔；数值阈值为试验')
    for i,g in enumerate(f['holes']):
        o=obj('hole-'+str(i),'hole',[g['x0'],g['y0'],g['x1'],g['y1']],b,f['extent'],area=g['area'])
        add('c' if len(f['holes'])==1 else 'i',o,'主体闭合空区，第四位描述本空区')
    if len(f['parts'])>1:
        allparts=f['parts'];box=[min(g['x0'] for g in allparts),min(g['y0'] for g in allparts),max(g['x1'] for g in allparts),max(g['y1'] for g in allparts)]
        add('k',obj('part-group','part-group',box,b,f['extent']),'字形有多个分离墨部件；本路径描述整个部件组')
    for i,g in enumerate(f['junctionObjects']):
        o=obj('junction-'+str(i),'junction',[g['x0'],g['y0'],g['x1'],g['y1']],b,f['extent'])
        arms=g['armCount']
        if arms in (3,4):add('m',o,f'同一局部交点有{arms}支；2像素邻域出口计数为试验测量')
        elif arms>=5:add('r',o,f'同一局部交点有{arms}支；2像素邻域出口计数为试验测量')
    # A long narrow whole subject is itself an observable line object.
    if max(f['ratio'],1/f['ratio'])>=4 and f['junctions']==0:add('l',body,'主体为无分叉长直线候选')
    members=[]
    for i,g in enumerate(f['parts']):
        box=[g['x0'],g['y0'],g['x1'],g['y1']]
        if box==b:continue
        w,h=g['x1']-g['x0'],g['y1']-g['y0'];ratio=w/h;density=g['area']/(w*h)
        partmask=component_mask(f['mask'],g)
        owned=bool((partmask&f['body']).any())
        inside=not owned and bool(f['silhouette'][round(g['cy']),round(g['cx'])])
        if g['area']<5:continue
        o=obj('part-'+str(i),'part',box,b,f['extent'],area=g['area'])
        if not owned and .5<=ratio<=2 and density>.55:
            add('d' if inside else 't',o,'主体内实心点块' if inside else '主体外实心点块')
        if max(ratio,1/ratio)>=3:
            o['orientation']=0 if ratio>1 else 90
            add('l' if inside or owned else 'y',o,'分离线状墨部件')
        part_holes=[h for h in components(~np.pad(partmask,1),4) if not h['edge'] and h['area']>=5]
        if inside and part_holes and .5<ratio<2:add('o',o,'主体内独立的有孔墨构件／环，非空白区域')
        members.append((g,o,normalized(partmask,16)))
    for i,(g,o,shape) in enumerate(members):
        similar=[q for q,_,other in members if q is not g and abs(math.log((q['x1']-q['x0'])/(g['x1']-g['x0'])))<.25 and abs(math.log((q['y1']-q['y0'])/(g['y1']-g['y0'])))<.25 and float(((shape-other)**2).mean())<=.045]
        if similar:add('n',o,'至少两个相似分离构件；第四位描述当前成员')
    if family in ('o','s','t'):
        # Inspect inner ink after excluding the enclosing frame. No disconnected-part
        # assumption: a cross touching a ring is still an internal cross.
        x0,y0,x1,y1=b;w,h=x1-x0,y1-y0
        inner=np.zeros_like(f['mask']);ix0,ix1=x0+round(w*.25),x1-round(w*.25);iy0,iy1=y0+round(h*.25),y1-round(h*.25)
        inner[iy0:iy1,ix0:ix1]=f['mask'][iy0:iy1,ix0:ix1]
        inner_parts=[g for g in components(inner,8) if g['area']>=5]
        for number,g in enumerate(inner_parts):
            im=component_mask(inner,g);top=crossing_topology(im);yy,xx=np.nonzero(im);eigen,vectors=np.linalg.eigh(np.cov(np.array([xx,yy])));vector=vectors[:,-1]
            sub={'bbox':bounds(im),'endpoints':top['endpoints'],'junctions':top['junctions'],
                 'anisotropy':float(eigen[-1]/max(.001,eigen[0])),'angle':float(math.degrees(math.atan2(-vector[1],vector[0]))%180)}
            o=obj('inner-ink-'+str(number),'inner-ink',sub['bbox'],b,f['extent'],area=g['area'],
                  orientation=sub['angle'] if sub['anisotropy']>1.5 else None)
            if sub['endpoints']>=4 and sub['junctions']:
                yy,xx=np.nonzero(im);cx=(sub['bbox'][0]+sub['bbox'][2]-1)/2;cy=(sub['bbox'][1]+sub['bbox'][3]-1)/2
                far=np.hypot(xx-cx,yy-cy)>max(sub['bbox'][2]-sub['bbox'][0],sub['bbox'][3]-sub['bbox'][1])*.2
                z=np.exp(4j*np.arctan2(cy-yy[far],xx[far]-cx)).mean() if far.any() else 0
                o['orientation']=float((np.angle(z)/4*180/np.pi)%90) if abs(z)>.4 else None
                o['orientationMode']='cross'
                add('x',o,'排除外框后的内部墨迹具有至少四端点及分叉')
            elif sub['anisotropy']>=9 and sub['junctions']==0:
                add('l',o,'排除外框后的内部单一直线')
    for template in templates or []:
        if family not in ('c','u'):continue
        distance=float(((f['signature']-template['signature'])**2).sum())
        if distance<.055 and abs(math.log(f['ratio']/template['ratio']))<.35:
            o=obj('contour-section','contour-section',b,b,f['extent'])
            o['relativePosition']=template['relativePosition'];o['referenceFrame']='拟合完整圆轮廓'
            add(template['third'],o,'与锁定字体半／四分之一圆弧原型匹配；第四位为该段相对完整轮廓的位置')
    # Gap direction is measured only on an observed open arc/U, never guessed from a generic accessory.
    if family in ('c','u') and not f['holes'] and len(f['parts'])==1:
        x0,y0,x1,y1=b;mask=f['body'][y0:y1,x0:x1];hh,ww=mask.shape
        strips=[mask[:max(1,hh//5)].mean(),mask[-max(1,hh//5):].mean(),mask[:,:max(1,ww//5)].mean(),mask[:,-max(1,ww//5):].mean()]
        order=np.argsort(strips)
        if strips[order[1]]-strips[order[0]]>.08:
            key=('w','s','a','d')[int(order[0])];px,py={'w':(.5,0),'s':(.5,1),'a':(0,.5),'d':(1,.5)}[key]
            xx=x0+px*(x1-x0);yy=y0+py*(y1-y0)
            opening=obj('opening','opening',[xx,yy,xx,yy],b,f['extent'])
            add('u',opening,'开口族边界低墨区；方向为试验观测')
    return result


def paths(bucket,family,observations,palette):
    found={}
    for fact in observations:
        prefix=bucket+family+fact['third']
        attrs=properties(fact['object'])
        entries=[(prefix+k,reason) for k,reason in attrs] or [(prefix,'没有可观测的第四位属性，停在三码')]
        for code,reason in entries:
            if len(code)==4 and code[-1] not in palette:raise ValueError('Undefined fourth key')
            evidence={'rule':fact['function'],'third':fact['third'],'objectId':fact['object']['id'],
                      'thirdObject':fact['object'],'fourthObjectId':fact['object']['id'],
                      'condition':fact['reason'],'attribute':reason,'status':fact['status']}
            item=found.setdefault(code,{'code':code,'evidence':[]})
            if evidence not in item['evidence']:item['evidence'].append(evidence)
    return list(found.values())
