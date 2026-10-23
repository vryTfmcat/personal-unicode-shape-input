"""Verify decoding by position, all alternate paths and fourth-position targets."""
import copy
import json
from audit_shape_rules import DATA
from render_shape_batch import annotated_paths, render


def main():
    batch=json.loads((DATA/'全形圆族试验-07.json').read_text(encoding='utf-8'))
    rows=annotated_paths(batch)
    assert len(rows)==30 and len({r['char'] for r in rows})==10
    hook=next(r for r in rows if r['char']=='J' and r['code']=='jgjn')
    assert [p['letter'] for p in hook['positions']]==list('jgjn')
    assert hook['positions'][2]['meaning']=='钩尾'
    assert hook['positions'][3]['meaning']=='左下'
    assert hook['fourthTarget']=='钩尾的位置'
    tall=next(r for r in rows if r['char']=='j' and r['code']=='jgvv')
    assert tall['positions'][2]['meaning']=='纵长'
    assert tall['positions'][3]['meaning']=='大'
    assert tall['fourthTarget']=='整体尺寸'
    corner=next(r for r in rows if r['char']=='Γ' and r['code']=='agaj')
    assert corner['fourthTarget']=='整个角折的角点位置'
    assert all(len(r['positions'])==4 and r['basis'] for r in rows)
    text=render(batch)
    assert 'pgvv' in text and 'jgvv' in text
    assert '`v`＝纵长' in text and '`v`＝大' in text
    bad=copy.deepcopy(batch)
    bad['characters'][0]['codes'][0]['code']='zgjn'
    try:annotated_paths(bad)
    except ValueError as e:assert '第1位' in str(e)
    else:raise AssertionError('未知键义不能猜测或静默省略')
    print('四位逐字解码、全部30条多码路径、描述对象与未知键义阻断验证通过。')


if __name__=='__main__':main()
