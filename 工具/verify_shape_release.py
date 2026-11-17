"""Verify the current four-round release; optionally trace reads or serve an isolated copy."""
import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

sys.dont_write_bytecode=True
PROJECT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(PROJECT/'原型/键位编辑器'),str(PROJECT/'工具')]


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--trace-json')
    parser.add_argument('--forbid-path')
    parser.add_argument('--output-dir',required=True)
    parser.add_argument('--serve',action='store_true')
    parser.add_argument('--port',type=int,default=8766)
    args=parser.parse_args();reads=set();violations=[]
    forbidden=Path(args.forbid_path).resolve() if args.forbid_path else None
    def hook(event,values):
        if event!='open' or not isinstance(values[0],(str,bytes,os.PathLike)):return
        path=Path(os.fsdecode(values[0])).resolve()
        if forbidden and path.is_relative_to(forbidden):
            violations.append(str(path));raise PermissionError('恢复验证禁止读取或写入原工作树：'+str(path))
        mode=values[1]
        if path.is_relative_to(PROJECT) and (mode is None or not any(c in mode for c in 'wax+')):
            reads.add(path.relative_to(PROJECT).as_posix())
    sys.addaudithook(hook)
    import shape_overview as so
    import shape_structure_bindings as binding
    if args.serve:
        from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
        class Handler(SimpleHTTPRequestHandler):
            def __init__(self,*a,**kw):super().__init__(*a,directory=str(PROJECT/'原型/键位编辑器'),**kw)
            def _json(self,status,payload):
                content=json.dumps(payload,ensure_ascii=False).encode('utf-8')
                self.send_response(status)
                self.send_header('Content-Type','application/json; charset=utf-8')
                self.send_header('Content-Length',str(len(content)))
                self.send_header('Cache-Control','no-store')
                self.end_headers();self.wfile.write(content)
            def do_GET(self):
                if not so.handle(self):super().do_GET()
        print('isolated overview http://127.0.0.1:'+str(args.port),flush=True)
        ThreadingHTTPServer(('127.0.0.1',args.port),Handler).serve_forever()
        return
    out=Path(args.output_dir);out.mkdir(parents=True,exist_ok=True)
    if binding.data()['version']=='structure-count-bindings-v10':
        from apply_continuous_total_batch_20261027 import build
    elif binding.data()['version']=='structure-count-bindings-v9':
        from apply_d_stroke_k_batch_20261026 import build
    elif binding.data()['version']=='structure-count-bindings-v8':
        from apply_seven_angle_batch_20261025 import build
    elif binding.data()['version'] in ('structure-count-bindings-v6','structure-count-bindings-v7'):
        from apply_k_family_batch_20261025 import build
    elif binding.data()['version']=='structure-count-bindings-v5':
        from apply_p_family_boundary_batch1 import build
    else:
        from apply_shape_scope_batch1 import build
    build()
    if so.joint_bc.policy():
        from apply_seven_bc_20261029 import build as build_bc
        assert build_bc()==so.joint_bc.policy(),'七组合确认未能从冻结输入重现'
    if so.count_bc.policy():
        from apply_six_count_bc_20261029 import build as build_six
        generated,boundaries=build_six()
        assert generated==so.count_bc.policy()
        assert boundaries==so.read(PROJECT/'数据/三模式/规则库/四键实验/人工审议.json')[so.count_bc.BOUNDARY]
    import audit_shape_new_key_rules as audit
    result=audit.run(offline=True,output_dir=out/'audit')
    import unittest
    loader=unittest.TestLoader();suite=unittest.TestSuite()
    for name in ['test_shape_structure_bindings.py','test_shape_pictorial_v17.py','test_shape_overview.py','test_subject_scope_bindings.py','test_bucket_order_query.py','test_first_bucket_primary.py','test_seven_angle_scope.py','test_d_stroke_k_scope.py','test_single_character_shapes.py','test_hole_group_bindings.py','test_external_group_bindings.py','test_continuous_total_v10.py','test_d_subject_hole_shapes.py','test_round_closure_20261028.py','test_joint_bc_seven_20261029.py','test_joint_count_six_20261029.py']:
        suite.addTests(loader.discover(str(PROJECT/'工具'),pattern=name))
    tests=unittest.TextTestRunner(verbosity=1).run(suite)
    if not tests.wasSuccessful():raise RuntimeError('隔离回归检查失败')
    overview=so.get_overview()
    # Include all actual glyph sheets used by the current overview, not just the sample seven.
    previews={r['preview']['url'] for r in overview.rows.values() if r.get('preview')}
    for rel in previews:
        path=PROJECT/'原型/键位编辑器'/rel
        with path.open('rb') as f:assert f.read(8)
    receipt=dict(passed=True,version=binding.data()['version'],tests=tests.testsRun,
        jointBCBindings=so.joint_bc.summary(),jointCountBindings=so.count_bc.summary(),
        shapeBoundaryRefinement=(so.round_refinement.policy() or {}).get('viewRevision'),
        holeGroupBindings=(so.hole_groups.policy() or {}).get('id'),
        holeGroupCountBinding=(so.hole_groups.count_policy() or {}).get('id'),
        externalGroupBindings=(so.external_groups.policy() or {}).get('id'),
        curveCountRestoration=((so.external_groups.curve_restore_policy() or {}).get('id') if so.external_groups.curve_restore_active() else None),
        countSemanticsVersion=binding.data().get('countSemanticsVersion','separate-straight-or-curve'),
        audit=result['summary'],glyphSheets=len(previews),originalTreeAccesses=violations,
        python=sys.version,scope='当前四轮总览、现有规则重生成和历史隔离；不是Android/Rime全项目恢复')
    if args.trace_json:
        Path(args.trace_json).write_text(json.dumps(sorted(reads),ensure_ascii=False,indent=2),encoding='utf-8')
    (out/'恢复验收.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in receipt.items() if k!='audit'},ensure_ascii=False))


if __name__=='__main__':main()
