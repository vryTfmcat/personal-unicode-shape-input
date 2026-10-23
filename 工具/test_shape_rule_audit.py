"""Catch the actual historical ambiguity, duplicates and incomplete new batches."""
import copy
import json
from audit_shape_rules import DATA, audit, project_layout


def main():
    batches = [(p.name, json.loads(p.read_text(encoding='utf-8')))
               for p in sorted(DATA.glob('全形*试验-*.json'))]
    current = audit(batches)
    assert current['ok'], current['errors']
    fourth_current = next(b for name, b in batches if name == '全形圆族试验-04.json')
    for key, function in {'j':'position.up_left','k':'position.up_right',
                          'n':'position.down_left','m':'position.down_right',
                          'a':'position.left','d':'position.right',
                          'w':'position.up','s':'position.down'}.items():
        assert fourth_current['functionIds']['fourth'][key] == function
    assert any(item['key'] == 's' for item in current['crossPositionReuse'])
    assert current['manualReview'], '泛义与细义不能因为 ID 不同而省略审查'

    historical = copy.deepcopy(batches)
    old_size=historical[0][1]
    old_size['rules']['fourth']['m']=old_size['rules']['fourth'].pop('c')
    old_size['functionIds']['fourth']['m']=old_size['functionIds']['fourth'].pop('c')
    for row in old_size['characters']:
        if row['proposedCode'].endswith('c'):row['proposedCode']=row['proposedCode'][:3]+'m'
    fourth = next(b for name, b in historical if name == '全形圆族试验-04.json')
    corner_key = next(k for k, f in fourth['functionIds']['fourth'].items() if f == 'position.down_right')
    fourth['fourth']['m'] = fourth['fourth'].pop(corner_key)
    fourth['functionIds']['fourth']['m'] = fourth['functionIds']['fourth'].pop(corner_key)
    for row in fourth['characters']:
        if row['char'] == '◶': row['proposedCode'] = 'oiam'
    issues = audit(historical)['errors']
    assert any(i['type'] == 'key_conflict' and i.get('position') == 4 and i.get('key') == 'm' for i in issues)

    duplicate = copy.deepcopy(batches)
    first = duplicate[0][1]
    first['rules']['third']['e'] = '与近圆同义的新名称'
    first['functionIds']['third']['e'] = 'proportion.near_round'
    assert any(i['type'] == 'function_duplicate' for i in audit(duplicate)['errors'])

    missing = copy.deepcopy(batches)
    del missing[0][1]['functionIds']['third']['s']
    assert any(i['type'] == 'missing_function_ids' for i in audit(missing)['errors'])

    bad_code = copy.deepcopy(batches)
    bad_code[0][1]['characters'][0]['proposedCode'] = 'oesy'
    assert any(i['type'] == 'undeclared_code_key' for i in audit(bad_code)['errors'])
    layout=json.loads((DATA/'全形第四位-当前布局.json').read_text(encoding='utf-8'))
    assert layout['status']=='approved'
    unchanged=copy.deepcopy(batches)
    projected,changes=project_layout(batches,layout)
    assert batches==unchanged, '试验布局不能覆盖已记录批次'
    assert audit(projected)['ok']
    assert not changes, '覆盖后的当前布局再次投影应保持相同编码'
    assert all(not row['confirmed'] for row in audit(projected)['bindings'])
    by_char={r['char']:r.get('proposedCode',r.get('code')) for _,b in projected
             for r in b['characters'] if r.get('primaryReference',True)}
    assert by_char['○']=='oesc' and by_char['◯']=='oesv'
    assert by_char['◐']=='opba' and by_char['◶']=='oiam'
    assert by_char['⦶']=='oili' and by_char['⊕']=='oixe'
    incomplete=copy.deepcopy(layout)
    del incomplete['fourth']['e']
    prior=copy.deepcopy(batches)
    cross=next(b for name,b in prior if name=='全形圆族试验-02.json')
    cross['fourth']['a']=cross['fourth'].pop('e')
    cross['functionIds']['fourth']['a']=cross['functionIds']['fourth'].pop('e')
    for row in cross['characters']:
        if row['proposedCode'].endswith('e'):row['proposedCode']=row['proposedCode'][:3]+'a'
    conflicted,_=project_layout(prior,incomplete)
    assert any(i['type']=='key_conflict' and i.get('key')=='a' for i in audit(conflicted)['errors']), '遗漏正置迁移必须报告跨批次 a 冲突'
    sixth=next(b for name,b in batches if name=='全形圆族试验-06.json')
    left=next(r for r in sixth['characters'] if r['char']=='(')
    assert {e['code'] for e in left['codes']}=={'cgva','cgpa','cgud','cgvc'}
    assert sum(len(r['codes']) for r in sixth['characters'])==30
    aliases=copy.deepcopy(batches)
    six=next(b for name,b in aliases if name=='全形圆族试验-06.json')
    six['characters'][0]['codes'][-1]['code']='cguy'
    assert any(e['type']=='undeclared_code_key' for e in audit(aliases)['errors']), '必须检查非展示码'
    repeated=copy.deepcopy(batches)
    six=next(b for name,b in repeated if name=='全形圆族试验-06.json')
    six['characters'][0]['codes'].append(copy.deepcopy(six['characters'][0]['codes'][0]))
    assert any(e['type']=='duplicate_alias' for e in audit(repeated)['errors'])
    no_basis=copy.deepcopy(batches)
    six=next(b for name,b in no_basis if name=='全形圆族试验-06.json')
    six['characters'][0]['codes'][-1]['basis']=''
    assert any(e['type']=='alias_without_basis' for e in audit(no_basis)['errors'])
    no_target=copy.deepcopy(batches)
    six=next(b for name,b in no_target if name=='全形圆族试验-06.json')
    del six['characters'][0]['codes'][-1]['fourthTarget']
    assert any(e['type']=='alias_without_target' for e in audit(no_target)['errors'])
    wrong_target=copy.deepcopy(batches)
    six=next(b for name,b in wrong_target if name=='全形圆族试验-06.json')
    six['characters'][0]['codes'][-1]['fourthTarget']='opening-direction'
    assert any(e['type']=='alias_target_mismatch' for e in audit(wrong_target)['errors'])
    migration=copy.deepcopy(layout)
    migration['fourth']['y']=migration['fourth'].pop('d')
    moved,_=project_layout(batches,migration)
    assert audit(moved)['ok']
    six=next(b for name,b in moved if name=='全形圆族试验-06.json')
    left=next(r for r in six['characters'] if r['char']=='(')
    assert {e['code'] for e in left['codes']}=={'cgva','cgpa','cguy','cgvc'}, '迁移必须包括备选码'
    print('真实 m 冲突、同功能异字母、缺失键义、非法候选码、跨位复用和相近功能提醒验证通过。')


if __name__ == '__main__': main()
