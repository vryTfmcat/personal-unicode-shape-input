"""Behavioral coverage of independent assignments, migration and persistence."""
import copy
import importlib.util
import itertools
import json
import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

import mode_codebooks as books
from test_association_server import request
from build_mode_rime import build


def main():
    base=books.base_data();book=books.seed_codebooks()
    assert base["statistics"]=={"characters":159345,"nonHan":56347,"prefixes":360,"blocks":323}
    codes=[c["blockCode"]["code"] for c in base["characters"] if c["blockCode"]]
    assert len(codes)==len(set(codes))==56347
    assert all(not c["blockCode"] for c in base["characters"] if c["han"])
    assert all(c["shape"]["detail"] is None for c in base["characters"] if c["shape"])
    assert base["chineseSource"]["uro"]==8114 and base["chineseSource"]["extended"]==297
    assert all(not a["enabled"] for aliases in book["personal"].values() for a in aliases)
    original=books.effective_data(base,book)
    by={c["char"]:c for c in original["characters"]}
    c=by["○"];old_block=copy.deepcopy(c["blockCode"]);old_shape=copy.deepcopy(c["shape"])
    book["personal"][c["id"]].append({"code":"zzzz","enabled":True,"note":"test"})
    after=books.effective_data(base,book)
    actual=next(x for x in after["characters"] if x["id"]==c["id"])
    assert actual["blockCode"]==old_block and actual["shape"]==old_shape
    book["shapeOverrides"][c["id"]]={"coarse":"oi","detail":None,"status":"reviewed","ruleVersion":"test"}
    actual=next(x for x in books.effective_data(base,book)["characters"] if x["id"]==c["id"])
    assert actual["blockCode"]==old_block and actual["personal"][-1]["code"]=="zzzz"
    book["blockOverrides"][c["id"]]={**old_block,"status":"reviewed"}
    books.validate_codebooks(book,base)
    for mutation in (lambda b:b["shapeOverrides"][c["id"]].update(detail="aa"),
                     lambda b:b["blockOverrides"][c["id"]].update(code="zzzz"),
                     lambda b:b["metadata"].update({c["id"]:{"audio":"bad"}})):
        bad=copy.deepcopy(book);mutation(bad)
        try:books.validate_codebooks(bad,base)
        except ValueError:pass
        else:raise AssertionError("invalid state accepted")
    index=books.candidate_index(books.effective_data(base,book))
    for count in (1,2,3):
        for combo in itertools.combinations(("block","shape","personal"),count):
            for chinese,extended in ((False,False),(False,True),(True,False),(True,True)):
                assert bool(books.query_candidates(index,"zzzz",list(combo),chinese,extended))==("personal" in combo)
                assert any("chinese" in r["sources"] for r in books.query_candidates(index,"aakk",list(combo),chinese,extended))==chinese
    server_path=books.PROJECT/"原型"/"键位编辑器"/"serve.py"
    spec=importlib.util.spec_from_file_location("modes_server_test",server_path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    with tempfile.TemporaryDirectory() as temp:
        root=Path(temp);path=root/"codebooks.json";books.atomic_json(path,book)
        store=module.CodebookStore(path)
        graph_path=root/"graph.json";graph_path.write_bytes((books.PROJECT/"数据"/"联想图谱"/"association-graph.json").read_bytes())
        graph_store=module.GraphStore(graph_path,root/"graph-backups")
        server=ThreadingHTTPServer(("127.0.0.1",0),module.handler_factory(graph_store,codebook_store=store,publisher=lambda b:{"verified":True}))
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start();url=f"http://127.0.0.1:{server.server_port}/api/codebooks"
        try:
            status,payload=request(url);assert status==200
            changed=copy.deepcopy(payload["codebooks"]);changed["metadata"][c["id"]]={"note":"持久化测试","ipa":"oː","language":"test"}
            body={"baseRevision":payload["revision"],"codebooks":changed}
            with ThreadPoolExecutor(max_workers=2) as pool:
                results=list(pool.map(lambda _:request(url,"PUT",body),range(2)))
            assert sorted(r[0] for r in results)==[200,409]
            assert store.read()[0]["metadata"][c["id"]]["ipa"]=="oː"
            status,new=request(url);assert new["revision"]!=payload["revision"]
            assert request(url+"/publish","POST",{"baseRevision":payload["revision"]})[0]==409
            assert request(url+"/publish","POST",{"baseRevision":new["revision"]})[0]==200
            assert request(url+"/snapshot","POST",{})[0]==200
            assert list((root/"备份").glob("codebooks.*.json"))
            with patch.object(books,"BASE_PATH",root/"mode-data.json"),patch.object(books,"BOOK_PATH",path),patch.object(books,"DATA",root):books.write()
            assert books.effective_data(base,json.loads(path.read_text(encoding="utf-8")))["characters"]==books.effective_data(base,store.read()[0])["characters"]
            generated=build(store.read()[0],root/"rime");assert generated["counts"]["block"]==56347
        finally:server.shutdown();server.server_close();thread.join(timeout=5)
    print("三模式独立编码、全量唯一、中文覆盖、并发保存、重建保留验证通过。")

if __name__=="__main__":main()
