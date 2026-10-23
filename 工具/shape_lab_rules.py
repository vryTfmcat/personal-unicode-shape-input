"""Representative prefix policies. Every policy shares the same observed fourth views."""
from __future__ import annotations
import math
import numpy as np

FAMILY = {'a':'角折','c':'曲弧','d':'小点块','h':'分叉','j':'钩弯估计','l':'线条',
          'm':'复合轮廓','o':'圆／椭圆','p':'带孔回环','r':'放射','s':'四边框／块','t':'三角',
          'u':'直臂U形','w':'波形','x':'交叉','q':'未观测'}
STATE = {'e':'疏墨描边','f':'高填充','g':'单体无闭孔','c':'一个闭孔','p':'多个闭孔',
         'i':'主体内有可分辨区域／构件','m':'多个墨构件','x':'主干交叠估计','q':'未观测'}
DETAIL = {'e':'整体取形','s':'近等宽高','v':'纵长','h':'横展','u':'开口估计',
          'a':'角点','d':'点状构件','o':'闭合空区／环状构件','j':'末端钩弯估计',
          'l':'线状构件','n':'多个墨构件','x':'交叠骨架','q':'未观测'}
TOPOLOGY = {'g':'单体无闭孔','f':'密实无闭孔','o':'一个闭孔','p':'两个闭孔',
            'm':'三个以上闭孔','d':'多分离墨部件','q':'未观测'}
PROPORTION = {'a':'极纵长','v':'纵长','s':'近等宽高','h':'横展','w':'极横展','q':'未观测'}
STROKE = {'l':'直干占主导','a':'直角骨架','x':'交叠直干','c':'弯曲／无长直干',
          'm':'混合笔迹','q':'未观测'}
FIXED_REQUIRED = {'w':'position.up','s':'position.down','a':'position.left','d':'position.right',
                  'z':'size.tiny','x':'size.small','c':'size.medium','v':'size.large',
                  'j':'position.up_left','k':'position.up_right','n':'position.down_left','m':'position.down_right'}


def size_key(extent):
    return 'z' if extent<=.35 else 'x' if extent<=.60 else 'c' if extent<=.90 else 'v'


def component_size_key(relative):
    # A fixed experiment convention, not tuned per candidate strategy.
    return 'z' if relative<=.18 else 'x' if relative<=.35 else 'c' if relative<=.50 else 'v'


def position_key(x,y,center_x=.5,center_y=.5):
    dx,dy=x-center_x,y-center_y
    if max(abs(dx),abs(dy))<.12:return None # c means medium, never invent a centre key.
    if abs(dx)>=.12 and abs(dy)>=.12:
        return ('j' if dx<0 else 'k') if dy<0 else ('n' if dx<0 else 'm')
    return ('a' if dx<0 else 'd') if abs(dx)>abs(dy) else ('w' if dy<0 else 's')


