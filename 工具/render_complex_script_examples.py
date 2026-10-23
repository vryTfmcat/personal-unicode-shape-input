"""Render curated Unicode glyph samples from locked reference fonts for human review."""
import gzip,json
from PIL import Image,ImageFont,ImageDraw
from inspect_shape_lab import load_run
from shape_strategy_lab import LAB

GROUPS=[
    ('埃及圣书体',[0x13000,0x13079,0x1313f,0x131cb,0x131f3,0x13250,0x132f9,0x133cf]),
    ('楔形文字',[0x12000,0x1202d,0x1207e,0x12097,0x120f2,0x12157,0x121a0,0x12217]),
    ('手语书写',[0x1d800,0x1d801,0x1d806,0x1d92b,0x1d933,0x1d98d,0x1d9ff,0x1d9f6]),
    ('安纳托利亚象形',[0x14400,0x14413,0x1441a,0x14432,0x1446f,0x144e3,0x14553,0x145c4]),
    ('线形文字 A',[0x10600,0x10601,0x10602,0x10603,0x10604,0x10605,0x10606,0x10607]),
    ('线形文字 B',[0x10000,0x10001,0x10002,0x10005,0x10080,0x10081,0x10082,0x10083])]


def main():
    _,source=load_run()
    with gzip.open(source['featureCache'],'rt',encoding='utf-8') as stream:records={r['cp']:r for r in map(json.loads,stream)}
    folder=LAB/'文字范围预览';folder.mkdir(exist_ok=True)
    image=Image.new('RGB',(1300,1240),'#f2f5f9');draw=ImageDraw.Draw(image)
    cn=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',23);title=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',32)
    note=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',17);en=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',15)
    draw.text((24,16),'复杂文字字形审查 · 每行 8 个代表样本',font=title,fill='#223a51')
    draw.text((24,60),'覆盖不同轮廓与构件；样本不表示常用频率。下方为码位和简写名称，完整名称见对照表。',font=note,fill='#63778a')
    manifest=[];lines=['# 复杂文字典型样本','','用于审查字形；不是常用频率排行，也不代表整个区块的全部复杂度。原分桶未改变。','']
    for i,(group,cps) in enumerate(GROUPS):
        y=100+i*174;draw.rounded_rectangle((18,y,1282,y+162),radius=10,fill='white')
        draw.text((30,y+30),group,font=cn,fill='#223a51');samples=[]
        lines+=['## '+group,'','| 字符 | 码位 | Unicode 名称 | 参考字体 |','|---|---|---|---|']
        for j,cp in enumerate(cps):
            r=records[cp];f=r['feature'];assert f['observed'],r['name']
            font=ImageFont.truetype(f['fontPath'],64,index=f.get('fontIndex',0));box=font.getbbox(r['char'])
            scale=min(1.,118/max(1,box[2]-box[0]),90/max(1,box[3]-box[1]))
            if scale<1:font=ImageFont.truetype(f['fontPath'],max(12,int(64*scale)),index=f.get('fontIndex',0));box=font.getbbox(r['char'])
            cx=266+j*130
            draw.text((cx-(box[2]-box[0])/2-box[0],y+59-(box[3]-box[1])/2-box[1]),r['char'],font=font,fill='#182e43')
            draw.text((cx-38,y+112),f'U+{cp:04X}',font=en,fill='#657b90')
            short=r['name']
            for prefix in ('EGYPTIAN HIEROGLYPH ','CUNEIFORM SIGN ','SIGNWRITING ','ANATOLIAN HIEROGLYPH ','LINEAR A SIGN ','LINEAR B SYLLABLE ','LINEAR B IDEOGRAM '):
                if short.startswith(prefix):short=short[len(prefix):];break
            original=short
            while draw.textlength(short,font=en)>118:short=short[:-1]
            if short!=original:
                short=short[:-1]+'…'
            draw.text((cx-draw.textlength(short,font=en)/2,y+137),short,font=en,fill='#657b90')
            samples.append({'char':r['char'],'cp':cp,'name':r['name'],'font':f['font'],'fontPath':f['fontPath']})
            lines.append(f"| {r['char']} | U+{cp:04X} | {r['name']} | {f['font']} |")
        lines.append('');manifest.append({'group':group,'samples':samples})
    draw.text((24,1164),'埃及字形：Egyptology Extended / Land of Kemet；基于 JSesh（Rosmorduc、Thomas），CeCILL v2.1。',font=note,fill='#63778a')
    draw.text((24,1196),'其他字形使用项目锁定的系统字体与 Noto 字体；Unicode 名称取自项目 Unicode 17 资料。',font=note,fill='#63778a')
    lines+=['埃及字形字体归属：Egyptology Extended by Land of Kemet (https://landofkemet.com)，基于 Serge Rosmorduc 与 Serge J.P. Thomas 的 JSesh 字形，CeCILL v2.1。实际各样本参考字体见表。','']
    image.save(folder/'复杂文字典型样本.png')
    (folder/'复杂文字典型样本.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    (folder/'复杂文字典型样本.md').write_text('\n'.join(lines),encoding='utf-8')
    print(folder/'复杂文字典型样本.png')


if __name__=='__main__':main()
