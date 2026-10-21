"""Generate Android-specific Rime sources without changing desktop schemes."""
from pathlib import Path
import hashlib,json,re,shutil
from build_mode_rime import build
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'原型/键位编辑器/touch/trime-base'
def main():
    from build_trime_fonts import main as build_fonts
    font_report=build_fonts()
    source=ROOT/'工具/work/trime-source'
    result=build(output=source)
    OUT.mkdir(parents=True,exist_ok=True)
    files=[]
    for p in source.glob('unicode_*.yaml'):
        shutil.copy2(p,OUT/p.name);files.append(p.name)
    schema=(source/'personal_unicode_modes.schema.yaml').read_text(encoding='utf-8')
    schema=re.sub(r'^  dependencies:.*$', '  dependencies: ['+', '.join('unicode_'+k for k,v in result['counts'].items() if v)+']',schema,flags=re.M)
    schema=schema.replace('schema_id: personal_unicode_modes','schema_id: personal_unicode_android').replace('name: Unicode 三模式','name: Unicode 安卓三模式').replace('unicode_modes*','unicode_android*')
    schema=re.sub(r'^  (?:ascii_)?icon:.*\n','',schema,flags=re.M)
    schema=schema.replace('  page_size: 5','  page_size: 8')
    (OUT/'personal_unicode_android.schema.yaml').write_text(schema,encoding='utf-8');files.append('personal_unicode_android.schema.yaml')
    lua=(source/'lua/unicode_modes.lua').read_text(encoding='utf-8').split('M.processor = {}')[0]+MOBILE_PROCESSOR
    (OUT/'lua').mkdir(exist_ok=True);(OUT/'lua/unicode_android.lua').write_text(lua,encoding='utf-8');files.append('lua/unicode_android.lua')
    files.extend('fonts/'+n for n in font_report['fonts'])
    files.append('fonts/coverage.json')
    files.extend(p.relative_to(OUT).as_posix() for p in sorted((OUT/'fonts/licenses').glob('*')) if p.is_file())
    hasher=hashlib.sha256()
    for n in sorted(files):hasher.update((OUT/n).read_bytes())
    digest=hasher.hexdigest()
    manifest={'format':'unicode-trime-base-v1','id':digest[:16],'sha256':digest,'files':files,'fonts':font_report['fonts'],'fontCoverage':{'target':font_report['target'],'covered':font_report['covered']},'counts':result['counts'],'shapeReviewProfile':result.get('shapeReviewProfile')}
    (OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False),encoding='utf-8')
    print('Android Rime bundle',manifest['id'],result['counts'])
MOBILE_PROCESSOR=r'''
M.processor = {}
local layers_options = {"unicode_block", "unicode_shape", "unicode_personal", "unicode_chinese", "unicode_extended"}
function M.processor.init(env)
  env.path = rime_api.get_user_data_dir() .. "/unicode_android.preferences.yaml"
  env.preferences = Config(env.path)
  local ctx = env.engine.context
  for _, name in ipairs(layers_options) do
    local saved = env.preferences:get_bool(name)
    if saved == nil then saved = name == "unicode_block" end
    ctx:set_option(name, saved)
  end
  env.connection = ctx.option_update_notifier:connect(function(context,name)
    for _, item in ipairs(layers_options) do
      if name == item then
        for _, option in ipairs(layers_options) do env.preferences:set_bool(option, context:get_option(option)) end
        env.preferences:save_to_file(env.path)
        return
      end
    end
  end)
end
function M.processor.fini(env)
  if env.connection then env.connection:disconnect() end
end
function M.processor.func(key,env)
  -- Mobile left Shift sends F6; physical standalone Shift_L also cycles modes.
  local ctx = env.engine.context
  local left = key.keycode == 0xffe1
  if left and not key:release() then
    if not env.pending then env.pending=true;env.used=key:ctrl() or key:alt() or key:super() end
    return 2
  end
  local cycle = key.keycode == 0xffc3 and not key:release()
  if key.keycode == 0xffc5 and not key:release() then
    ctx:set_option("unicode_block",true);ctx:set_option("unicode_shape",true);ctx:set_option("unicode_personal",true)
    ctx:refresh_non_confirmed_composition();return 1
  end
  if left and key:release() then cycle=env.pending and not env.used;env.pending=false end
  if cycle then
    local b,s,p=ctx:get_option("unicode_block"),ctx:get_option("unicode_shape"),ctx:get_option("unicode_personal")
    local nb,ns,np=true,false,false
    if b and not s and not p then nb,ns,np=false,true,false
    elseif s and not b and not p then nb,ns,np=false,false,true
    elseif p and not b and not s then nb,ns,np=true,true,true end
    ctx:set_option("unicode_block",nb);ctx:set_option("unicode_shape",ns);ctx:set_option("unicode_personal",np)
    ctx:refresh_non_confirmed_composition()
    return 1
  end
  if env.pending and not key:release() then env.used=true end
  return 2
end
return M
'''
if __name__=='__main__':main()