def family_raw(f):
    r,d=f['ratio'],f['density']
    if (r<.18 or r>5) and not f['holes']:return 'l'
    if f['components']>1:
        return 'd' if f['extentEm']<.35 else 'm'
    pixels=np.array(f['bitmap']).reshape(8,8)
    occupied=pixels>.10
    def span(a):
        return np.array([(np.flatnonzero(row)[-1]-np.flatnonzero(row)[0]+1)/8 if row.any() else 0 for row in a])
    profile=span(occupied);columns=span(occupied.T);t=(np.arange(8)+.5)/8
    triangle_error=min(np.mean(abs(profile-t)),np.mean(abs(profile-(1-t))),
                       np.mean(abs(columns-t)),np.mean(abs(columns-(1-t))))
    diamond_error=min(np.mean(abs(profile-(1-abs(2*t-1)))),np.mean(abs(columns-(1-abs(2*t-1)))))
    ellipse_error=min(np.mean(abs(profile-np.sqrt(1-(2*t-1)**2))),np.mean(abs(columns-np.sqrt(1-(2*t-1)**2))))
    if (f['holes'] or d>.55) and max(f['symV'],f['symH'])>.65:
        if triangle_error<.15 and triangle_error+.035<ellipse_error:return 't'
        if diamond_error<.13 and diamond_error+.025<ellipse_error:return 's'
    if f['holes']>=2:return 'p' if f['holeRatio']>.1 else 'm'
    if f['holes']==1:
        if f['cornerInk']>.22 and f['hRun']>.65 and f['vRun']>.65:return 's'
        return 'o' if f['holeRatio']>.15 and max(f['symH'],f['symV'])>.7 else 'p'
    if f['extentEm']<.28 and .5<r<2 and d>.4:return 'd'
    if d>.65:return 's' if d>.86 else 'o'
    if f['hRun']>.7 and f['vRun']>.7 and f['lineCoverage']>.65:
        x,y=f['vPos'],f['hPos']
        if (x<.25 or x>.75) and (y<.25 or y>.75):return 'a'
        if .25<x<.75 and .25<y<.75:return 'x'
    if .35<d<.60 and f['symV']>.8 and f['hRun']>.8 and (f['hPos']<.2 or f['hPos']>.8):return 't'
    if f['symH']>.8 and f['symV']<.6 and r>.35 and d<.55 and abs(f['border'][2]-f['border'][3])>.15:return 'c'
    if f['vRun']>.6 and f['symV']>.76 and f['symH']<.8 and min(f['border'][:2])+.12<min(f['border'][2:]):return 'u'
    if f['vRun']>.6 and r<.9 and f['symV']<.76 and d<.5:return 'j'
    if f['symV']>.7 and pixels[5:,:3].mean()<.1 and pixels[5:,5:].mean()<.1 and pixels[5:,3:5].mean()>.25 and pixels[:3,:3].mean()>.10 and pixels[:3,5:].mean()>.10:
        return 'h'
    endpoints=[pixels[:2,3:5].mean(),pixels[-2:,3:5].mean(),pixels[3:5,:2].mean(),pixels[3:5,-2:].mean(),
               pixels[:2,:2].mean(),pixels[:2,-2:].mean(),pixels[-2:,:2].mean(),pixels[-2:,-2:].mean()]
    if min(f['symV'],f['symH'])>.65 and pixels[3:5,3:5].mean()>.3 and sum(v>.10 for v in endpoints)>=6:return 'r'
    if r>1.5 and f['hRun']<.6:
        masses=pixels.sum(axis=0);centres=(pixels*np.arange(8)[:,None]).sum(axis=0)/np.maximum(masses,.001)
        direction=np.sign(np.diff(centres));direction=direction[np.abs(np.diff(centres))>.3]
        if len(direction)>2 and np.count_nonzero(direction[1:]!=direction[:-1])>=2:return 'w'
    if abs(f['diagonal'])>.85:return 'l'
    if d<.5 and f['hRun']<.7 and f['vRun']<.7:return 'c'
    return 'm'


def family(f):
    if '_family_rules_v2' not in f:f['_family_rules_v2']=family_raw(f)
    return f['_family_rules_v2']


def state(f):
    if f['components']>1:return 'm'
    if f['holes']>1:return 'p'
    if f['holes']==1:return 'c'
    return 'f' if f['density']>.65 else 'g'


def topology(f):
    if f['holes']>=3:return 'm'
    if f['holes']==2:return 'p'
    if f['holes']==1:return 'o'
    if f['components']>1:return 'd'
    return 'f' if f['density']>.65 else 'g'


def proportion(r):
    return 'a' if r<.35 else 'v' if r<.8 else 's' if r<=1.25 else 'h' if r<=3 else 'w'


def focus(f):
    return 'v' if f['ratio']<.8 else 'h' if f['ratio']>1.25 else 's'


def vector(f):
    if not f['observed']:return np.zeros(74,dtype=np.float32)
    stats=[math.log(max(.05,min(20,f['ratio']))),f['density'],min(4,f['holes'])/4,
           min(6,f['components'])/6,f['symH'],f['symV'],f['hRun'],f['vRun'],
           min(2,f['extentEm'])/2,f['cornerInk']]
    return np.array(stats+f['bitmap'],dtype=np.float32)


