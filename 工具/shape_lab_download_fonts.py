"""Fetch public Noto reference assets into the project; never install system fonts."""
import hashlib
import json
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from shape_strategy_lab import LAB
from shape_lab_features import font_cmap

FAMILIES=('NotoSerifTangut','NotoSerifKhitanSmallScript','NotoSansNushu',
          'NotoSansSignWriting','NotoSansAnatolianHieroglyphs','NotoSansLinearA',
          'NotoMusic','NotoSansMendeKikakui','NotoNaskhArabic','NotoSansSymbols2')
BASE='https://raw.githubusercontent.com/notofonts/noto-fonts/main/'
EXTRA={'NotoSerifKhitanSmallScript': 'https://notofonts.github.io/khitan-small-script/fonts/NotoSerifKhitanSmallScript/hinted/ttf/NotoSerifKhitanSmallScript-Regular.ttf',
       'EgyptologyExtended': 'https://raw.githubusercontent.com/LumabyteCo/egyptology-extended-font/main/fonts/EgyptologyExtended.ttf'}


def main():
    target=LAB/'字体';target.mkdir(parents=True,exist_ok=True)
    records=[]
    def fetch(family):
        filename=family+'-Regular.ttf' if family!='EgyptologyExtended' else family+'.ttf'
        url=EXTRA.get(family,BASE+'hinted/ttf/'+family+'/'+filename);path=target/filename
        try:
            if not path.exists():
                with urllib.request.urlopen(url,timeout=45) as response:data=response.read(64*1024*1024+1)
                if len(data)>64*1024*1024 or data[:4] not in (b'\x00\x01\x00\x00',b'OTTO',b'ttcf'):raise ValueError('不是可用的字体资产')
                temporary=path.with_suffix('.download');temporary.write_bytes(data)
                font_cmap(temporary);temporary.replace(path)
            coverage,name=font_cmap(path)
            record={'family':name,'file':filename,'url':url,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
                    'coverage':len(coverage),'status':'downloaded','date':'2026-10-12'}
        except Exception as error:record={'family':family,'url':url,'status':'unavailable','error':str(error)}
        print(json.dumps(record,ensure_ascii=False),flush=True);return record
    with ThreadPoolExecutor(max_workers=4) as executor:records=list(executor.map(fetch,FAMILIES+('EgyptologyExtended',)))
    try:
        license_data=urllib.request.urlopen(BASE+'LICENSE',timeout=30).read()
        (target/'LICENSE-Noto.txt').write_bytes(license_data)
    except Exception as error:print('许可原文获取状态：'+str(error),flush=True)
    try:
        license_data=urllib.request.urlopen('https://raw.githubusercontent.com/LumabyteCo/egyptology-extended-font/main/LICENSE.md',timeout=30).read()
        (target/'LICENSE-Egyptology.md').write_bytes(license_data)
        (target/'ATTRIBUTION-Egyptology.txt').write_text('Egyptology Extended Font by Land of Kemet (https://landofkemet.com)\nBased on JSesh glyphs by Serge Rosmorduc & Serge J.P. Thomas\nLicensed under CeCILL v2.1\nSource: https://github.com/LumabyteCo/egyptology-extended-font\n',encoding='utf-8')
    except Exception as error:print('扩展字体许可原文获取状态：'+str(error),flush=True)
    (target/'来源清单.json').write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


if __name__=='__main__':main()
