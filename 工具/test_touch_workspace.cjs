const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const W=require('../原型/键位编辑器/touch/workspace-core.js');
const known=new Set(['u-2c2d','u-1319f']);
const p={version:2,entries:{'u-2c2d':{favorite:true,chineseName:'三角字母',tags:['常用','常用']}},mobileKeys:{f:{charId:'u-2c2d',action:'commit'},g:{charId:'u-1319f',action:'send'}},recent:['u-1319f','u-1319f','unknown']};
const clean=W.validate(p,known);assert.deepEqual(clean.recent,['u-1319f']);assert.deepEqual(clean.entries['u-2c2d'].tags,['常用']);assert.deepEqual(W.validate(JSON.parse(JSON.stringify(clean)),known),clean);
assert.throws(()=>W.validate({...p,mobileKeys:{f:{charId:'unknown',action:'commit'}}},known),/无效/);
assert.throws(()=>W.validate({...p,entries:{unknown:p.entries['u-2c2d']}},known),/未知/);
assert.throws(()=>W.validate({...p,mobileKeys:{f:{charId:'u-2c2d',action:'execute'}}},known),/无效/);
const byId=new Map([['u-2c2d',{char:'Ⱝ'}],['u-1319f',{char:'𓆟'}]]);
const theme=W.theme(clean,byId);assert.match(theme,/Unicode_f: \{label: "Ⱝ", commit: "Ⱝ"/);assert.match(theme,/Unicode_g: \{label: "𓆟", send: g/);
assert.match(theme,/UnicodeAscii:.*toggle: ascii_mode/);assert.match(theme,/UnicodeCycle:.*send: F6/);
assert(theme.indexOf('click: "UnicodeAscii"')<theme.indexOf('click: "Unicode_q"'));
assert(theme.indexOf('click: "UnicodeCycle"')<theme.indexOf('click: "Unicode_z"'));
assert.match(theme,/personal_unicode_android:\n    import_preset: unicode/,'Trime schema-ID layout must win over automatic qwerty matching');
assert.match(theme,/keyboards: \[personal_unicode_android, unicode,/);
assert.match(theme,/UnicodeAscii.*width: 20, height: 28, key_text_size: 14/);
assert.match(theme,/Unicode_q.*height: 52/);
assert.match(theme,/unicode_function_bg: "0xff335d4a"/);
assert.match(theme,/UnicodeCycle.*key_back_color: unicode_function_bg, key_text_color: unicode_function_fg/);
assert.match(theme,/UnicodeSpace: \{label: 空格/);
const fontTheme=W.theme(clean,byId,['latin.ttf','symbols.otf']);assert.match(fontTheme,/candidate_font: \["latin.ttf","symbols.otf"\]/);assert.match(fontTheme,/latin_font: \[\]/);
for(const field of ['key_font','label_font','comment_font','text_font'])assert.match(fontTheme,new RegExp(field+': \\[\\]'),'UI text must keep the system typeface');
const base=path.join(__dirname,'../原型/键位编辑器/touch/trime-base');
if(fs.existsSync(base)){
const schema=fs.readFileSync(path.join(base,'personal_unicode_android.schema.yaml'),'utf8');assert(!schema.includes('.ico'));assert(!schema.includes('personal_unicode_modes_'));assert(schema.includes('unicode_android*processor'));
const lua=fs.readFileSync(path.join(base,'lua/unicode_android.lua'),'utf8');assert(!lua.includes('apply_schema'));assert(lua.includes('0xffc3'));assert(lua.includes('0xffc5'));
}
W.zip({'样本.txt':'𓆟á','nested/metadata.json':JSON.stringify(clean)}).arrayBuffer().then(b=>{fs.mkdirSync(path.join(__dirname,'work'),{recursive:true});fs.writeFileSync(path.join(__dirname,'work/touch-test.zip'),Buffer.from(b));console.log('PASS: metadata validation, exact supplementary characters, backup roundtrip, keyboard semantics and positions, Android-specific Lua, ZIP fixture');});