def views(f, palette):
    if not f['observed']:
        return [{'kind':'unobserved','suffix':None,'detail':'q','relation':'q','confidence':0.,'target':'无法观测'}]
    fam=family(f)
    result=[{'kind':'body-size','suffix':size_key(f['extentEm']),'detail':focus(f),
             'relation':state(f),'confidence':.9,'target':'整体尺寸'}]
    w,h=f['maskSize'];major=f['major']
    for g in f['extras']:
        gw,gh=g['x1']-g['x0'],g['y1']-g['y0'];relative=max(gw,gh)/max(w,h)
        inside=major['x0']<=g['cx']<major['x1'] and major['y0']<=g['cy']<major['y1']
        detail='d' if g['area']/(gw*gh)>.4 and .5<gw/gh<2 else 'l' if max(gw/gh,gh/gw)>3 else 'o'
        common={'detail':detail,'relation':'i' if inside else 'm','confidence':.65,
                'object':[g['x0']/w,g['y0']/h,g['x1']/w,g['y1']/h]}
        result.append(dict(common,kind='component-size',suffix=component_size_key(relative),target='分离墨部件相对主体的尺寸'))
        p=position_key(g['cx']/max(1,w-1),g['cy']/max(1,h-1),major['cx']/max(1,w-1),major['cy']/max(1,h-1))
        if p:result.append(dict(common,kind='component-position',suffix=p,target='分离墨部件相对主体的位置'))
    for g in f['holeObjects']:
        p=position_key(g['cx']/max(1,w-1),g['cy']/max(1,h-1))
        if p:result.append({'kind':'hole-position','suffix':p,'detail':'o','relation':'i','confidence':.65,'target':'封闭空区位置'})
    if f['vRun']>.65 and f['ratio']<.9 and not f['holes'] and (fam=='j' or f['components']>1):
        pixels=np.array(f['bitmap']).reshape(8,8).copy()
        major_y0=int(8*major['y0']/h);major_y1=max(major_y0+1,int(math.ceil(8*major['y1']/h)))
        pixels[:major_y0]=pixels[major_y1:]=0
        middle_start=major_y0+(major_y1-major_y0)//3;middle_end=max(middle_start+1,major_y1-(major_y1-major_y0)//3)
        stem_columns=pixels[middle_start:middle_end].mean(axis=0)>.25
        pixels[:,stem_columns]=0
        for lo,hi in ((major_y0,min(major_y1,major_y0+3)),(max(major_y0,major_y1-3),major_y1)):
            area=pixels[lo:hi];mass=area.sum()
            if mass<.7:continue
            y,x=np.indices(area.shape);cx=float((area*x).sum()/mass)/7;cy=float((area*(y+lo)).sum()/mass)/7
            p=position_key(cx,cy)
            if p in ('j','k','n','m'):
                result.append({'kind':'hook-estimate','suffix':p,'detail':'j','relation':state(f),
                               'confidence':.5,'target':'主干末端侧向弯笔位置估计，须人工核对'})
    if fam in ('c','u') and not f['holes'] and f['components']==1:
        border=np.array(f['border']);order=np.argsort(border)
        if border[order[1]]-border[order[0]]>.015:
            result.append({'kind':'opening','suffix':('w','s','a','d')[int(order[0])],
                           'detail':'u','relation':'g','confidence':.55,'target':'低墨边界估计的开口方向，待核对'})
    if fam=='a' and f['hRun']>.7 and f['vRun']>.7:
        p=position_key(f['vPos'],f['hPos'])
        if p is not None and p in 'jknm':
            result.append({'kind':'corner','suffix':p,'detail':'a','relation':'g','confidence':.8,'target':'长横／竖干交点的角位'})
    if fam=='x' and 'e' in palette:
        result.append({'kind':'cross','suffix':'e','detail':'x','relation':'x','confidence':.65,'target':'轴向交叠骨架'})
    for v in result:
        if v['suffix'] is not None and v['suffix'] not in palette:raise ValueError('实验不得新增或改写第四位键义')
    return result


def strategies():
    result=[]
    names={'shape':'轮廓优先','topology':'拓扑优先','proportion':'比例优先',
           'decompose':'主干与附件','bins':'可量化特征分档','cluster':'视觉聚类'}
    for algorithm,name in names.items():
        for level in ('coarse','standard','fine'):
            if algorithm=='bins':k={'coarse':3,'standard':5,'fine':7}[level]
            elif algorithm=='cluster':k={'coarse':12,'standard':18,'fine':24}[level]
            else:k=0
            result.append({'id':algorithm+'-'+level,'name':name+'／'+level,'algorithm':algorithm,
                           'level':level,'bins':k if algorithm=='bins' else 0,'clusters':k if algorithm=='cluster' else 0,
                           'semantic':{'shape':1.,'topology':.9,'proportion':.9,'decompose':1.,'bins':.45,'cluster':.15}[algorithm],
                           'mnemonic':{'shape':.9,'topology':.8,'proportion':.75,'decompose':.85,'bins':.25,'cluster':.1}[algorithm],
                           'branches':{'shape':15,'topology':9,'proportion':6,'decompose':18,'bins':3*k,'cluster':k}[algorithm]})
            if algorithm in ('topology','proportion') and level=='fine':
                result[-1]['mnemonic']=.55;result[-1]['branches']=16 if algorithm=='topology' else 9
    return result


