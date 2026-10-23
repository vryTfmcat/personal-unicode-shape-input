"""Publication preserves unrelated settings and restores failed transactions."""
import tempfile
from pathlib import Path
from unittest.mock import patch
import yaml
import publish_mode_rime as release


def main():
    raw='patch:\n  menu/page_size: 7\n  schema_list/+:\n    - schema: existing\n'
    result=release.merged_default(raw)
    assert release.merged_default(result)==result
    data=yaml.safe_load(result)
    assert data['patch']['menu/page_size']==7
    assert data['patch']['schema_list/+']==[{'schema':'existing'}]+[{'schema':release.schema_id(mask)} for mask in (1,2,4,7,3,5,6,0)]
    def builder(book,output):
        output.mkdir(parents=True)
        (output/'unicode_block.dict.yaml').write_text('new dictionary',encoding='utf-8')
        (output/'new.schema.yaml').write_text('new schema',encoding='utf-8')
        return {'counts':{'block':1}}
    for fail in (False,True):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);target=root/'user';target.mkdir()
            (target/'default.custom.yaml').write_text(raw,encoding='utf-8')
            (target/'unicode_block.dict.yaml').write_text('old dictionary',encoding='utf-8')
            def verifier(output,book,weasel,deployed=None):
                if deployed:
                    assert (deployed/'unicode_block.dict.yaml').read_text('utf-8')=='new dictionary'
                    if fail:raise RuntimeError('intentional verification failure')
                return {'verified':True}
            with patch.object(release,'PROJECT',root),patch.object(release,'validate_codebooks',lambda b: b),patch.object(release,'build',builder),patch.object(release,'verify',verifier),patch.object(release,'deploy') as deployer:
                try:result=release.publish({'fixture':True},target,root/'weasel')
                except RuntimeError:
                    assert fail
                    assert (target/'default.custom.yaml').read_text('utf-8')==raw
                    assert (target/'unicode_block.dict.yaml').read_text('utf-8')=='old dictionary'
                    assert not (target/'new.schema.yaml').exists()
                    assert deployer.call_count==2
                else:
                    assert not fail
                    assert Path(result['backup']).is_dir()
                    assert (target/'new.schema.yaml').exists()
                    assert deployer.call_count==1
            assert not release.PUBLISH_LOCK.locked()
    print('发布配置保留、独立构建、备份、失败回滚验证通过。')


if __name__=='__main__':main()