def definitions(spec):
    algorithm=spec['algorithm'];k=spec['bins'] or spec['clusters']
    bucket={chr(97+i):f'第{i+1}数值区间' for i in range(k)}
    cluster={chr(97+i):f'视觉原型簇{i+1}（须看原型，不是语义形族）' for i in range(k)}
    if algorithm=='shape':maps=[dict(FAMILY),dict(STATE),dict(DETAIL)]
    elif algorithm=='topology':maps=[dict(TOPOLOGY),dict(FAMILY),dict(DETAIL)]
    elif algorithm=='proportion':maps=[dict(PROPORTION),dict(TOPOLOGY),dict(DETAIL)]
    elif algorithm=='decompose':maps=[dict(FAMILY),dict(STATE),dict(DETAIL)]
    elif algorithm=='bins':maps=[dict(bucket),dict(bucket),dict(TOPOLOGY)]
    else:maps=[dict(cluster),dict(TOPOLOGY),dict(DETAIL)]
    if spec['level']=='coarse' and algorithm in ('shape','decompose'):
        maps[0]={'a':'角形（角折／四边／三角）','c':'曲线（弧／钩／U／波形）',
                 'o':'围环（圆／回环）','x':'线群（交叉／分叉／放射）',
                 'd':'小点块','l':'线条','m':'复合轮廓','q':'未观测'}
    if algorithm=='bins':
        maps[0]={chr(97+i):f'宽高比对数的第{i+1}/{k}档（范围0.167～6）' for i in range(k)}
        maps[1]={chr(97+i):f'墨迹密度[{i/k:.3f}, {(i+1)/k:.3f}]' for i in range(k)}
    if algorithm=='topology' and spec['level']=='coarse':
        maps[0]={'g':'稀疏单体无孔','f':'密实无孔','o':'有闭孔','d':'多分离部件','q':'未观测'}
    if algorithm=='topology' and spec['level']=='fine':
        maps[0]={chr(97+holes*4+parts):f'{holes if holes<3 else "3+"}闭孔／{parts+1 if parts<3 else "4+"}墨部件'
                 for holes in range(4) for parts in range(4)}
    if algorithm=='proportion' and spec['level']=='coarse':
        maps[0]={'v':'纵长','s':'近等宽高','h':'横展','q':'未观测'}
    if algorithm=='proportion' and spec['level']=='fine':
        limits=[0,.25,.45,.65,.85,1.18,1.55,2.2,4,float('inf')]
        maps[0]={chr(97+i):f'宽高比[{limits[i]}, {limits[i+1]})' for i in range(9)}
    if spec['level']=='fine' and algorithm in ('shape','decompose'):
        maps[0].update(e='纵长圆类轮廓',b='密集复合',k='稀疏复合',y='多分离部件',z='多孔复合')
        maps[2]['e']='主体直接取形（选择对象，不冒充新形状特点）'
    return maps


def first_family(f,spec):
    base=family(f)
    if spec['level']=='coarse':
        return {'a':'a','s':'a','t':'a','u':'c','j':'c','w':'c','p':'o','h':'x','r':'x'}.get(base,base)
    if spec['level']=='fine':
        if base=='o' and f['ratio']<.8:return 'e'
        if base=='m':
            if f['components']>2:return 'y'
            if f['holes']>2:return 'z'
            return 'b' if f['density']>.4 else 'k'
    return base


def encode(f,view,spec,cluster=None):
    if not f['observed']:return None
    algorithm=spec['algorithm'];detail=view['detail']
    if spec['level']=='coarse' and view['kind']=='body-size':detail='e'
    if spec['level']=='fine' and algorithm in ('shape','decompose'):
        anchor=first_family(f,spec)
        if algorithm=='decompose' and f['vRun']>.65 and f['ratio']<1:anchor='l'
        if (view['kind']=='body-size' and anchor=='e' and detail=='v') or \
           (view['kind']=='opening' and anchor in ('c','u')) or \
           (view['kind']=='corner' and anchor=='a') or \
           (view['kind']=='cross' and anchor=='x'):
            detail='e'
    if algorithm=='shape':prefix=first_family(f,spec)+view['relation']+detail
    elif algorithm=='topology':
        top=topology(f)
        if spec['level']=='coarse' and top in ('p','m'):top='o'
        elif spec['level']=='fine':top=chr(97+min(3,f['holes'])*4+min(3,max(0,f['components']-1)))
        prefix=top+family(f)+detail
    elif algorithm=='proportion':
        p=proportion(f['ratio'])
        if spec['level']=='coarse':p='v' if f['ratio']<.8 else 'h' if f['ratio']>1.25 else 's'
        elif spec['level']=='fine':p=chr(97+int(np.searchsorted([.25,.45,.65,.85,1.18,1.55,2.2,4],f['ratio'],side='right')))
        prefix=p+topology(f)+detail
    elif algorithm=='decompose':
        anchor=first_family(f,spec)
        if f['vRun']>.65 and f['ratio']<1:anchor='l'
        prefix=anchor+view['relation']+detail
    elif algorithm=='bins':
        k=spec['bins']
        log_ratio=(math.log(max(.15,min(6,f['ratio'])))+math.log(6))/(2*math.log(6))
        a=chr(97+min(k-1,max(0,int(log_ratio*k))))
        b=chr(97+min(k-1,max(0,int(f['density']*k))))
        prefix=a+b+topology(f)
    else:
        prefix=chr(97+int(cluster))+topology(f)+detail
    return prefix+view['suffix']
